from typing import List, Dict, Any
import json

from app.core.redis_client import redis_client
from app.models.redis_keys import (
    workflow_branches_key,
    workflow_branch_key,
)


class BranchManager:
    @staticmethod
    async def create_branch(workflow_id: str, branch_id: str) -> bool:
        """
        Create new branch for a workflow. Returns False if the branch already exists.
        """
        exists = await redis_client.sismember(
            workflow_branches_key(workflow_id), branch_id
        )
        if exists:
            return False

        # register branch in workflow branches set
        await redis_client.sadd(workflow_branches_key(workflow_id), branch_id)
        # the branch job list is created lazily when the first job is added
        return True

    @staticmethod
    async def add_job_to_branch(
        workflow_id: str,
        branch_id: str,
        job_template_id: str,
        input_payload: Dict[str, Any] | None = None,
    ) -> bool:
        """
        Append a job spec to the branch's ordered job list.
        The job spec is stored as JSON:
            {
                "template_id": "<job_template_id>",
                "input_payload": { ... }
            }

        Returns False if branch does not exist.
        """
        exists = await redis_client.sismember(
            workflow_branches_key(workflow_id), branch_id
        )
        if not exists:
            return False

        job_spec = {
            "template_id": job_template_id,
            "input_payload": input_payload or {},
        }

        await redis_client.rpush(
            workflow_branch_key(workflow_id, branch_id),
            json.dumps(job_spec),
        )
        return True

    @staticmethod
    async def get_branch_jobs(workflow_id: str, branch_id: str) -> List[Dict[str, Any]]:
        """
        Return the ordered list of job specs for a branch (linear stream of jobs).

        Each job spec has the form:
            {
                "template_id": "<job_template_id>",
                "input_payload": { ... }
            }
        """
        raw_jobs = await redis_client.lrange(
            workflow_branch_key(workflow_id, branch_id),
            0,
            -1,
        )
        jobs: List[Dict[str, Any]] = []
        for j in raw_jobs:
            try:
                jobs.append(json.loads(j))
            except Exception:
                # backward compatibility: if old entries are just strings,
                # wrap them into the new structure with empty payload
                jobs.append(
                    {
                        "template_id": j,
                        "input_payload": {},
                    }
                )
        return jobs

    @staticmethod
    async def list_branches(workflow_id: str) -> List[str]:
        """
        Get branches by workflow id.
        """
        branches = await redis_client.smembers(workflow_branches_key(workflow_id))
        # Redis returns a set-like; convert to list for JSON
        return list(branches)

    @staticmethod
    async def delete_branch(workflow_id: str, branch_id: str) -> bool:
        """
        Delete branch from a workflow
            - remove branch_id from workflow:<wf_id>:branches
            - delete its job list key
        """
        removed = await redis_client.srem(
            workflow_branches_key(workflow_id), branch_id
        )
        if removed == 0:
            return False

        await redis_client.delete(workflow_branch_key(workflow_id, branch_id))
        return True
