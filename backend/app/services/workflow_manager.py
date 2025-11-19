'''
    Note that "workflow" is defined as the "dummy_node" for branches. 
    User could have multiple "workflows", as he/she could have multiple branches.
    Think of it as a special kind of branch node.
'''

from typing import Optional, Dict, Any, List

from app.core.redis_client import redis_client
from app.models.redis_keys import (
    workflows_key,
    workflow_key
)

class WorkflowManager:
    @staticmethod
    async def create_workflow(
        workflow_id: str,
        name: str,
        owner_user_id: str,
        entry_branch: Optional[str] = None,
    ) -> bool:
        '''
            Create a new workflow def.
            Returns False if workflow_id already exists.
        '''
        exists = await redis_client.sismember(workflows_key(), workflow_id)
        if exists:
            return False
        
        # register workflow id
        await redis_client.sadd(workflows_key(), workflow_id)
        
        # store workflow metadata
        fields: Dict[str, Any] = {
            "name": name,
            "owner_user_id": owner_user_id
        }
        
        if entry_branch is not None:
            fields["entry_branch"] = entry_branch
            
        await redis_client.hset(workflow_key(workflow_id), mapping = fields)
        return True
    
    @staticmethod
    async def workflow_exists(workflow_id: str) -> bool:
        return await redis_client.sismember(workflows_key(), workflow_id)
    
    @staticmethod
    async def get_workflow(workflow_id: str) -> Optional[Dict[str, Any]]:
        '''
            Get workflow as a dict if exists : None
        '''
        meta = await redis_client.hgetall(workflow_key(workflow_id))
        if not meta:
            return None
        meta["workflow_id"] = workflow_id
        return meta
    
    @staticmethod
    async def delete_workflow(workflow_id: str) -> bool:
        '''
            Delete a workflow definition
            @todo: also clean up subsequent branches / state
        '''
        removed = await redis_client.srem(workflows_key(), workflow_id)
        if removed == 0:
            return False
        await redis_client.delete(workflow_key(workflow_id))
        return True
    
    @staticmethod
    async def list_workflows() -> List[Dict[str, Any]]:
        '''
            Return list of workflow metadata dicts.
        '''
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
        '''
            Get workflows by user
        '''
        workflow_ids = await redis_client.smembers(workflows_key())
        result = []

        for wf_id in workflow_ids:
            meta = await redis_client.hgetall(workflow_key(wf_id))
            if not meta:
                continue
            if meta.get("owner_user_id") == user_id:
                meta["workflow_id"] = wf_id
                result.append(meta)

        return result
