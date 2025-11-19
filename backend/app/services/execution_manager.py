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
)


class ExecutionManager:
    @staticmethod
    async def execute_workflow(workflow_id: str):
        """
        Expand workflow → create job instances → enqueue them into GLOBAL_PENDING_JOBS.
        Scheduler will later pick them up and execute with max concurrency.
        """

        # 1) Get workflow + owner
        workflow = await WorkflowManager.get_workflow(workflow_id)
        if workflow is None:
            return None

        user_id = workflow["owner_user_id"]

        # 2) New run_id for this workflow execution
        run_id = str(uuid.uuid4())
        await redis_client.sadd(workflow_runs_key(workflow_id), run_id)

        created_jobs: List[str] = []

        # 3) Iterate over branches and job specs
        branches = await BranchManager.list_branches(workflow_id)

        for branch_id in branches:
            job_specs: List[Dict[str, Any]] = await BranchManager.get_branch_jobs(
                workflow_id, branch_id
            )

            for job_spec in job_specs:
                template_id = job_spec.get("template_id")
                input_payload = job_spec.get("input_payload", {})

                # Create a job instance (status=PENDING)
                job_id = await JobManager.create_job_instance(
                    user_id=user_id,
                    workflow_id=workflow_id,
                    run_id=run_id,
                    branch_id=branch_id,
                    job_template_id=template_id,
                    input_payload=input_payload,
                )

                created_jobs.append(job_id)

                # Track job under this workflow run
                await redis_client.rpush(
                    workflow_run_jobs_key(workflow_id, run_id),
                    job_id,
                )

                # Push into global scheduler queue (NOT user queue)
                await redis_client.rpush(GLOBAL_PENDING_JOBS, job_id)

        return {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "job_ids": created_jobs,
        }
