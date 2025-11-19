import numpy as np
from pathlib import Path
from PIL import Image
import openslide
import cv2
from instanseg.inference_class import InstanSeg
import time

# global configs
OUTPUT_DIR = Path("./results")
LEVEL = 0
OVERLAP = 0
# WSI_PATH = Path("../data/CMU-1-Small-Region.svs")
WSI_PATH = Path("../data/JP2k-33003-1.svs")
TILE_SIZE = 1024
MIN_TILE_SIZE = 512
MAX_TILE_SIZE = 2048
OVERLAP = 64
BATCH_SIZE = 8 

INSTANSEG_MODEL = InstanSeg("brightfield_nuclei", verbosity=0)


# helper - tile generation
def tile_coordinates(width, height, tile_size=TILE_SIZE, overlap=OVERLAP):
    """Generate coordinates for tile top-left corner."""
    xs = list(range(0, width, tile_size - overlap))
    ys = list(range(0, height, tile_size - overlap))
    return [(x, y) for x in xs for y in ys]

# helper - output
def save_downsampled_mask(mask, slide, out_path, max_size=4096):
    """Save a downsampled version of the full mask."""
    h, w = mask.shape
    scale = min(max_size / max(h, w), 1.0)
    new_size = (int(w * scale), int(h * scale))

    if mask.max() > 0:
        mask_uint8 = (mask / mask.max() * 255).astype(np.uint8)
    else:
        mask_uint8 = mask.astype(np.uint8)

    mask_resized = cv2.resize(mask_uint8, new_size, interpolation=cv2.INTER_NEAREST)
    Image.fromarray(mask_resized).save(out_path)


def save_overlay(mask, slide, out_path, max_size=4096):
    """Save colored overlay of mask on WSI thumbnail."""
    h, w = mask.shape
    scale = min(max_size / max(h, w), 1.0)
    new_size = (int(w * scale), int(h * scale))

    # Slide thumbnail
    thumbnail = slide.get_thumbnail(new_size)
    thumbnail_np = np.array(thumbnail)

    # Resize mask
    if mask.max() > 0:
        mask_uint8 = (mask / mask.max() * 255).astype(np.uint8)
    else:
        mask_uint8 = mask.astype(np.uint8)

    mask_resized = cv2.resize(mask_uint8, new_size, interpolation=cv2.INTER_NEAREST)

    # Colorize & blend
    colored = cv2.applyColorMap(mask_resized, cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(thumbnail_np, 0.7, colored, 0.3, 0)

    Image.fromarray(overlay).save(out_path)


# main pipeline
def process_wsi_naive(input_path: Path, output_dir: Path):
    '''
        Pipeline Overview:
        WSI Loading                         - lazily loads WSI metadata; extract dimensions and report
        Tile Generation                     - slide divided to fixed-size tiles (TILE_SIZE, OVERLAP)
        Tile-Level Instance Segmentation    - for each tile coord, extract tile from WSI, run InstanSeg, check instance ID validity, insert tile mask into global mask
        Output Generation                   - generate downsampled: downsampled mask, overlay viz, then dump to /results
    '''
    print(f"Loading: {input_path}")

    slide = openslide.OpenSlide(str(input_path))
    w, h = slide.dimensions

    print(f"WSI size: {w} x {h}")

    coords = tile_coordinates(w, h)
    print(f"Total tiles: {len(coords)}")

    final_mask = np.zeros((h, w), dtype=np.uint32)

    # Load InstanSeg model
    print("Loading InstanSeg model…")
    model = InstanSeg("brightfield_nuclei", verbosity=0)

    running_label = 1

    for (x, y) in coords:
        tile_img = slide.read_region((x, y), LEVEL, (TILE_SIZE, TILE_SIZE))
        tile_np = np.array(tile_img.convert("RGB"))

        labeled_output, _ = model.eval_small_image(tile_np)
        labeled_output = labeled_output.squeeze().numpy()

        # Offset labels to avoid collisions
        labeled_output[labeled_output > 0] += running_label
        running_label = labeled_output.max() + 1

        # Insert tile into final mask
        y_end = min(y + TILE_SIZE, h)
        x_end = min(x + TILE_SIZE, w)
        tile_h = y_end - y
        tile_w = x_end - x

        final_mask[y:y_end, x:x_end] = labeled_output[:tile_h, :tile_w]

        print(f"Processed tile ({x},{y}) → next label {running_label}")

    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True, parents=True)

    mask_path = output_dir / "mask.png"
    overlay_path = output_dir / "overlay.png"

    print("Saving results...")
    save_downsampled_mask(final_mask, slide, mask_path)
    save_overlay(final_mask, slide, overlay_path)

    print(f"Saved mask     → {mask_path}")
    print(f"Saved overlay  → {overlay_path}")
    
