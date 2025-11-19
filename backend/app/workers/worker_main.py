import asyncio
import json
import traceback
from datetime import datetime

from app.core.redis_client import redis_client
from app.models.redis_keys import user_queue_key, job_key
from app.schemas.jobs import JobStatus
from app.workers.registry import JOB_REGISTRY
from app.services.job_manager import JobManager


async def worker_loop(user_id: str):
    """
    Dedicated worker for a specific user.
    Continuously reads job_ids from that user's queue and processes them.
    """

    queue = user_queue_key(user_id)
    print(f"[Worker for {user_id}] Started. Listening on queue: {queue}")

    while True:
        try:
            # Try to pop one job from queue
            job_id = await redis_client.lpop(queue)

            # Nothing queued → sleep and retry
            if not job_id:
                await asyncio.sleep(0.5)
                continue

            print(f"[Worker for {user_id}] Picked job {job_id}")

            # Load job hash
            job_data = await redis_client.hgetall(job_key(job_id))
            if not job_data:
                print(f"[Worker WARN] Job {job_id} missing in Redis; skipping.")
                continue

            template = job_data.get("job_template_id")
            raw_payload = job_data.get("input_payload", "")

            # Parse JSON input
            try:
                input_payload = json.loads(raw_payload or "{}")
            except Exception:
                print(f"[Worker WARN] Failed to parse input_payload for job {job_id}. Using empty dict.")
                input_payload = {}

            # Mark job as running
            await redis_client.hset(
                job_key(job_id),
                mapping={
                    "status": JobStatus.RUNNING.value,
                    "started_at": datetime.utcnow().isoformat()
                }
            )

            # Look up job implementation
            if template not in JOB_REGISTRY:
                print(f"[Worker ERROR] job template '{template}' not registered")
                await JobManager.set_status(job_id, JobStatus.FAILED)
                await JobManager.set_output(job_id, {"error": f"Unknown template: {template}"})
                continue

            func = JOB_REGISTRY[template]

            # Execute job function
            try:
                result = await func(job_id, input_payload)

                # Store success results
                await redis_client.hset(
                    job_key(job_id),
                    mapping={
                        "status": JobStatus.SUCCESS.value,
                        "output_payload": json.dumps(result or {}),
                        "finished_at": datetime.utcnow().isoformat(),
                    }
                )

                print(f"[Worker] Job {job_id} completed successfully.")

            except Exception as e:
                traceback.print_exc()
                print(f"[Worker ERROR] Job {job_id} failed: {e}")

                await redis_client.hset(
                    job_key(job_id),
                    mapping={
                        "status": JobStatus.FAILED.value,
                        "output_payload": json.dumps({"error": str(e)}),
                        "finished_at": datetime.utcnow().isoformat(),
                    }
                )

        except Exception as loop_err:
            # Catch unexpected errors that would break the worker
            traceback.print_exc()
            print(f"[Worker CRASH] Unexpected error: {loop_err}")
            await asyncio.sleep(1)  # prevent tight crash loop
