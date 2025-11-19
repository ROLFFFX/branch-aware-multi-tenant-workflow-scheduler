import uuid
from typing import List, Dict, Any

from app.core.redis_client import redis_client
from app.services.job_manager import JobManager
from app.services.branch_manager import BranchManager
from app.services.workflow_manager import WorkflowManager
from app.models.redis_keys import (
    workflow_runs_key,
    workflow_run_jobs_key,
    GLOBAL_PENDING_JOBS,
    slide_key,
)


class ExecutionManager:
    @staticmethod
    async def execute_workflow(workflow_id: str):
        """
        Expand workflow → create job instances → enqueue them into GLOBAL_PENDING_JOBS.
        Scheduler will pick them up.
        """

        # 1) Load workflow metadata
        workflow = await WorkflowManager.get_workflow(workflow_id)
        if workflow is None:
            return None

        user_id = workflow["owner_user_id"]

        # 2) Create new run
        run_id = str(uuid.uuid4())
        await redis_client.sadd(workflow_runs_key(workflow_id), run_id)

        created_jobs: List[str] = []

        # 3) Iterate branches
        branches = await BranchManager.list_branches(workflow_id)

        for branch_id in branches:
            job_specs: List[Dict[str, Any]] = await BranchManager.get_branch_jobs(
                workflow_id, branch_id
            )

            # -------------------------------------------------------------
            # For each job template in branch → convert to job instance
            # -------------------------------------------------------------
            for job_spec in job_specs:

                template_id = job_spec.get("template_id")
                payload = job_spec.get("input_payload", {})

                # =========================================================
                # PATCH: Expand WSI job template with real slide metadata
                # =========================================================
                if template_id in ("init_wsi", "wsi_initialize"):
                    slide_id = payload.get("slide_id")
                    if not slide_id:
                        raise Exception("init_wsi template requires slide_id")

                    # Load slide metadata from Redis
                    meta = await redis_client.hgetall(slide_key(slide_id))
                    if not meta:
                        raise Exception(f"Slide metadata missing for {slide_id}")

                    slide_path = meta.get("slide_path")
                    if not slide_path:
                        raise Exception(f"slide_path missing for slide {slide_id}")

                    # Construct final payload expected by job
                    payload = {
                        "slide_id": slide_id,
                        "slide_path": slide_path,
                        "tile_size": payload.get("tile_size", 1024),
                        "overlap": payload.get("overlap", 128),
                        "min_tile": payload.get("min_tile", 512),
                        "max_tile": payload.get("max_tile", 1536),
                    }

                # =========================================================
                # Create job instance in Redis (status = PENDING)
                # =========================================================
                job_id = await JobManager.create_job_instance(
                    user_id=user_id,
                    workflow_id=workflow_id,
                    run_id=run_id,
                    branch_id=branch_id,
                    job_template_id=template_id,
                    input_payload=payload,
                )

                created_jobs.append(job_id)

                # Track job under this workflow run
                await redis_client.rpush(
                    workflow_run_jobs_key(workflow_id, run_id),
                    job_id,
                )

                # Add to global scheduler pending queue
                await redis_client.rpush(GLOBAL_PENDING_JOBS, job_id)

        return {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "job_ids": created_jobs,
        }
