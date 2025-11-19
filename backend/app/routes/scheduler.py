from fastapi import APIRouter
from app.core.redis_client import redis_client
from app.models.redis_keys import scheduler_state_key

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.post("/start")
async def start_scheduler():
    await redis_client.set(scheduler_state_key(), "running")
    return {"message": "Scheduler started", "state": "running"}


@router.post("/pause")
async def pause_scheduler():
    await redis_client.set(scheduler_state_key(), "paused")
    return {"message": "Scheduler paused", "state": "paused"}


@router.get("/state")
async def get_scheduler_state():
    state = await redis_client.get(scheduler_state_key())
    return {"state": state or "paused"}
