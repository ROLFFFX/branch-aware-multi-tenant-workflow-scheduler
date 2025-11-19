from app.core.redis_client import redis_client
from app.models.redis_keys import (
    users_key,
    user_key,
    active_users_key,
    user_queue_key,
    user_running_jobs_key
)
from app.services.workflow_manager import WorkflowManager
from app.services.branch_manager import BranchManager

class UserManager:
    @staticmethod
    async def register_user(user_id: str):
        '''
            Register new user if not already registered.
        '''
        await redis_client.sadd(users_key(), user_id)
        await redis_client.hsetnx(user_key(user_id), "status", "idle")
        
    @staticmethod
    async def delete_user(user_id: str) -> bool:
        '''
            Delete user. remove from global user set/active users/metadata hash/running-jobs count
        '''
        exists = await redis_client.sismember(users_key(), user_id)
        if not exists:
            return False

        # 2. Get all workflows owned by this user
        workflows = await WorkflowManager.list_workflows_by_user(user_id)

        for wf in workflows:
            wf_id = wf["workflow_id"]

            # 2a. Delete all branches under workflow
            branches = await BranchManager.list_branches(wf_id)
            for branch_id in branches:
                # BranchManager.delete_branch already deletes:
                #   - branch metadata
                #   - job list under branch
                await BranchManager.delete_branch(wf_id, branch_id)

            # 2b. Delete workflow metadata
            await WorkflowManager.delete_workflow(wf_id)

        # 3. Delete user's job execution queue
        await redis_client.delete(user_queue_key(user_id))

        # 4. Delete user's executed job instances (optional safety)
        # NOTE: If you used job:<id> format and want per-user job cleanup:
        pattern = f"job:*:{user_id}"
        async for key in redis_client.scan_iter(pattern):
            await redis_client.delete(key)

        # 5. Remove user from global user sets
        await redis_client.srem(users_key(), user_id)
        await redis_client.srem(active_users_key(), user_id)

        # 6. Remove user metadata & counters
        await redis_client.delete(user_key(user_id))
        await redis_client.delete(user_running_jobs_key(user_id))

        return True
        
    @staticmethod
    async def is_registered(user_id: str) -> bool:
        return await redis_client.sismember(users_key(), user_id)
    
    @staticmethod
    async def get_active_users_count() -> int:
        return await redis_client.scard(active_users_key())
    
    @staticmethod
    async def is_user_active(user_id: str) -> bool:
        return await redis_client.sismember(active_users_key(), user_id)
    
    @staticmethod
    async def activate_user(user_id: str) -> bool:
        '''
            Activates a user if the active-users limit (<=3) allows; 
            Returns True upon activation success.
        '''
        count = await UserManager.get_active_users_count()
        if count >= 3:
            return False
        
        await redis_client.sadd(active_users_key(), user_id)
        await redis_client.hset(user_key(user_id), "status", "running")
        await redis_client.set(user_running_jobs_key(user_id), 0)
        return True
    
    @staticmethod
    async def increment_running_jobs(user_id: str):
        await redis_client.incr(user_running_jobs_key(user_id))
        
    @staticmethod
    async def decrement_running_jobs(user_id: str):
        '''
            Decrease running job count; if user has no running job left, remove from active users and mark idle.
        '''
        value = await redis_client.decr(user_running_jobs_key(user_id))
        if value < 0:
            await redis_client.set(user_running_jobs_key(user_id), 0)   # reset to 0
            
            # set idle to deactivated users
            await redis_client.srem(active_users_key(), user_id)
            await redis_client.hset(user_key(user_id), "status", "idle")

    @staticmethod
    async def get_user_status(user_id: str):
        return await redis_client.hgetall(user_key(user_id))
    
    @staticmethod
    async def get_all_users():
        return await redis_client.smembers(users_key())
    
    