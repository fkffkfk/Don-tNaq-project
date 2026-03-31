import os
from flask_caching import Cache

cache = Cache(config={
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
    "CACHE_DEFAULT_TIMEOUT": int(os.getenv("CACHE_DEFAULT_TIMEOUT", "60")),
})