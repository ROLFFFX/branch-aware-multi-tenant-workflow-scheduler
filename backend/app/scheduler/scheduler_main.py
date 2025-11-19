import asyncio
import json
from datetime import datetime

from app.core.redis_client import redis_client
from app.models.redis_keys import GLOBAL_PENDING_JOBS, job_key, scheduler_state_key
from app.workers.registry import JOB_REGISTRY
from app.schemas.jobs import JobStatus
from app.services.job_manager import JobManager

import app.jobs.wsi_initialize
import app.jobs.fake_sleep

MAX_CONCURRENT_JOBS = 10


async def _execute_single_job(job_id: str, semaphore: asyncio.Semaphore):
    """
    Execute a single job under a concurrency semaphore.
    """
    async with semaphore:
        # Load job data
        data = await JobManager.get_job(job_id)
        if not data:
            print(f"[Scheduler] Job {job_id} not found in Redis.")
            return

        template_name = data.get("job_template_id")
        raw_payload = data.get("input_payload", "{}")

        # robust double-decode protection
        try:
            payload = json.loads(raw_payload)
            if isinstance(payload, str):          # <- if still string → decode again
                payload = json.loads(payload)
        except Exception:
            payload = {}

        # Look up job function
        func = JOB_REGISTRY.get(template_name)
        if func is None:
            print(f"[Scheduler] No job registered for template '{template_name}'")
            await redis_client.hset(
                job_key(job_id),
                mapping={
                    "status": JobStatus.FAILED.value,
                    "finished_at": datetime.utcnow().isoformat(),
                    "output_payload": json.dumps({"error": f"Unknown template: {template_name}"}),
                },
            )
            return

        # Mark as RUNNING
        await redis_client.hset(
            job_key(job_id),
            mapping={
                "status": JobStatus.RUNNING.value,
                "started_at": datetime.utcnow().isoformat(),
            },
        )

        try:
            # Call the async job function
            result = await func(job_id, payload)

            await redis_client.hset(
                job_key(job_id),
                mapping={
                    "status": JobStatus.SUCCESS.value,
                    "finished_at": datetime.utcnow().isoformat(),
                    "output_payload": json.dumps(result or {}),
                },
            )

            print(f"[Scheduler] Job {job_id} completed successfully.")

        except Exception as e:
            await redis_client.hset(
                job_key(job_id),
                mapping={
                    "status": JobStatus.FAILED.value,
                    "finished_at": datetime.utcnow().isoformat(),
                    "output_payload": json.dumps({"error": str(e)}),
                },
            )
            print(f"[Scheduler] Job {job_id} failed: {e}")


async def scheduler_loop():
    """
    Global scheduler:
    - Watches GLOBAL_PENDING_JOBS
    - Respects scheduler:state (running / paused)
    - Limits concurrent job executions via a semaphore
    """
    print("[Scheduler] Loop started.")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

    while True:
        state = await redis_client.get(scheduler_state_key())
        if state is None:
            # default to paused on first run
            await redis_client.set(scheduler_state_key(), "paused")
            state = "paused"

        if state != "running":
            # Scheduler is paused; don't pull new jobs
            await asyncio.sleep(0.5)
            continue

        # BLPOP with timeout so we can re-check state regularly
        result = await redis_client.blpop(GLOBAL_PENDING_JOBS, timeout=1)
        if not result:
            # nothing popped, loop again
            continue

        _, job_id = result
        print(f"[Scheduler] Dispatching job {job_id}")

        # Fire-and-forget: job concurrency is controlled by the semaphore
        asyncio.create_task(_execute_single_job(job_id, semaphore))

if __name__ == "__main__":
    print("[Scheduler] Starting scheduler...")
    try:
        asyncio.run(scheduler_loop())
    except KeyboardInterrupt:
        print("[Scheduler] Stopped.")