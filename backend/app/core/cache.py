import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("cache")

# Try to import Redis
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class CacheEntry:
    """Cache entry with expiration"""

    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        self.hits = 0
        self.created_at = datetime.now()

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def hit(self):
        self.hits += 1


class SimpleCache:
    """Simple in-memory cache implementation"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
        self._max_size = 1000
        self._cleanup_interval = 300  # 5 minutes

    def _cleanup_expired(self):
        """Remove expired entries from cache"""
        now = datetime.now()
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

        for key in expired_keys:
            del self._cache[key]
            self._stats["evictions"] += 1

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        # Periodic cleanup
        if hash(key) % 100 == 0:  # Simple check every 100 gets
            self._cleanup_expired()

        entry = self._cache.get(key)

        if entry is None or entry.is_expired():
            self._stats["misses"] += 1
            return None

        entry.hit()
        self._stats["hits"] += 1
        return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set value in cache with TTL"""
        # Enforce max size
        if len(self._cache) >= self._max_size:
            self._cleanup_expired()

            if len(self._cache) >= self._max_size:
                # Remove least recently used entries
                sorted_keys = sorted(
                    self._cache.keys(), key=lambda k: self._cache[k].created_at
                )
                remove_count = len(self._cache) - self._max_size + 100
                for key in sorted_keys[:remove_count]:
                    del self._cache[key]
                    self._stats["evictions"] += 1

        self._cache[key] = CacheEntry(value, ttl_seconds)

    def get_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            **self._stats,
            "total_entries": len(self._cache),
            "hit_rate": round(hit_rate * 100, 2),
            "total_requests": total_requests,
        }

    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
        logger.info("Cache cleared")


class RedisCache:
    """Redis-based cache implementation"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            return False

        try:
            redis_url = getattr(settings, "REDIS_URL", None)
            if redis_url:
                self._client = await redis.from_url(redis_url, decode_responses=True)
                await self._client.ping()
                self._connected = True
                logger.info("Connected to Redis cache")
                return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")

        return False

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self._connected or not self._client:
            return None

        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")

        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set value in Redis cache"""
        if not self._connected or not self._client:
            return

        try:
            await self._client.setex(key, ttl_seconds, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete key from Redis"""
        if not self._connected or not self._client:
            return

        try:
            await self._client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        if not self._connected or not self._client:
            return 0

        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self._client.delete(*keys)
                return len(keys)
        except Exception as e:
            logger.warning(f"Redis clear pattern error: {e}")

        return 0


# Global cache instances
cache = SimpleCache()
redis_cache = RedisCache()


# Initialize Redis if available
async def init_cache():
    """Initialize cache (Redis if available, otherwise in-memory)"""
    await redis_cache.connect()


# Use Redis if available, otherwise fall back to in-memory cache
async def get_cache() -> Any:
    """Get the active cache instance"""
    if redis_cache._connected:
        return redis_cache
    return cache


def generate_cache_key(*args: Any, **kwargs: Any) -> str:
    """Generate a cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl_seconds: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            key = key_prefix + generate_cache_key(func.__name__, *args, **kwargs)

            # Get active cache
            active_cache = await get_cache()

            # Try to get from cache
            cached_value = await active_cache.get(key)

            if cached_value is not None:
                return cached_value

            # Call the function
            result = await func(*args, **kwargs)

            # Cache the result
            if result is not None:
                await active_cache.set(key, result, ttl_seconds)
                logger.debug(f"Cached result for {func.__name__} (TTL: {ttl_seconds}s)")

            return result

        return wrapper

    return decorator


def invalidate_pattern(pattern: str) -> None:
    """Invalidate cache entries matching a pattern"""
    import re

    regex = re.compile(pattern)
    keys_to_delete = [key for key in cache._cache.keys() if regex.match(key)]

    for key in keys_to_delete:
        del cache._cache[key]
        cache._stats["evictions"] += len(keys_to_delete)

    logger.info(
        f"Invalidated {len(keys_to_delete)} cache entries matching pattern: {pattern}"
    )


def get_cache_stats() -> Dict[str, any]:
    """Get global cache statistics"""
    return cache.get_stats()
