"""
Production-ready rate limiting with Redis backend.
Phase 2: Distributed rate limiting for multi-instance deployments.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    from redis.exceptions import RedisError

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis not installed, RedisRateLimitMiddleware not available")

if REDIS_AVAILABLE:
    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
    from starlette.types import ASGIApp

    class RedisRateLimitMiddleware(BaseHTTPMiddleware):
        """
        Production rate limiting with Redis backend.
        Implements sliding window with Lua scripts for atomicity.
        """

        # Lua script for atomic rate limit check and increment
        LUA_SCRIPT = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])

        -- Remove old entries
        redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

        -- Count current entries
        local current = redis.call('ZCARD', key)

        if current < limit then
            -- Add new entry
            redis.call('ZADD', key, now, now)
            redis.call('EXPIRE', key, window)
            return {1, limit - current - 1}
        else
            -- Get oldest entry to calculate retry-after
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            local retry_after = 0
            if oldest[2] then
                retry_after = math.ceil(oldest[2] + window - now)
            end
            return {0, retry_after}
        end
        """

        def __init__(
            self,
            app: ASGIApp,
            redis_client: Redis,
            default_limit: int = 60,
            window_seconds: int = 60,
            key_prefix: str = "rate_limit",
            enable_user_limits: bool = True,
            user_limit_multiplier: float = 2.0,
            excluded_paths: Optional[set] = None,
        ):
            super().__init__(app)
            self.redis = redis_client
            self.default_limit = default_limit
            self.window = window_seconds
            self.key_prefix = key_prefix
            self.enable_user_limits = enable_user_limits
            self.user_multiplier = user_limit_multiplier
            self.excluded_paths = excluded_paths or {
                "/health",
                "/metrics",
                "/docs",
                "/openapi.json",
                "/favicon.ico",
            }

            # Register Lua script
            self._script_sha = None

            # Per-endpoint limits
            self.endpoint_limits = {
                "/api/auth/login": 5,  # 5 per minute
                "/api/auth/register": 10,  # 10 per minute
                "/api/password-reset": 3,  # 3 per minute
                "/api/upload": 20,  # 20 per minute
            }

        async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
        ) -> Response:
            # Skip rate limiting for excluded paths
            if request.url.path in self.excluded_paths:
                return await call_next(request)

            # Get client identifier and limit
            client_id = self._get_client_id(request)
            limit = self._get_limit(request)

            # Check rate limit
            try:
                is_allowed, remaining_or_retry = await self._check_rate_limit(
                    client_id, limit, request.url.path
                )

                if not is_allowed:
                    logger.warning(
                        "rate_limit.exceeded",
                        client=client_id,
                        path=request.url.path,
                        retry_after=remaining_or_retry,
                    )

                    return Response(
                        content=json.dumps(
                            {
                                "error": "Rate limit exceeded",
                                "retry_after": remaining_or_retry,
                            }
                        ),
                        status_code=429,
                        headers={
                            "Retry-After": str(remaining_or_retry),
                            "X-RateLimit-Limit": str(limit),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(
                                int(time.time()) + remaining_or_retry
                            ),
                        },
                        media_type="application/json",
                    )

                # Process request
                response = await call_next(request)

                # Add rate limit headers
                response.headers.update(
                    {
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": str(remaining_or_retry),
                        "X-RateLimit-Reset": str(int(time.time()) + self.window),
                    }
                )

                return response

            except RedisError as e:
                # Redis failure - log and fail open
                logger.error(
                    "rate_limit.redis_error",
                    error=str(e),
                    client=client_id,
                    path=request.url.path,
                )

                # Fail open - allow request but log the issue
                return await call_next(request)

        async def _check_rate_limit(
            self, client_id: str, limit: int, path: str
        ) -> tuple[bool, int]:
            """Check rate limit using Redis with Lua script."""

            key = f"{self.key_prefix}:{client_id}:{path}"
            now = time.time()

            # Load script if not cached
            if not self._script_sha:
                self._script_sha = await self.redis.script_load(self.LUA_SCRIPT)

            try:
                # Execute Lua script
                result = await self.redis.evalsha(
                    self._script_sha, 1, key, limit, self.window, now
                )

                is_allowed = bool(result[0])
                remaining_or_retry = int(result[1])

                return is_allowed, remaining_or_retry

            except redis.NoScriptError:
                # Script not in cache, reload it
                self._script_sha = await self.redis.script_load(self.LUA_SCRIPT)
                return await self._check_rate_limit(client_id, limit, path)

        def _get_client_id(self, request: Request) -> str:
            """Generate unique client identifier."""

            # Start with IP address
            ip = "unknown"
            if request.client:
                ip = request.client.host

            # Check for proxy headers
            if forwarded := request.headers.get("x-forwarded-for"):
                ip = forwarded.split(",")[0].strip()
            elif real_ip := request.headers.get("x-real-ip"):
                ip = real_ip

            # Include user ID if authenticated
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                return f"user:{user_id}"

            # Hash IP for privacy
            return f"ip:{hashlib.sha256(ip.encode()).hexdigest()[:16]}"

        def _get_limit(self, request: Request) -> int:
            """Get rate limit for the request."""

            # Check endpoint-specific limits
            path = request.url.path
            if path in self.endpoint_limits:
                limit = self.endpoint_limits[path]
            else:
                limit = self.default_limit

            # Increase limit for authenticated users
            if self.enable_user_limits:
                user_id = getattr(request.state, "user_id", None)
                if user_id:
                    limit = int(limit * self.user_multiplier)

            # Check for custom limits based on user tier
            user_tier = getattr(request.state, "user_tier", None)
            if user_tier:
                tier_multipliers = {
                    "free": 1.0,
                    "basic": 2.0,
                    "pro": 5.0,
                    "enterprise": 10.0,
                }
                multiplier = tier_multipliers.get(user_tier, 1.0)
                limit = int(limit * multiplier)

            return limit