def process_wsi_optimized(input_path: Path, output_dir: Path, BATCH_SIZE, TILE_SIZE, MIN_TILE_SIZE, MAX_TILE_SIZE, OVERLAP):
    '''
        optimized Pipeline Overview:
        WSI Loading                         - lazily loads WSI metadata; extract dimensions and report
            : precompute tissue mask at low-res to skip empty tiles; avoid repeated read_region overhead
        Tile Generation                     - slide divided to fixed-size tiles (TILE_SIZE, OVERLAP)
            : smart tiling / tissue detection; skip pure background tiles; use adaptive tile sizes (smaller for dense areas, bigger for sparse)
        Tile-Level Instance Segmentation    - for each tile coord, extract tile from WSI, run InstanSeg, check instance ID validity, insert tile mask into global mask
            : batch tiles
        Output Generation                   - generate downsampled: downsampled mask, overlay viz, then dump to /results
            : downsample using OpenSlide thumbnail res; 
    '''
    def compute_tissue_mask(slide, threshold=200):
        """
        Compute low-res tissue mask using the slide thumbnail.
        Returns a binary mask (tissue = 1, background = 0).
        """
        thumbnail = slide.get_thumbnail((1024, 1024))
        thumb_np = np.array(thumbnail.convert("L"))

        mask = (thumb_np < threshold).astype(np.uint8)

        mask_full = cv2.resize(
            mask,
            slide.dimensions,
            interpolation=cv2.INTER_NEAREST
        )
        return mask_full
    
    def generate_smart_tiles(tissue_mask, tile_size, overlap):
        """
        Generate tiles only where tissue exists.
        Adaptive tile size is used based on local tissue density.
        """
        h, w = tissue_mask.shape
        tiles = []

        # sliding window at coarse stride
        for y in range(0, h, tile_size - overlap):
            for x in range(0, w, tile_size - overlap):

                y_end = min(y + tile_size, h)
                x_end = min(x + tile_size, w)
                region = tissue_mask[y:y_end, x:x_end]

                tissue_ratio = region.mean()

                # skip empty tiles
                if tissue_ratio < 0.05:
                    continue

                # adaptive tile size
                if tissue_ratio > 0.40:
                    adaptive_size = MIN_TILE_SIZE
                elif tissue_ratio > 0.10:
                    adaptive_size = tile_size
                else:
                    adaptive_size = MAX_TILE_SIZE

                tiles.append({
                    "x": x,
                    "y": y,
                    "size": adaptive_size
                })

        return tiles

    def batch_inference(model, slide, tile_batch):
        """
        True batching for speed: batch the expensive OpenSlide I/O,
        but run InstanSeg sequentially (it does not support tensor batching).
        """
        # 1. Pre-load all tiles using OpenSlide (I/O bound)
        tiles_np = []
        coords = []

        for t in tile_batch:
            x, y, size = t["x"], t["y"], t["size"]
            tile = slide.read_region((x, y), 0, (size, size))
            tile_np = np.array(tile.convert("RGB"))
            tiles_np.append(tile_np)
            coords.append((x, y, size))

        # 2. Run inference sequentially (CPU/GPU bound)
        outputs = []
        for tile_np in tiles_np:
            labeled, _ = model.eval_small_image(tile_np)
            outputs.append(labeled.squeeze().numpy())

        return list(zip(outputs, coords))

    
    def save_downsampled_mask(mask, slide, out_path):
        """
        Downsample mask using OpenSlide thumbnail (fast + accurate).
        """
        max_dim = 4096
        thumbnail = slide.get_thumbnail(
            (mask.shape[1] * max_dim // max(mask.shape),
            mask.shape[0] * max_dim // max(mask.shape))
        )
        thumb_size = thumbnail.size

        mask_ds = cv2.resize(mask.astype(np.uint8), thumb_size, interpolation=cv2.INTER_NEAREST)
        Image.fromarray(mask_ds).save(out_path)
        
    def save_overlay(mask, slide, out_path):
        """
        Create overlay using slide thumbnail for consistent scaling.
        """
        # match mask to thumbnail resolution
        max_dim = 4096
        thumbnail = slide.get_thumbnail(
            (mask.shape[1] * max_dim // max(mask.shape),
            mask.shape[0] * max_dim // max(mask.shape))
        )
        thumb_np = np.array(thumbnail)

        mask_ds = cv2.resize(mask.astype(np.uint8), thumbnail.size, interpolation=cv2.INTER_NEAREST)
        colored = cv2.applyColorMap(mask_ds, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(thumb_np, 0.7, colored, 0.3, 0)

        Image.fromarray(overlay).save(out_path)
    
    print(f"\n=== Loading WSI: {input_path}")
    slide = openslide.OpenSlide(str(input_path))
    w, h = slide.dimensions
    print(f"WSI resolution: {w} × {h}")

    # low-res tissue mask
    print("Computing tissue mask…")
    tissue_mask = compute_tissue_mask(slide)

    # smart tiling
    print("Generating smart tiles…")
    tiles = generate_smart_tiles(tissue_mask, TILE_SIZE, OVERLAP)
    print(f"Tiles to process: {len(tiles)}")

    # global mask
    final_mask = np.zeros((h, w), dtype=np.uint32)

    # model load
    model = INSTANSEG_MODEL

    running_label = 1

    # batch tile
    print("Running batch inference…")
    for i in range(0, len(tiles), BATCH_SIZE):
        print(f"Processing {i} out of {len(tiles)}")
        batch = tiles[i:i+BATCH_SIZE]
        batch_out = batch_inference(model, slide, batch)

        for labeled_output, (x, y, size) in batch_out:

            # shift labels → global uniqueness
            labeled_output[labeled_output > 0] += running_label
            running_label = labeled_output.max() + 1

            # paste into global mask
            y_end = min(y + size, h)
            x_end = min(x + size, w)
            tile_h = y_end - y
            tile_w = x_end - x

            final_mask[y:y_end, x:x_end] = labeled_output[:tile_h, :tile_w]

    # ---------------------------
    # 4. OUTPUT SAVING
    # ---------------------------
    output_dir.mkdir(exist_ok=True, parents=True)
    mask_path = output_dir / "mask.png"
    overlay_path = output_dir / "overlay.png"

    print("Saving final outputs…")
    save_downsampled_mask(final_mask, slide, mask_path)
    save_overlay(final_mask, slide, overlay_path)

    print("\nSaved:")
    print(f" - mask    → {mask_path}")
    print(f" - overlay → {overlay_path}\n")
   



if __name__ == "__main__":
    start = time.time()
    # process_wsi_naive(WSI_PATH, OUTPUT_DIR)
    process_wsi_optimized(WSI_PATH, OUTPUT_DIR, BATCH_SIZE, TILE_SIZE, MIN_TILE_SIZE, MAX_TILE_SIZE, OVERLAP)
    end = time.time()
    print(f"Total runtime: {end-start:.2f} seconds")
    
    
'''
    Runtime Reports (no GPU; Apple Silicon M2 MacBook Air with 8GB unified memory):
    METHOD                   INPUT                       FILE SIZE   EXECUTION TIME
    process_wsi_naive        CMU-1-Small-Region.svs      1.9 MB      7.02 seconds
    process_wsi_optimized    CMU-1-Small-Region.svs      1.9 MB      5.85 seconds
    
    
    process_wsi_naive        JP2k-33003-1.svs            60.89 MB    200.79 seconds
    process_wsi_optimized    JP2k-33003-1.svs            60.89 MB    114.87 seconds
'''
