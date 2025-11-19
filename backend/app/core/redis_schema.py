from app.core.redis_client import redis_client
from app.models.redis_keys import (
    users_key, active_users_key
)

async def initialize_redis_schema():
    '''
        Init redis keys & data. Called upon FastAPI startup.
    '''
    exists_users = await redis_client.exists(users_key())
    if not exists_users:
        await redis_client.sadd(users_key(), "__init__")
        await redis_client.srem(users_key(), "__init__")
        print("[Redis Schema] Init users set.")
        
    # ensure active_users set exists
    exists_active = await redis_client.exists(active_users_key())
    if not exists_active:
        await redis_client.sadd(active_users_key(), "__init__")
        await redis_client.srem(active_users_key(), "__init__")
        print("[Redis Schema] Init active_users set.")
    
    print("[Redis Schema] Init completed")