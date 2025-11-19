from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import uuid
import os

router = APIRouter(prefix="/files", tags=["Files"])

# -------------------------------------------------------------------
# Storage folder (absolute path inside backend/storage/slides/)
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "slides"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------------
# Upload WSI (.svs) file
# -------------------------------------------------------------------
@router.post("/upload_wsi")
async def upload_wsi(file: UploadFile = File(...)):
    filename = file.filename.lower()

    # Only allow .svs
    if not filename.endswith(".svs"):
        raise HTTPException(status_code=400, detail="Only .svs files allowed")

    # Ensure file not empty
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)

    if size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Store with UUID name
    slide_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{slide_id}.svs"

    try:
        with save_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    return {
        "slide_id": slide_id,
        "slide_path": str(save_path),
        "size_bytes": size
    }
