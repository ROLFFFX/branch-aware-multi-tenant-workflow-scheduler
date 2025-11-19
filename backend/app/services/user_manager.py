from app.core.redis_client import redis_client
from app.models.redis_keys import (
    users_key,
    user_key,
    active_users_key,
    user_running_jobs_key
)

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
            @todo: cases for running jobs, do we also decrease job count, branch count, workflow count etc.
        '''
        removed = await redis_client.srem(users_key(), user_id)
        if removed == 0:
            return False
        
        await redis_client.srem(active_users_key(), user_id)
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
    
    