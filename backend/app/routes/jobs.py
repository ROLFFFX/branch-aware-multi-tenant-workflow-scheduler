import json
from fastapi import APIRouter, HTTPException
from app.services.job_manager import JobManager
from app.schemas.jobs import JobInstance
from app.workers.registry import JOB_REGISTRY


router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/job-templates")
async def list_job_templates():
    return list(JOB_REGISTRY.keys())


@router.get("/{job_id}", response_model=JobInstance)
async def get_job(job_id: str):
    data = await JobManager.get_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    input_payload_raw = data.get("input_payload")
    output_payload_raw = data.get("output_payload")

    try:
        data["input_payload"] = (
            json.loads(input_payload_raw) if isinstance(input_payload_raw, str) else input_payload_raw
        )
    except Exception:
        data["input_payload"] = {}

    try:
        data["output_payload"] = (
            json.loads(output_payload_raw) if isinstance(output_payload_raw, str) and output_payload_raw else {}
        )
    except Exception:
        data["output_payload"] = {}

    return JobInstance(**data)

