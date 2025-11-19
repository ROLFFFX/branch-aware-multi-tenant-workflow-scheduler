# app/scheduler/scheduler_main.py
import asyncio

from app.core.redis_client import redis_client
from app.models.redis_keys import (
    GLOBAL_PENDING_JOBS,
    user_queue_key,
    job_key,
    scheduler_state_key,
    ACTIVE_USERS_KEY,
)
from app.schemas.jobs import JobStatus  # optional if you want to use it for logging

# Max number of distinct users that can have jobs running concurrently
MAX_ACTIVE_USERS = 3


async def scheduler_loop():
    """
    Global scheduler:

    - Watches GLOBAL_PENDING_JOBS (a Redis list of job_ids).
    - Respects `scheduler:state` (running / paused).
    - Dispatches jobs to per-user queues (one queue per user).
    - Enforces a global limit on number of *active users*.
    """
    print("[Scheduler] Loop started.")

    # Ensure state key exists
    state = await redis_client.get(scheduler_state_key())
    if state is None:
        await redis_client.set(scheduler_state_key(), "paused")

    while True:
        # Check scheduler state
        state = await redis_client.get(scheduler_state_key())
        if state != "running":
            await asyncio.sleep(0.5)
            continue

        # Pop a pending job (blocking pop with timeout)
        result = await redis_client.blpop(GLOBAL_PENDING_JOBS, timeout=1)
        if not result:
            # No pending job in the last second
            continue

        _, job_id = result
        print(f"[Scheduler] Got pending job {job_id}")

        # Load job metadata
        job_data = await redis_client.hgetall(job_key(job_id))
        if not job_data:
            print(f"[Scheduler] Missing metadata for {job_id}, skipping.")
            continue

        user_id = job_data.get("user_id")
        if not user_id:
            print(f"[Scheduler] Missing user_id for {job_id}, skipping.")
            continue

        # Enforce active user limit.
        # - If user is already active, we allow more jobs for them.
        # - If user is new and we already have MAX_ACTIVE_USERS, we re-queue the job.
        active_user_ids = await redis_client.smembers(ACTIVE_USERS_KEY)
        num_active = len(active_user_ids)

        if user_id not in active_user_ids and num_active >= MAX_ACTIVE_USERS:
            # Too many distinct active users → requeue the job at the tail
            print(
                f"[Scheduler] Active users = {num_active} (>= {MAX_ACTIVE_USERS}), "
                f"deferring job {job_id} for user {user_id}"
            )
            await redis_client.rpush(GLOBAL_PENDING_JOBS, job_id)
            # brief pause to avoid tight cycles
            await asyncio.sleep(0.2)
            continue

        # Assign job to the user's queue
        queue = user_queue_key(user_id)
        await redis_client.rpush(queue, job_id)

        print(f"[Scheduler] Dispatched job {job_id} → {queue} (user={user_id})")
