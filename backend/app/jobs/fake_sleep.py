print("[fake_sleep] module imported!")   # <-- add this line

import asyncio
from app.workers.registry import register_job

@register_job("fake_sleep")
async def fake_sleep(job_id: str, payload: dict):
    print(f"[fake_sleep] Running job {job_id}")
    await asyncio.sleep(2)
    return {
        "job_id": job_id,
        "message": "Fake sleep completed",
        "slept_seconds": 2,
        "input": payload,
    }
