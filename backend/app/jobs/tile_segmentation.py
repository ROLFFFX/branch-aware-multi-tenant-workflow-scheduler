import uuid
import json
import asyncio
import functools
from typing import List, Dict, Any

# Import redis_client globally so it's accessible to the thread function
from app.core.redis_client import redis_client
from app.services.job_manager import JobManager
from app.services.branch_manager import BranchManager
from app.services.workflow_manager import WorkflowManager
from app.models.redis_keys import (
    workflow_runs_key,
    workflow_run_jobs_key,
    GLOBAL_PENDING_JOBS,
    slide_key,  # Used for WSI hydration
)

from app.workers.registry import register_job

import numpy as np
from PIL import Image
import os
import openslide
from pathlib import Path
import torch
import cv2
from torchvision import models, transforms

# Initialize INSTANSEG_MODEL (assuming it's a pre-trained model from torchvision)
INSTANSEG_MODEL = models.segmentation.deeplabv3_resnet101(pretrained=True)
INSTANSEG_MODEL.eval()  # Set the model to evaluation mode

# Initialize BATCH_SIZE for batch processing
BATCH_SIZE = 10

# -------------------------------------------
# Sync Worker Function (Runs in Thread)
# -------------------------------------------
def run_segmentation_task(job_id, slide_path_str, tile_size, overlap, min_tile_size, max_tile_size, loop):
    """
    The synchronous core logic for segmentation. 
    This runs entirely in a separate thread to prevent blocking the asyncio event loop.
    We pass 'loop' explicitly to schedule updates back to the main thread.
    """
    try:
        # 1. Open Slide (Safe in thread)
        slide = openslide.OpenSlide(slide_path_str)
        w, h = slide.dimensions
        print(f"\n=== [Thread] Loading WSI: {slide_path_str}")
        print(f"WSI resolution: {w} × {h}")

        # 2. Compute Tissue Mask
        print("[Thread] Computing tissue mask…")
        tissue_mask, scale = compute_tissue_mask(slide)

        # 3. Generate Tiles
        print("[Thread] Generating smart tiles…")
        tiles = generate_smart_tiles(tissue_mask, scale, tile_size, overlap, min_tile_size, max_tile_size)
        print(f"[Thread] Tiles to process: {len(tiles)}")

        # 4. Init Global Mask
        # Allocating large arrays can be slow, better done in thread
        final_mask = np.zeros((h, w), dtype=np.uint32)

        # 5. Batch Inference & Stitching
        print("[Thread] Running batch inference…")
        running_label = 1
        
        # Preprocessing transform
        preprocess = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        total_tiles = len(tiles)

        for i in range(0, total_tiles, BATCH_SIZE):
            # Log occasional progress
            if i % BATCH_SIZE == 0: 
                print(f"[Thread] Processing {i}/{total_tiles}")
            
            batch = tiles[i:i+BATCH_SIZE]
            
            # Run inference for batch
            batch_out = batch_inference_logic(INSTANSEG_MODEL, slide, batch, preprocess)

            # Stitch results
            for labeled_output, x, y, size in batch_out:
                # Shift labels for uniqueness
                non_zero_mask = labeled_output > 0
                labeled_output[non_zero_mask] += running_label
                running_label = labeled_output.max() + 1

                # Paste into global mask
                y_end = min(y + size, h)
                x_end = min(x + size, w)
                
                h_clip = y_end - y
                w_clip = x_end - x

                final_mask[y:y_end, x:x_end] = labeled_output[:h_clip, :w_clip]
            
            # --- UPDATE PROGRESS SAFELY ---
            # Schedule the Redis update on the main event loop.
            # We use the global 'redis_client' variable.
            if total_tiles > 0:
                current_processed = min(i + BATCH_SIZE, total_tiles)
                percent = int((current_processed / total_tiles) * 100)
                
                asyncio.run_coroutine_threadsafe(
                    redis_client.hset(f"job:{job_id}", mapping={
                        "progress": percent,
                        "status": "running"
                    }),
                    loop
                )

        # 6. Save Outputs
        # Save to 'tmp' directory to match the file server's resolution path
        output_dir = Path("tmp") 
        output_dir.mkdir(exist_ok=True, parents=True)

        filename_mask = f"{job_id}_mask.png"
        filename_overlay = f"{job_id}_overlay.png"

        mask_path = output_dir / filename_mask
        overlay_path = output_dir / filename_overlay

        print("[Thread] Saving final outputs…")
        save_downsampled_mask(final_mask, slide, mask_path)
        save_overlay(final_mask, slide, overlay_path)
        
        print(f"DEBUG: Saved files to {output_dir.resolve()}")

        return {
            "mask_filename": filename_mask,
            "overlay_filename": filename_overlay,
            "num_tiles": len(tiles)
        }

    except Exception as e:
        print(f"Error in segmentation task: {e}")
        raise e

