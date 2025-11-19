import uuid
from pathlib import Path

BASE_STORAGE = Path("storage")
UPLOAD_DIR = BASE_STORAGE / "uploads"
TMP_DIR = BASE_STORAGE / "tmp"
RESULTS_DIR = BASE_STORAGE / "results"

for d in [UPLOAD_DIR, TMP_DIR, RESULTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def save_upload(file, filename=None):
    ext = filename.split(".")[-1]
    new_name = f"{uuid.uuid4()}.{ext}"
    out_path = UPLOAD_DIR / new_name
    with open(out_path, "wb") as f:
        f.write(file)
    return out_path
