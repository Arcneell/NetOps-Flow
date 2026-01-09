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

    # Action-specific rate limits (max_requests, window_size in seconds)
    ACTION_LIMITS = {
        "login": (5, 60),           # 5 requests per minute (brute force protection)
        "mfa": (5, 60),             # 5 MFA attempts per minute
        "settings_update": (50, 60), # 50 settings updates per minute (batch saves)
        "api": (100, 60),           # 100 API calls per minute
    }

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self._client: Optional[redis.Redis] = None
        self.default_window_size = settings.rate_limit_window
        self.default_max_requests = settings.rate_limit_max_requests

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

    def _get_limits(self, action: str) -> tuple:
        """Get rate limits for a specific action."""
        if action in self.ACTION_LIMITS:
            return self.ACTION_LIMITS[action]
        return (self.default_max_requests, self.default_window_size)

    def is_allowed(self, identifier: str, action: str = "login") -> bool:
        """
        Check if a request is allowed under rate limit.

        Uses atomic Lua script to prevent TOCTOU race conditions.

        Args:
            identifier: Unique identifier (e.g., IP address, user ID)
            action: Action being rate limited (e.g., "login", "api")

        Returns:
            True if request is allowed, False if rate limited
        """
        max_requests, window_size = self._get_limits(action)
        key = self._get_key(identifier, action)
        current_time = time.time()
        window_start = current_time - window_size

        # Lua script for atomic rate limiting (prevents TOCTOU race condition)
        # 1. Remove old entries
        # 2. Add current request
        # 3. Count entries AFTER adding (atomic check)
        # 4. Set expiry
        # Returns the count AFTER adding the new request
        lua_script = """
        local key = KEYS[1]
        local window_start = tonumber(ARGV[1])
        local current_time = tonumber(ARGV[2])
        local max_requests = tonumber(ARGV[3])
        local window_size = tonumber(ARGV[4])

        -- Remove old entries outside the window
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

        -- Add current request with timestamp as score
        redis.call('ZADD', key, current_time, tostring(current_time))

        -- Count AFTER adding (atomic)
        local count = redis.call('ZCARD', key)

        -- Set expiry
        redis.call('EXPIRE', key, window_size + 10)

        return count
        """

        try:
            # Execute atomic Lua script
            current_count = self.client.eval(
                lua_script,
                1,  # Number of keys
                key,  # KEYS[1]
                window_start,  # ARGV[1]
                current_time,  # ARGV[2]
                max_requests,  # ARGV[3]
                window_size   # ARGV[4]
            )

            if current_count > max_requests:
                logger.warning(f"Rate limit exceeded for {identifier} on {action}")
                return False

            return True

        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # Fail open - allow request if Redis is unavailable
            return True

    def get_remaining(self, identifier: str, action: str = "login") -> int:
        """Get remaining requests in current window."""
        max_requests, window_size = self._get_limits(action)
        key = self._get_key(identifier, action)
        current_time = time.time()
        window_start = current_time - window_size

        try:
            # Clean old entries and count
            pipe = self.client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = pipe.execute()
            current_count = results[1]

            return max(0, max_requests - current_count)

        except redis.RedisError as e:
            logger.error(f"Redis error getting remaining: {e}")
            return max_requests

    def get_reset_time(self, identifier: str, action: str = "login") -> int:
        """Get seconds until rate limit resets."""
        _, window_size = self._get_limits(action)
        key = self._get_key(identifier, action)

        try:
            # Get oldest entry in window
            oldest = self.client.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                reset_time = int(oldest_time + window_size - time.time())
                return max(0, reset_time)
            return 0

        except redis.RedisError as e:
            logger.error(f"Redis error getting reset time: {e}")
            return window_size

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