# -------------------------------------------
# Async Job Wrapper
# -------------------------------------------
@register_job("tile_segmentation")
async def tile_segmentation(job_id: str, payload: dict):
    """
    Async wrapper that offloads the entire heavy lifting to a thread.
    """
    print(f"DEBUG: Starting tile_segmentation for Job {job_id}")
    
    # FIX 1: IMMEDIATELY set status to Running.
    # This ensures the UI updates instantly, covering the time taken by 'compute_tissue_mask'.
    try:
        await redis_client.hset(f"job:{job_id}", mapping={
            "status": "running",
            "progress": 0
        })
        print(f"DEBUG: Set Job {job_id} status to RUNNING")
    except Exception as e:
        print(f"ERROR: Failed to set initial Redis status for job {job_id}: {e}")

    slide_id = payload["slide_id"]
    slide_path = payload["slide_path"] # Keep as string for thread safety
    
    # Parameters
    tile_size = payload.get("tile_size", 1024)
    overlap = payload.get("overlap", 128)
    min_tile_size = payload.get("min_tile_size", 512)
    max_tile_size = payload.get("max_tile_size", 1536)

    loop = asyncio.get_running_loop()

    # FIX 2: Pass 'loop' directly instead of a closure callback.
    # This prevents pickling errors if the executor environment is strict.
    result = await loop.run_in_executor(
        None, 
        run_segmentation_task,
        job_id, slide_path, tile_size, overlap, min_tile_size, max_tile_size, loop
    )

    print("\nJob Completed Successfully.")
    print(f" - mask    → {result['mask_filename']}")
    print(f" - overlay → {result['overlay_filename']}\n")

    # Final update to 100%
    await redis_client.hset(f"job:{job_id}", mapping={"progress": 100, "status": "completed"})

    return {
        "slide_id": slide_id,
        # Return relative filename so the download endpoint (rooted in tmp) finds it
        "mask_path": result["mask_filename"],     
        "overlay_path": result["overlay_filename"], 
        "num_tiles": result["num_tiles"],
    }

# -------------------------------------------
# Helper functions
# -------------------------------------------

