import uuid
import json
from datetime import datetime

from app.core.redis_client import redis_client
from app.models.redis_keys import (
    job_key,
    global_job_progress_key,
    global_running_jobs_key,
)
from app.schemas.jobs import JobStatus


class JobManager:

    # ======================================================
    # JOB CREATION
    # ======================================================
    @staticmethod
    async def create_job_instance(
        user_id: str,
        workflow_id: str,
        run_id: str,
        branch_id: str,
        job_template_id: str,
        input_payload: dict,
    ) -> str:

        job_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        input_payload_str = json.dumps(input_payload)

        await redis_client.hset(
            job_key(job_id),
            mapping={
                "job_id": job_id,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "branch_id": branch_id,
                "job_template_id": job_template_id,
                "user_id": user_id,

                "status": JobStatus.PENDING.value,
                "created_at": now,
                "scheduled_at": "",
                "started_at": "",
                "finished_at": "",

                "input_payload": input_payload_str,
                "output_payload": "",
                "progress": 0,
                "progress_message": "",
                "stage": "",
                "eta_seconds": "",
            }
        )

        return job_id

    # ======================================================
    # FETCH JOB
    # ======================================================
    @staticmethod
    async def get_job(job_id: str):
        data = await redis_client.hgetall(job_key(job_id))
        return data if data else None

    # ======================================================
    # UPDATE STATUS
    # ======================================================
    @staticmethod
    async def set_status(job_id: str, status: JobStatus):
        await redis_client.hset(job_key(job_id), "status", status.value)

    # ======================================================
    # SET OUTPUT
    # ======================================================
    @staticmethod
    async def set_output(job_id: str, output_payload: dict):
        output_payload_str = json.dumps(output_payload)
        await redis_client.hset(job_key(job_id), "output_payload", output_payload_str)

    # ======================================================
    # 🔥 UNIFIED PROGRESS UPDATE (LOCAL + GLOBAL)
    # ======================================================
    @staticmethod
    async def update_progress(
        job_id: str,
        progress: int,
        message: str = "",
        stage: str = "",
        eta: int | None = None,
        current: int | None = None,
        total: int | None = None,
        user_id: str | None = None,
    ):
        """
        INTERNAL JOB PROGRESS
        ----------------------
        progress: 0–100 (int)
        message: optional human-readable text
        stage: optional str label
        eta: seconds remaining

        GLOBAL PROGRESS
        ----------------
        current, total, percent computed here if provided.
        """

        # --------------------------------------------
        # 1) Update LOCAL JOB HASH
        # --------------------------------------------
        mapping = {
            "progress": progress,
            "progress_message": message,
        }
        if stage:
            mapping["stage"] = stage
        if eta is not None:
            mapping["eta_seconds"] = eta

        await redis_client.hset(job_key(job_id), mapping=mapping)

        # --------------------------------------------
        # 2) GLOBAL PROGRESS UPDATE (frontend dashboard)
        # --------------------------------------------
        if current is not None and total is not None:
            percent = float(current) / float(total) if total > 0 else 0.0
        else:
            # fallback: use 0–100 progress
            percent = progress / 100.0

        # We require user_id for the global panel.
        if user_id is None:
            job = await redis_client.hgetall(job_key(job_id))
            user_id = job.get("user_id", "unknown")

        global_payload = {
            "job_id": job_id,
            "user_id": user_id,
            "status": "RUNNING",
            "current": current if current is not None else progress,
            "total": total if total is not None else 100,
            "percent": percent,
            "message": message,
            "stage": stage,
            "eta_seconds": eta,
            "updated_at": datetime.utcnow().isoformat(),
        }

        await redis_client.hset(
            global_job_progress_key(),
            job_id,
            json.dumps(global_payload)
        )

    # ======================================================
    # NEW: MARK RUNNING
    # ======================================================
    @staticmethod
    async def mark_running(job_id: str):
        now = datetime.utcnow().isoformat()

        await redis_client.hset(
            job_key(job_id),
            mapping={
                "status": JobStatus.RUNNING.value,
                "started_at": now,
                "scheduled_at": now,   # optional: scheduler timestamp
            }
        )

    # ======================================================
    # NEW: MARK SUCCESS
    # ======================================================
    @staticmethod
    async def mark_success(job_id: str, output_payload: dict | None):
        now = datetime.utcnow().isoformat()

        await redis_client.hset(
            job_key(job_id),
            mapping={
                "status": JobStatus.SUCCESS.value,
                "finished_at": now,
                "output_payload": json.dumps(output_payload or {}),
                "progress": 100,
                "stage": "completed",
            }
        )

    # ======================================================
    # NEW: MARK FAILED
    # ======================================================
    @staticmethod
    async def mark_failed(job_id: str, error_message: str):
        now = datetime.utcnow().isoformat()

        await redis_client.hset(
            job_key(job_id),
            mapping={
                "status": JobStatus.FAILED.value,
                "finished_at": now,
                "progress_message": error_message,
                "stage": "failed",
                "progress": 100,
            }
        )
