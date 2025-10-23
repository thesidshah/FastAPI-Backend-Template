"""
Security middleware for FastAPI applications.
Phase 1: Core security features with no external dependencies.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies security headers to all responses.
    Prevents common web vulnerabilities like clickjacking, XSS, and MIME sniffing.
    """

    def __init__(
        self,
        app: ASGIApp,
        is_production: bool = False,
        enable_hsts: bool = True,
        enable_csp: bool = False,
        csp_policy: Optional[str] = None,
    ):
        super().__init__(app)
        self.is_production = is_production
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
        self.csp_policy = csp_policy or "default-src 'self'"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # Essential security headers - always apply
        response.headers.update(
            {
                # Prevent MIME type sniffing
                "X-Content-Type-Options": "nosniff",
                # Prevent clickjacking attacks
                "X-Frame-Options": "DENY",
                # Control referrer information
                "Referrer-Policy": "strict-origin-when-cross-origin",
                # Disable browser features that are commonly abused
                "Permissions-Policy": (
                    "camera=(), "
                    "microphone=(), "
                    "geolocation=(), "
                    "payment=(), "
                    "usb=(), "
                    "magnetometer=(), "
                    "gyroscope=(), "
                    "accelerometer=()"
                ),
                # Disable client-side caching for sensitive data
                "Cache-Control": "no-store, max-age=0",
                # Remove server header info
                "Server": "undisclosed",
            }
        )

        # HSTS - only in production with HTTPS
        if self.is_production and self.enable_hsts:
            if request.url.scheme == "https":
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains; preload"
                )

        # Content Security Policy - optional but recommended
        if self.enable_csp and self.is_production:
            response.headers["Content-Security-Policy"] = self.csp_policy

        return response