def compute_tissue_mask(slide):
    w, h = slide.dimensions
    thumbnail = slide.get_thumbnail((2048, 2048))
    thumb_w, thumb_h = thumbnail.size
    thumb_np = np.array(thumbnail.convert("RGB"))
    
    scale_x = w / thumb_w
    scale_y = h / thumb_h
    scale = (scale_x, scale_y)

    hsv = cv2.cvtColor(thumb_np, cv2.COLOR_RGB2HSV)
    H, S, V = cv2.split(hsv)

    _, sat_mask = cv2.threshold(S, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, val_mask = cv2.threshold(V, 220, 255, cv2.THRESH_BINARY_INV)

    tissue_mask = (sat_mask > 0).astype(np.uint8) & (val_mask > 0).astype(np.uint8)
    return tissue_mask, scale


def generate_smart_tiles(tissue_mask, scale, tile_size, overlap, min_size, max_size):
    scale_x, scale_y = scale
    mask_h, mask_w = tissue_mask.shape

    W0 = int(mask_w * scale_x)
    H0 = int(mask_h * scale_y)

    tiles = []
    stride = tile_size - overlap
    for y0 in range(0, H0, stride):
        for x0 in range(0, W0, stride):
            mx1 = int(x0 / scale_x)
            my1 = int(y0 / scale_y)
            mx2 = int((x0 + tile_size) / scale_x)
            my2 = int((y0 + tile_size) / scale_y)

            mx2 = min(mx2, mask_w)
            my2 = min(my2, mask_h)
            
            if mx1 >= mx2 or my1 >= my2: continue
            
            region = tissue_mask[my1:my2, mx1:mx2]
            if region.size == 0: continue

            tissue_ratio = region.mean()
            if tissue_ratio < 0.05: continue

            if tissue_ratio > 0.40: adaptive_size = min_size
            elif tissue_ratio > 0.10: adaptive_size = tile_size
            else: adaptive_size = max_size

            tiles.append({"x": x0, "y": y0, "size": adaptive_size})

    return tiles

def batch_inference_logic(model, slide, batch, preprocess):
    """
    Helper logic for batch inference, called inside the thread loop.
    """
    batch_out = []
    for tile in batch:
        x, y, size = tile["x"], tile["y"], tile["size"]
        
        tile_image = slide.read_region((x, y), 0, (size, size))
        tile_pil = tile_image.convert("RGB")
        input_tensor = preprocess(tile_pil).unsqueeze(0)

        with torch.no_grad():
            output = model(input_tensor)["out"]
            _, predicted_mask = torch.max(output, 1)
            
            labeled_output = predicted_mask.squeeze(0).cpu().numpy().astype(np.uint8)
            
            labeled_output_resized = cv2.resize(
                labeled_output, (size, size), interpolation=cv2.INTER_NEAREST
            ).astype(np.uint32)

        batch_out.append((labeled_output_resized, x, y, size))
    return batch_out

def save_downsampled_mask(mask, slide, out_path):
    downsample_factor = 16
    mask_downsampled = mask[::downsample_factor, ::downsample_factor]
    
    unique_labels = np.unique(mask_downsampled)
    unique_labels = unique_labels[unique_labels != 0]

    np.random.seed(42)
    colors = {}
    for label in unique_labels:
        colors[label] = tuple(np.random.randint(50, 256, 3)) 

    h, w = mask_downsampled.shape
    colored_mask = np.zeros((h, w, 3), dtype=np.uint8)

    for label, color in colors.items():
        colored_mask[mask_downsampled == label] = color

    mask_image = Image.fromarray(colored_mask)
    mask_image.save(out_path)

def save_overlay(mask, slide, out_path):
    w, h = slide.dimensions
    downsample_factor = 8
    overlay_w = w // downsample_factor
    overlay_h = h // downsample_factor
    
    background = slide.get_thumbnail((overlay_w, overlay_h)).convert("RGB")
    background_np = np.array(background)
    
    # NumPy slicing for downsampling (avoids cv2.resize uint32 error)
    mask_resized = mask[0:overlay_h * downsample_factor:downsample_factor, 
                        0:overlay_w * downsample_factor:downsample_factor]
    
    unique_labels = np.unique(mask_resized)
    unique_labels = unique_labels[unique_labels != 0]

    np.random.seed(42)
    colors = {}
    for label in unique_labels:
        colors[label] = tuple(np.random.randint(50, 256, 3)) 

    overlay_layer = np.zeros_like(background_np)
    for label, color in colors.items():
        overlay_layer[mask_resized == label] = color

    alpha = 0.5
    final_overlay = cv2.addWeighted(background_np, 1 - alpha, overlay_layer, alpha, 0)
    
    overlay_image = Image.fromarray(final_overlay)
    overlay_image.save(out_path)