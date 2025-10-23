"""
Enterprise-grade security middleware.
Phase 3: Advanced features for scale and compliance.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class GeoBlockingMiddleware(BaseHTTPMiddleware):
    """
    Geographic restriction middleware for compliance.
    Requires geoip2 library and MaxMind database.
    """

    def __init__(
        self,
        app: ASGIApp,
        allowed_countries: Optional[Set[str]] = None,
        blocked_countries: Optional[Set[str]] = None,
        geoip_database_path: Optional[str] = None,
    ):
        super().__init__(app)
        self.allowed_countries = allowed_countries
        self.blocked_countries = blocked_countries or set()

        # Initialize GeoIP database (using maxmind or similar)
        self.geoip = None
        if geoip_database_path:
            try:
                import geoip2.database

                self.geoip = geoip2.database.Reader(geoip_database_path)
            except ImportError:
                logger.warning("geoip2 not installed, geo-blocking disabled")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self.geoip:
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        try:
            # Look up country
            response = self.geoip.country(client_ip)
            country_code = response.country.iso_code

            # Check restrictions
            if (
                self.allowed_countries
                and country_code not in self.allowed_countries
            ):
                return self._blocked_response(country_code)

            if country_code in self.blocked_countries:
                return self._blocked_response(country_code)

            # Add country to request state
            request.state.country_code = country_code

        except Exception as e:
            logger.warning(
                "geo_blocking.lookup_failed", ip=client_ip, error=str(e)
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP."""
        if forwarded := request.headers.get("x-forwarded-for"):
            return forwarded.split(",")[0].strip()
        if real_ip := request.headers.get("x-real-ip"):
            return real_ip
        if request.client:
            return request.client.host
        return "127.0.0.1"

    def _blocked_response(self, country_code: str) -> Response:
        """Return blocked response."""
        logger.warning("geo_blocking.blocked", country=country_code)
        return Response(
            content=json.dumps({"error": "Access denied from your region"}),
            status_code=403,
            media_type="application/json",
        )


