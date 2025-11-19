'''
    Note that "workflow" is defined as the "dummy_node" for branches. 
    User could have multiple "workflows", as he/she could have multiple branches.
    Think of it as a special kind of branch node.
'''

from typing import Optional, Dict, Any, List
from app.services.branch_manager import BranchManager


from app.core.redis_client import redis_client
from app.models.redis_keys import (
    workflows_key,
    workflow_key,
    workflow_branches_key,
    workflow_branch_key
)


class WorkflowManager:
    @staticmethod
    async def create_workflow(workflow_id: str, name: str, owner_user_id: str):
        """
        Create workflow metadata AND auto-create default branch 'default'.
        """
        # Check if workflow already exists
        exists = await redis_client.exists(f"workflow:{workflow_id}")
        if exists:
            return False

        DEFAULT_BRANCH = "default"

        # Write workflow metadata
        workflow_data = {
            "workflow_id": workflow_id,
            "name": name,
            "owner_user_id": owner_user_id,
            "entry_branch": DEFAULT_BRANCH,
        }

        await redis_client.hset(f"workflow:{workflow_id}", mapping=workflow_data)
        await redis_client.sadd(workflows_key(), workflow_id)


        # Create the default branch
        await BranchManager.create_branch(workflow_id, DEFAULT_BRANCH)

        return True


    @staticmethod
    async def workflow_exists(workflow_id: str) -> bool:
        return await redis_client.sismember(workflows_key(), workflow_id)

    @staticmethod
    async def get_workflow(workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Return workflow metadata dict
        """
        meta = await redis_client.hgetall(workflow_key(workflow_id))
        if not meta:
            return None
        meta["workflow_id"] = workflow_id
        return meta

    @staticmethod
    async def delete_workflow(workflow_id: str) -> bool:
        """
        Delete a workflow and its metadata.
        TODO: also clean up branches / runs / job instances later.
        """
        removed = await redis_client.srem(workflows_key(), workflow_id)
        if removed == 0:
            return False

        await redis_client.delete(workflow_key(workflow_id))
        await redis_client.delete(workflow_branches_key(workflow_id))
        # Note: clean up branch keys separately if needed
        return True

    @staticmethod
    async def list_workflows() -> List[Dict[str, Any]]:
        ids = await redis_client.smembers(workflows_key())
        result: List[Dict[str, Any]] = []

        for wf_id in ids:
            meta = await redis_client.hgetall(workflow_key(wf_id))
            if meta:
                meta["workflow_id"] = wf_id
                result.append(meta)

        return result

    @staticmethod
    async def list_workflows_by_user(user_id: str):
        workflow_ids = await redis_client.smembers(workflows_key())
        result = []

        for wf_id in workflow_ids:
            meta = await redis_client.hgetall(workflow_key(wf_id))
            if meta and meta.get("owner_user_id") == user_id:
                meta["workflow_id"] = wf_id
                result.append(meta)

        return result