class ContentValidationMiddleware(BaseHTTPMiddleware):
    """
    Validates request content to prevent abuse.
    - Enforces size limits
    - Validates content types
    - Blocks suspicious payloads
    """

    # Default limits by path pattern (in bytes)
    DEFAULT_LIMITS = {
        "/api/upload": 50 * 1024 * 1024,  # 50MB for file uploads
        "/api/import": 10 * 1024 * 1024,  # 10MB for data imports
        "/api/": 1 * 1024 * 1024,  # 1MB for API calls
        "/webhook": 256 * 1024,  # 256KB for webhooks
        "/graphql": 100 * 1024,  # 100KB for GraphQL
        "/": 64 * 1024,  # 64KB default
    }

    # Allowed content types by method
    ALLOWED_CONTENT_TYPES = {
        "POST": {
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        },
        "PUT": {
            "application/json",
            "application/octet-stream",
            "multipart/form-data",
        },
        "PATCH": {
            "application/json",
            "application/merge-patch+json",
        },
    }

    def __init__(
        self,
        app: ASGIApp,
        size_limits: Optional[Dict[str, int]] = None,
        allowed_types: Optional[Dict[str, Set[str]]] = None,
        block_null_bytes: bool = True,
    ):
        super().__init__(app)
        self.size_limits = size_limits or self.DEFAULT_LIMITS
        self.allowed_types = allowed_types or self.ALLOWED_CONTENT_TYPES
        self.block_null_bytes = block_null_bytes

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip validation for GET, HEAD, OPTIONS
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        # Validate content length
        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            limit = self._get_size_limit(request.url.path)

            if size > limit:
                logger.warning(
                    "content_validation.size_exceeded",
                    path=request.url.path,
                    size=size,
                    limit=limit,
                    client=request.client.host if request.client else None,
                )
                return Response(
                    content=json.dumps(
                        {"error": "Payload too large", "max_size": limit}
                    ),
                    status_code=413,
                    media_type="application/json",
                )

        # Validate content type
        content_type = request.headers.get("content-type", "").split(";")[0].strip()
        if content_type:
            allowed = self.allowed_types.get(request.method, set())

            if allowed and content_type not in allowed:
                logger.warning(
                    "content_validation.invalid_type",
                    path=request.url.path,
                    content_type=content_type,
                    method=request.method,
                )
                return Response(
                    content=json.dumps(
                        {
                            "error": "Unsupported media type",
                            "allowed_types": list(allowed),
                        }
                    ),
                    status_code=415,
                    media_type="application/json",
                )

        # Check for null bytes in URL (path traversal attempt)
        if self.block_null_bytes and "\x00" in str(request.url):
            logger.warning(
                "content_validation.null_bytes",
                path=request.url.path,
                client=request.client.host if request.client else None,
            )
            return Response(
                content=json.dumps({"error": "Invalid request"}),
                status_code=400,
                media_type="application/json",
            )

        return await call_next(request)

    def _get_size_limit(self, path: str) -> int:
        """Get size limit for a given path."""
        for pattern, limit in self.size_limits.items():
            if path.startswith(pattern):
                return limit
        return self.size_limits.get("/", 64 * 1024)


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory rate limiting using sliding window algorithm.
    Phase 1 implementation - upgrade to Redis in Phase 2.
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
        excluded_paths: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self.burst = burst_size
        self.excluded_paths = excluded_paths or {
            "/health",
            "/health/ready",
            "/metrics",
            "/docs",
            "/openapi.json",
        }

        # Sliding windows: client_id -> list of timestamps
        self.minute_windows: Dict[str, List[float]] = defaultdict(list)
        self.hour_windows: Dict[str, List[float]] = defaultdict(list)

        # Cleanup tracking
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        client_id = self._get_client_identifier(request)
        now = time.time()

        # Periodic cleanup
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_entries(now)
            self._last_cleanup = now

        # Check rate limits
        is_allowed, retry_after = self._check_rate_limit(client_id, now)

        if not is_allowed:
            logger.warning(
                "rate_limit.exceeded", client=client_id, path=request.url.path
            )
            return Response(
                content=json.dumps(
                    {"error": "Rate limit exceeded", "retry_after": retry_after}
                ),
                status_code=429,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": f"{self.rpm}/min, {self.rph}/hour",
                },
                media_type="application/json",
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        minute_remaining = max(0, self.rpm - len(self.minute_windows[client_id]))
        response.headers["X-RateLimit-Remaining"] = str(minute_remaining)
        response.headers["X-RateLimit-Limit"] = f"{self.rpm}/min"

        return response

    def _get_client_identifier(self, request: Request) -> str:
        """Generate unique client identifier."""
        # Use combination of IP and user ID if available
        ip = "unknown"
        if request.client:
            ip = request.client.host

        # Check for IP behind proxy
        if forwarded_for := request.headers.get("x-forwarded-for"):
            ip = forwarded_for.split(",")[0].strip()
        elif real_ip := request.headers.get("x-real-ip"):
            ip = real_ip

        # Include authenticated user if available
        user_id = getattr(request.state, "user_id", None)

        if user_id:
            return f"{ip}:{user_id}"
        return ip

    def _check_rate_limit(self, client_id: str, now: float) -> tuple[bool, int]:
        """Check if request is within rate limits."""
        # Clean old entries from windows
        minute_cutoff = now - 60
        hour_cutoff = now - 3600

        self.minute_windows[client_id] = [
            t for t in self.minute_windows[client_id] if t > minute_cutoff
        ]
        self.hour_windows[client_id] = [
            t for t in self.hour_windows[client_id] if t > hour_cutoff
        ]

        minute_count = len(self.minute_windows[client_id])
        hour_count = len(self.hour_windows[client_id])

        # Check minute limit (with burst)
        if minute_count >= self.rpm + self.burst:
            return False, 60

        # Check hour limit
        if hour_count >= self.rph:
            # Calculate when the oldest request will expire
            oldest = min(self.hour_windows[client_id])
            retry_after = int(oldest + 3600 - now)
            return False, retry_after

        # Add current request
        self.minute_windows[client_id].append(now)
        self.hour_windows[client_id].append(now)

        return True, 0

    def _cleanup_old_entries(self, now: float):
        """Remove old entries to prevent memory leak."""
        minute_cutoff = now - 60
        hour_cutoff = now - 3600

        # Clean minute windows
        empty_clients = []
        for client_id, timestamps in list(self.minute_windows.items()):
            self.minute_windows[client_id] = [
                t for t in timestamps if t > minute_cutoff
            ]
            if not self.minute_windows[client_id]:
                empty_clients.append(client_id)

        for client_id in empty_clients:
            del self.minute_windows[client_id]

        # Clean hour windows
        empty_clients = []
        for client_id, timestamps in list(self.hour_windows.items()):
            self.hour_windows[client_id] = [t for t in timestamps if t > hour_cutoff]
            if not self.hour_windows[client_id]:
                empty_clients.append(client_id)

        for client_id in empty_clients:
            del self.hour_windows[client_id]

        logger.info(
            "rate_limit.cleanup",
            minute_clients=len(self.minute_windows),
            hour_clients=len(self.hour_windows),
        )


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """
    Handles headers from reverse proxies and CDNs.
    Essential for accurate IP tracking and HTTPS detection.
    """

    def __init__(
        self,
        app: ASGIApp,
        trusted_proxies: Optional[Set[str]] = None,
        trust_x_forwarded: bool = True,
    ):
        super().__init__(app)
        self.trusted_proxies = trusted_proxies or {"127.0.0.1", "::1"}
        self.trust_x_forwarded = trust_x_forwarded

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Only trust headers from known proxies
        if request.client and request.client.host in self.trusted_proxies:
            # Fix client IP
            if forwarded_for := request.headers.get("x-forwarded-for"):
                ip = forwarded_for.split(",")[0].strip()
                request.scope["client"] = (ip, request.client.port)
            elif real_ip := request.headers.get("x-real-ip"):
                request.scope["client"] = (real_ip, request.client.port)

            # Fix scheme (HTTP/HTTPS)
            if forwarded_proto := request.headers.get("x-forwarded-proto"):
                request.scope["scheme"] = forwarded_proto

            # Fix host
            if forwarded_host := request.headers.get("x-forwarded-host"):
                request.scope["server"] = (forwarded_host, request.scope["server"][1])

        return await call_next(request)
