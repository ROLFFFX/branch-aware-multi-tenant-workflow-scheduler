from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import uuid
import os

from app.core.redis_client import redis_client
from app.models.redis_keys import (
    user_slides_key,
    slide_key,
)

router = APIRouter(prefix="/files", tags=["Files"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "slides"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload_wsi")
async def upload_wsi(user_id: str, file: UploadFile = File(...)):
    filename = file.filename.lower()

    if not filename.endswith(".svs"):
        raise HTTPException(400, "Only .svs files allowed")

    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)

    if size == 0:
        raise HTTPException(400, "Uploaded file is empty")

    slide_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{slide_id}.svs"

    # Save physical file
    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Store in Redis
    await redis_client.sadd(user_slides_key(user_id), slide_id)
    await redis_client.hset(
        slide_key(slide_id),
        mapping={
            "slide_id": slide_id,
            "user_id": user_id,
            "slide_path": str(save_path),
            "size_bytes": size,
        },
    )

    return {
        "slide_id": slide_id,
        "slide_path": str(save_path),
        "size_bytes": size,
        "user_id": user_id,
    }

@router.get("/user/{user_id}/slides")
async def list_slides(user_id: str):
    # Fetch all slide IDs owned by user
    slide_ids = await redis_client.smembers(user_slides_key(user_id))
    slides = []

    for sid in slide_ids:
        meta = await redis_client.hgetall(slide_key(sid))
        if meta:
            slides.append(meta)

    return slides
