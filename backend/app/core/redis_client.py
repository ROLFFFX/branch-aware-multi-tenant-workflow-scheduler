import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
    max_connections=50, # prevent connection explosion under high QPS
)

async def test_redis_connection():
    try:
        pong = await redis_client.ping()
        if pong:
            print("Redis connected successfully")
    except Exception as e:
        print("Redis connection failed: ", e)