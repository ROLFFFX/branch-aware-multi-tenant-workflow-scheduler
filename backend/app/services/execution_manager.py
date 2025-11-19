import uuid
import json # You need this for the payload if handling raw data elsewhere
from typing import List, Dict, Any

from app.core.redis_client import redis_client
from app.services.job_manager import JobManager
from app.services.branch_manager import BranchManager
from app.services.workflow_manager import WorkflowManager
from app.models.redis_keys import (
    workflow_runs_key,
    workflow_run_jobs_key,
    GLOBAL_PENDING_JOBS,
    slide_key, # Used for WSI hydration
)


class ExecutionManager:
    @staticmethod
    async def execute_workflow(workflow_id: str):
        # 1) Load workflow metadata
        workflow = await WorkflowManager.get_workflow(workflow_id)
        if workflow is None:
            return None

        user_id = workflow["owner_user_id"]

        # 2) Create new run
        run_id = str(uuid.uuid4())
        # Note: You should be using rpush or sadd/hset to store the run status, 
        # but using sadd as you did previously is sufficient for ID tracking.
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
                
                # --- START OF RESILIENT JOB PROCESSING ---
                try:
                    template_id = job_spec.get("template_id")
                    # Start with the payload defined in the job spec
                    payload = job_spec.get("input_payload", {}) 

                    # =========================================================
                    # PATCH: Expand WSI job template with real slide metadata
                    # =========================================================
                    # FIX 1: Ensure template_id matches the one added in curl
                    if template_id == "wsi_metadata": 
                        slide_id = payload.get("slide_id")
                        if not slide_id:
                            # RAISE the error so the outer EXCEPT block can catch it.
                            raise ValueError("Job wsi_metadata requires 'slide_id' in payload.")

                        # Load slide metadata from Redis
                        meta = await redis_client.hgetall(slide_key(slide_id))
                        if not meta:
                            raise ValueError(f"Slide metadata missing for {slide_id}")

                        # Handle bytes decoding (Redis data is often bytes)
                        slide_path = meta.get(b"slide_path") or meta.get("slide_path")
                        if isinstance(slide_path, bytes):
                            slide_path = slide_path.decode("utf-8")
                            
                        if not slide_path:
                            raise ValueError(f"slide_path missing for slide {slide_id}")

                        # Construct final payload (merging with existing data)
                        payload["slide_path"] = slide_path
                        # You can add other WSI params here if needed

                    # =========================================================
                    # Create job instance in Redis (status = PENDING)
                    # =========================================================
                    # FIX 2: Correctly pass all required arguments to JobManager
                    job_id = await JobManager.create_job_instance(
                        user_id=user_id,
                        workflow_id=workflow_id,
                        run_id=run_id,
                        branch_id=branch_id,
                        job_template_id=template_id,
                        input_payload=payload, # Use the hydrated payload
                    )

                    created_jobs.append(job_id)

                    # Queueing MUST BE inside the try block
                    await redis_client.rpush(
                        workflow_run_jobs_key(workflow_id, run_id), job_id
                    )
                    await redis_client.rpush(GLOBAL_PENDING_JOBS, job_id)
                    
                    print(f"SUCCESS: Queued job {job_id}")

                except Exception as e:
                    # Catch the error, log it (including the ID), and continue
                    print(f"ERROR: Failed to process job spec ({template_id}). Error: {e}")
                    # CRITICAL: This allows the execution to continue to the next job
                    continue 

        return {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "job_ids": created_jobs,
        }