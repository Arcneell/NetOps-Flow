"""
Redis caching utilities for API responses.
"""
import json
import logging
from typing import Optional, Any, Callable
from functools import wraps
import redis

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Redis client singleton
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client instance."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis cache connection established")
        except redis.ConnectionError as e:
            logger.warning(f"Redis cache unavailable: {e}")
            _redis_client = None
        except Exception as e:
            logger.error(f"Redis cache error: {e}")
            _redis_client = None
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    """
    Get a value from Redis cache.

    Args:
        key: Cache key

    Returns:
        Cached value (deserialized from JSON) or None if not found/error
    """
    client = get_redis_client()
    if not client:
        return None

    try:
        cached = client.get(key)
        if cached:
            return json.loads(cached)
        return None
    except Exception as e:
        logger.warning(f"Cache get error for key {key}: {e}")
        return None


def cache_set(key: str, value: Any, expire_seconds: int = 300) -> bool:
    """
    Set a value in Redis cache.

    Args:
        key: Cache key
        value: Value to cache (must be JSON serializable)
        expire_seconds: Time to live in seconds (default: 5 minutes)

    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        client.setex(key, expire_seconds, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.warning(f"Cache set error for key {key}: {e}")
        return False


def cache_delete(key: str) -> bool:
    """
    Delete a value from Redis cache.

    Args:
        key: Cache key

    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete error for key {key}: {e}")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching a pattern.

    Args:
        pattern: Redis key pattern (e.g., "dashboard:*")

    Returns:
        Number of keys deleted
    """
    client = get_redis_client()
    if not client:
        return 0

    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"Cache delete pattern error for {pattern}: {e}")
        return 0


def invalidate_dashboard_cache():
    """Invalidate all dashboard-related caches."""
    cache_delete_pattern("dashboard:*")


def invalidate_topology_cache():
    """Invalidate all topology-related caches."""
    cache_delete_pattern("topology:*")


# Cache key builders
def build_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Build a cache key from prefix and arguments.

    Args:
        prefix: Key prefix (e.g., "dashboard", "topology")
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key

    Returns:
        Cache key string
    """
    parts = [prefix]
    for arg in args:
        parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        if v is not None:
            parts.append(f"{k}={v}")
    return ":".join(parts)
