import redis
import os

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = 6379

def get_redis_connection():
    try:
        # We use decode_responses=True so we get Strings back, not Bytes
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping()
        return r
    except redis.ConnectionError:
        print(f"Error: Cannot connect to Redis at {REDIS_HOST}:{REDIS_PORT}")
        return None