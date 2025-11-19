# app/workers/worker_main.py
import asyncio
import json
from datetime import datetime

from app.core.redis_client import redis_client
from app.models.redis_keys import (
    user_queue_key,
    job_key,
    GLOBAL_RUNNING_JOBS,
    GLOBAL_JOB_PROGRESS,
    ACTIVE_USERS_KEY,
)
from app.workers.registry import JOB_REGISTRY
from app.schemas.jobs import JobStatus
from app.services.job_manager import JobManager


async def _user_has_other_running_jobs(user_id: str, current_job_id: str) -> bool:
    """
    Check if the given user still has other jobs in the GLOBAL_RUNNING_JOBS set.
    Used to decide whether we can safely remove the user from ACTIVE_USERS_KEY.
    """
    running_ids = await redis_client.smembers(GLOBAL_RUNNING_JOBS)
    if not running_ids:
        return False

    for jid in running_ids:
        if jid == current_job_id:
            continue

        job_data = await redis_client.hgetall(job_key(jid))
        if job_data and job_data.get("user_id") == user_id:
            return True

    return False


async def _set_progress(job_id: str, user_id: str, status: JobStatus, percent: float):
    """
    Helper to update the GLOBAL_JOB_PROGRESS hash in a consistent format.
    Note: `percent` is in [0, 1].
    """
    await redis_client.hset(
        GLOBAL_JOB_PROGRESS,
        job_id,
        json.dumps(
            {
                "job_id": job_id,
                "user_id": user_id,
                "status": status.value,
                "percent": float(percent),
                "updated_at": datetime.utcnow().isoformat(),
            }
        ),
    )


async def worker_loop(user_id: str):
    """
    Dedicated worker for a single user.
    Continuously pulls job_ids from user:<id>:queue and executes them.

    This worker does NOT do global scheduling logic; it only consumes jobs
    that have already been assigned to this user by the scheduler.
    """
    queue = user_queue_key(user_id)
    print(f"[Worker:{user_id}] Started. Queue = {queue}")

    while True:
        # Non-blocking pop with small sleep to avoid busy-loop
        job_id = await redis_client.lpop(queue)
        if not job_id:
            await asyncio.sleep(0.5)
            continue

        print(f"[Worker:{user_id}] Picked job {job_id}")

        # Load job metadata
        job_data = await redis_client.hgetall(job_key(job_id))
        if not job_data:
            print(f"[Worker:{user_id}] Missing job data for {job_id}")
            continue

        template = job_data.get("job_template_id")
        raw_payload = job_data.get("input_payload", "{}")

        # Parse payload (defensive against double JSON encoding)
        try:
            payload = json.loads(raw_payload)
            if isinstance(payload, str):
                payload = json.loads(payload)
        except Exception:
            payload = {}

        # --- Mark job RUNNING & register globally ---
        try:
            # Persist job state in your JobManager (DB / Redis / etc.)
            await JobManager.mark_running(job_id)

            # Mark in global sets / hashes (for scheduler + UI)
            await redis_client.sadd(GLOBAL_RUNNING_JOBS, job_id)
            await redis_client.sadd(ACTIVE_USERS_KEY, user_id)

            await _set_progress(job_id, user_id, JobStatus.RUNNING, 0.0)

            # ---- Execute the actual job function ----
            func = JOB_REGISTRY.get(template)
            if not func:
                raise RuntimeError(f"Unknown job template: {template}")

            # func is expected to be an async callable: await func(job_id, payload)
            result = await func(job_id, payload)

            # Mark success in your JobManager
            await JobManager.mark_success(job_id, result)

            # Final progress = 100%
            await _set_progress(job_id, user_id, JobStatus.SUCCESS, 1.0)

        except Exception as exc:
            # Persist failure
            err_msg = f"{type(exc).__name__}: {exc}"
            print(f"[Worker:{user_id}] Job {job_id} FAILED: {err_msg}")
            await JobManager.mark_failed(job_id, err_msg)

            # Mark as failed for UI
            await _set_progress(job_id, user_id, JobStatus.FAILED, 1.0)

        finally:
            # Always remove this job from the running set
            await redis_client.srem(GLOBAL_RUNNING_JOBS, job_id)

            # Only remove the user from ACTIVE_USERS if they have no more running jobs
            has_other = await _user_has_other_running_jobs(user_id, job_id)
            if not has_other:
                await redis_client.srem(ACTIVE_USERS_KEY, user_id)
                print(f"[Worker:{user_id}] No more running jobs, removed from ACTIVE_USERS")