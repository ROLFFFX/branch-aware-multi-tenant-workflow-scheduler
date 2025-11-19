import uuid
import json
from datetime import datetime
from app.core.redis_client import redis_client
from app.models.redis_keys import job_key
from app.schemas.jobs import JobStatus


class JobManager:

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

        # Serialize dict to JSON string
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
            }
        )

        return job_id

    @staticmethod
    async def get_job(job_id: str):
        data = await redis_client.hgetall(job_key(job_id))
        return data if data else None

    @staticmethod
    async def set_status(job_id: str, status: JobStatus):
        await redis_client.hset(job_key(job_id), "status", status.value)

    @staticmethod
    async def set_output(job_id: str, output_payload: dict):

        # Serialize output dict
        output_payload_str = json.dumps(output_payload)

        await redis_client.hset(
            job_key(job_id),
            "output_payload",
            output_payload_str
        )

    @staticmethod
    async def update_progress(job_id: str, progress: int, message: str = "", stage: str = "", eta: int | None = None):
        mapping = {
            "progress": progress,
            "progress_message": message,
        }

        if stage:
            mapping["stage"] = stage
        if eta is not None:
            mapping["eta_seconds"] = eta

        await redis_client.hset(job_key(job_id), mapping=mapping)
