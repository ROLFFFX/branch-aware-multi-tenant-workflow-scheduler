import json
import numpy as np
import cv2
from PIL import Image
import openslide
from pathlib import Path

from app.workers.registry import register_job

TMP_DIR = Path("tmp")
TMP_DIR.mkdir(exist_ok=True)


# -----------------------------------------------------
# 1. Generate a tissue mask at low resolution
# -----------------------------------------------------
def compute_tissue_mask(slide, thumb_size=(2048, 2048)):
    """
    Returns:
        tissue_mask (np.uint8 array): 1 = tissue, 0 = background
        scale: ratio between mask size and level-0 WSI size
    """
    # Low-res thumbnail for mask generation
    thumbnail = slide.get_thumbnail(thumb_size)
    thumb_np = np.array(thumbnail.convert("RGB"))

    # Convert to HSV → H & S channels help eliminate white background
    hsv = cv2.cvtColor(thumb_np, cv2.COLOR_RGB2HSV)
    H, S, V = cv2.split(hsv)

    # Otsu threshold on saturation
    _, sat_mask = cv2.threshold(S, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Remove very bright areas (white background)
    _, val_mask = cv2.threshold(V, 220, 255, cv2.THRESH_BINARY_INV)

    raw_mask = (sat_mask > 0).astype(np.uint8) & (val_mask > 0).astype(np.uint8)

    # Morph closing to fill holes
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    tissue_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, kernel)

    # Compute scaling factor back to level-0 coordinates
    W0, H0 = slide.dimensions
    mask_h, mask_w = tissue_mask.shape
    scale_x = mask_w / W0
    scale_y = mask_h / H0

    return tissue_mask, (scale_x, scale_y)


# -----------------------------------------------------
# 2. Smart Tiling (Mask-based)
# -----------------------------------------------------
def generate_smart_tiles(tissue_mask, scale, tile_size, overlap=0, min_size=512, max_size=1536):
    """
    Args:
        tissue_mask: low-res mask
        scale: (scale_x, scale_y)
    """
    scale_x, scale_y = scale
    mask_h, mask_w = tissue_mask.shape

    # Project tile grid into the tissue-mask space
    # Compute level-0 width/height from scale
    W0 = int(mask_w / scale_x)
    H0 = int(mask_h / scale_y)

    tiles = []

    # Step across full resolution (level 0)
    stride = tile_size - overlap
    for y0 in range(0, H0, stride):
        for x0 in range(0, W0, stride):

            # Map tile coords → mask coords
            mx1 = int(x0 * scale_x)
            my1 = int(y0 * scale_y)
            mx2 = int((x0 + tile_size) * scale_x)
            my2 = int((y0 + tile_size) * scale_y)

            mx2 = min(mx2, mask_w)
            my2 = min(my2, mask_h)

            region = tissue_mask[my1:my2, mx1:mx2]
            if region.size == 0:
                continue

            tissue_ratio = region.mean()

            # Skip blank tiles
            if tissue_ratio < 0.05:
                continue

            # Adapt tile sizes (your logic preserved)
            if tissue_ratio > 0.40:
                adaptive = min_size
            elif tissue_ratio > 0.10:
                adaptive = tile_size
            else:
                adaptive = max_size

            tiles.append({
                "x": x0,
                "y": y0,
                "size": adaptive,
            })

    return tiles


# -----------------------------------------------------
# 3. JOB EXECUTION
# -----------------------------------------------------
@register_job("init_wsi")
async def wsi_initialize(job_id: str, payload: dict):

    slide_id = payload["slide_id"]
    slide_path = Path(payload["slide_path"])

    TILE_SIZE = payload.get("tile_size", 1024)
    OVERLAP = payload.get("overlap", 128)
    MIN_TILE = payload.get("min_tile", 512)
    MAX_TILE = payload.get("max_tile", 1536)

    slide = openslide.OpenSlide(str(slide_path))
    W0, H0 = slide.dimensions

    # 1) Compute tissue mask (low level)
    tissue_mask, scale = compute_tissue_mask(slide)

    # 2) Compute tiles based on mask
    tiles = generate_smart_tiles(
        tissue_mask,
        scale,
        TILE_SIZE,
        OVERLAP,
        MIN_TILE,
        MAX_TILE,
    )

    # 3) Save mask for frontend visualization
    tissue_mask_vis = (tissue_mask * 255).astype(np.uint8)
    mask_path = TMP_DIR / f"{job_id}_tissue_mask.png"
    Image.fromarray(tissue_mask_vis).save(mask_path)

    # 4) Save smart tile metadata
    tiles_path = TMP_DIR / f"{job_id}_tiles.json"
    with open(tiles_path, "w") as f:
        json.dump(tiles, f)

    # 5) Return job output (stored by worker)
    return {
        "slide_id": slide_id,
        "width": W0,
        "height": H0,
        "num_tiles": len(tiles),
        "tiles_path": str(tiles_path),
        "tissue_mask_path": str(mask_path),
        "scale": scale,
    }