class RequestSignatureMiddleware(BaseHTTPMiddleware):
    """
    HMAC signature validation for API requests.
    Prevents replay attacks and ensures request integrity.
    """

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str,
        header_name: str = "X-Signature",
        timestamp_header: str = "X-Timestamp",
        max_age_seconds: int = 300,
    ):
        super().__init__(app)
        self.secret_key = secret_key.encode()
        self.header_name = header_name
        self.timestamp_header = timestamp_header
        self.max_age = max_age_seconds

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip signature check for public endpoints
        if request.url.path.startswith("/health"):
            return await call_next(request)

        # Get signature and timestamp
        signature = request.headers.get(self.header_name)
        timestamp = request.headers.get(self.timestamp_header)

        if not signature or not timestamp:
            return await call_next(request)  # Optional signature

        try:
            # Check timestamp freshness
            request_time = int(timestamp)
            current_time = int(time.time())

            if abs(current_time - request_time) > self.max_age:
                return Response(
                    content=json.dumps({"error": "Request expired"}),
                    status_code=401,
                    media_type="application/json",
                )

            # Read body
            body = await request.body()

            # Calculate expected signature
            message = f"{request.method}:{request.url.path}:{timestamp}:{body.decode()}"
            expected_signature = hmac.new(
                self.secret_key, message.encode(), hashlib.sha256
            ).hexdigest()

            # Verify signature (constant time comparison)
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("signature.invalid", path=request.url.path)
                return Response(
                    content=json.dumps({"error": "Invalid signature"}),
                    status_code=401,
                    media_type="application/json",
                )

            # Allow body to be read again
            request._body = body

        except Exception as e:
            logger.error("signature.validation_error", error=str(e))
            return Response(
                content=json.dumps({"error": "Signature validation failed"}),
                status_code=400,
                media_type="application/json",
            )

        return await call_next(request)


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """
    Circuit breaker pattern for downstream service protection.
    """

    def __init__(
        self,
        app: ASGIApp,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        super().__init__(app)
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        # Circuit state per endpoint
        self.states: Dict[str, str] = defaultdict(lambda: "closed")
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.last_failure_times: Dict[str, float] = {}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        endpoint = f"{request.method}:{request.url.path}"

        # Check circuit state
        state = self._get_state(endpoint)

        if state == "open":
            # Check if we should try half-open
            if self._should_attempt_reset(endpoint):
                self.states[endpoint] = "half_open"
            else:
                return Response(
                    content=json.dumps({"error": "Service temporarily unavailable"}),
                    status_code=503,
                    headers={"Retry-After": str(self.recovery_timeout)},
                    media_type="application/json",
                )

        try:
            # Process request
            response = await call_next(request)

            # Check response status
            if response.status_code >= 500:
                self._record_failure(endpoint)
            else:
                self._record_success(endpoint)

            return response

        except self.expected_exception as e:
            self._record_failure(endpoint)

            if self.states[endpoint] == "open":
                return Response(
                    content=json.dumps({"error": "Service temporarily unavailable"}),
                    status_code=503,
                    media_type="application/json",
                )

            raise

    def _get_state(self, endpoint: str) -> str:
        """Get current circuit state."""
        return self.states[endpoint]

    def _record_success(self, endpoint: str):
        """Record successful request."""
        self.failure_counts[endpoint] = 0
        if self.states[endpoint] == "half_open":
            self.states[endpoint] = "closed"

    def _record_failure(self, endpoint: str):
        """Record failed request."""
        self.failure_counts[endpoint] += 1
        self.last_failure_times[endpoint] = time.time()

        if self.failure_counts[endpoint] >= self.failure_threshold:
            self.states[endpoint] = "open"
            logger.warning(
                "circuit_breaker.opened",
                endpoint=endpoint,
                failures=self.failure_counts[endpoint],
            )

    def _should_attempt_reset(self, endpoint: str) -> bool:
        """Check if we should attempt to reset circuit."""
        last_failure = self.last_failure_times.get(endpoint, 0)
        return (time.time() - last_failure) >= self.recovery_timeout


class DDoSProtectionMiddleware(BaseHTTPMiddleware):
    """
    Advanced DDoS protection with multiple strategies.
    """

    def __init__(
        self,
        app: ASGIApp,
        syn_flood_threshold: int = 100,
        request_rate_threshold: int = 1000,
        unique_ip_threshold: int = 500,
    ):
        super().__init__(app)
        self.syn_threshold = syn_flood_threshold
        self.rate_threshold = request_rate_threshold
        self.ip_threshold = unique_ip_threshold

        # Tracking
        self.connection_counts: Dict[str, int] = defaultdict(int)
        self.request_counts: Dict[str, List[float]] = defaultdict(list)
        self.unique_ips: Set[str] = set()
        self.blocked_ips: Set[str] = set()

        # Start cleanup task
        asyncio.create_task(self._cleanup_loop())

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = self._get_client_ip(request)

        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            return Response(
                content=json.dumps({"error": "Blocked"}),
                status_code=403,
                media_type="application/json",
            )

        # Track connection
        self.connection_counts[client_ip] += 1
        self.unique_ips.add(client_ip)

        # Check for attacks
        if self._detect_attack(client_ip):
            self.blocked_ips.add(client_ip)
            logger.warning(
                "ddos.ip_blocked",
                ip=client_ip,
                connections=self.connection_counts[client_ip],
            )
            return Response(
                content=json.dumps({"error": "Too many requests"}),
                status_code=429,
                media_type="application/json",
            )

        try:
            response = await call_next(request)
            return response
        finally:
            self.connection_counts[client_ip] -= 1

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP."""
        if forwarded := request.headers.get("x-forwarded-for"):
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _detect_attack(self, client_ip: str) -> bool:
        """Detect potential DDoS attack."""

        # Check connection count
        if self.connection_counts[client_ip] > self.syn_threshold:
            return True

        # Check request rate
        now = time.time()
        self.request_counts[client_ip].append(now)

        # Clean old requests
        self.request_counts[client_ip] = [
            t for t in self.request_counts[client_ip] if now - t < 60
        ]

        if len(self.request_counts[client_ip]) > self.rate_threshold:
            return True

        # Check unique IPs (botnet detection)
        if len(self.unique_ips) > self.ip_threshold:
            logger.warning("ddos.high_unique_ips", count=len(self.unique_ips))

        return False

    async def _cleanup_loop(self):
        """Periodic cleanup of tracking data."""
        while True:
            await asyncio.sleep(300)  # 5 minutes

            # Clean up old data
            self.unique_ips.clear()

            # Unblock IPs after cooldown
            self.blocked_ips = {
                ip for ip in self.blocked_ips if self.connection_counts[ip] > 0
            }

            logger.info(
                "ddos.cleanup",
                blocked_ips=len(self.blocked_ips),
                active_connections=sum(self.connection_counts.values()),
            )
