# app/routes/scheduler.py
import json
from fastapi import APIRouter

from app.core.redis_client import redis_client
from app.models.redis_keys import (
    scheduler_state_key,
    GLOBAL_RUNNING_JOBS,
    GLOBAL_JOB_PROGRESS,
    ACTIVE_USERS_KEY,
    GLOBAL_PENDING_JOBS,
)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


# ------------------ CONTROL ------------------
@router.post("/start")
async def start_scheduler():
    await redis_client.set(scheduler_state_key(), "running")
    return {"state": "running"}


@router.post("/pause")
async def pause_scheduler():
    await redis_client.set(scheduler_state_key(), "paused")
    return {"state": "paused"}


@router.get("/state")
async def get_scheduler_state():
    state = await redis_client.get(scheduler_state_key())
    return state or "paused"


# ------------------ GLOBAL STATUS ------------------
@router.get("/global_status")
async def get_global_status():

    running = list(await redis_client.smembers(GLOBAL_RUNNING_JOBS) or [])
    active_users = list(await redis_client.smembers(ACTIVE_USERS_KEY) or [])
    pending = await redis_client.lrange(GLOBAL_PENDING_JOBS, 0, -1)

    raw_progress = await redis_client.hgetall(GLOBAL_JOB_PROGRESS)

    progress = {}
    for job_id, payload in raw_progress.items():
        try:
            progress[job_id] = json.loads(payload)
        except:
            progress[job_id] = {
                "job_id": job_id,
                "status": "UNKNOWN",
                "percent": 0,
                "updated_at": ""
            }

    return {
        "running_jobs": running,
        "active_users": active_users,
        "pending_jobs": pending,
        "progress": progress,
    }