"""
Distributed Rate Limiter using Redis.
Works across multiple workers/processes.
"""
import redis
import time
import logging
from typing import Optional
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisRateLimiter:
    """
    Distributed rate limiter using Redis.
    Implements sliding window algorithm.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self._client: Optional[redis.Redis] = None
        self.window_size = settings.rate_limit_window
        self.max_requests = settings.rate_limit_max_requests

    @property
    def client(self) -> redis.Redis:
        """Lazy initialization of Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        return self._client

    def _get_key(self, identifier: str, action: str = "login") -> str:
        """Generate Redis key for rate limiting."""
        return f"rate_limit:{action}:{identifier}"

    def is_allowed(self, identifier: str, action: str = "login") -> bool:
        """
        Check if a request is allowed under rate limit.

        Args:
            identifier: Unique identifier (e.g., IP address, user ID)
            action: Action being rate limited (e.g., "login", "api")

        Returns:
            True if request is allowed, False if rate limited
        """
        key = self._get_key(identifier, action)
        current_time = time.time()
        window_start = current_time - self.window_size

        try:
            pipe = self.client.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            pipe.zcard(key)

            # Add current request with timestamp as score
            pipe.zadd(key, {str(current_time): current_time})

            # Set expiry on the key
            pipe.expire(key, self.window_size + 10)

            results = pipe.execute()
            current_count = results[1]

            if current_count >= self.max_requests:
                logger.warning(f"Rate limit exceeded for {identifier} on {action}")
                return False

            return True

        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # Fail open - allow request if Redis is unavailable
            return True

    def get_remaining(self, identifier: str, action: str = "login") -> int:
        """Get remaining requests in current window."""
        key = self._get_key(identifier, action)
        current_time = time.time()
        window_start = current_time - self.window_size

        try:
            # Clean old entries and count
            pipe = self.client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = pipe.execute()
            current_count = results[1]

            return max(0, self.max_requests - current_count)

        except redis.RedisError as e:
            logger.error(f"Redis error getting remaining: {e}")
            return self.max_requests

    def get_reset_time(self, identifier: str, action: str = "login") -> int:
        """Get seconds until rate limit resets."""
        key = self._get_key(identifier, action)

        try:
            # Get oldest entry in window
            oldest = self.client.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                reset_time = int(oldest_time + self.window_size - time.time())
                return max(0, reset_time)
            return 0

        except redis.RedisError as e:
            logger.error(f"Redis error getting reset time: {e}")
            return self.window_size

    def reset(self, identifier: str, action: str = "login") -> bool:
        """Reset rate limit for an identifier."""
        key = self._get_key(identifier, action)
        try:
            self.client.delete(key)
            return True
        except redis.RedisError as e:
            logger.error(f"Redis error resetting rate limit: {e}")
            return False


# Global rate limiter instance
_rate_limiter: Optional[RedisRateLimiter] = None


def get_rate_limiter() -> RedisRateLimiter:
    """Get or create rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimiter()
    return _rate_limiter
