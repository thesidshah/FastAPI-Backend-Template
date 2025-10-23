"""
Monitoring and metrics for security middleware.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from typing import Dict

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ..integrations.alerting import AlertDispatcher

logger = structlog.get_logger(__name__)

# Try to import prometheus, but make it optional
try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest

    PROMETHEUS_AVAILABLE = True

    # Prometheus metrics
    request_count = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )

    request_duration = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration",
        ["method", "path"],
    )

    rate_limit_hits = Counter(
        "rate_limit_hits_total",
        "Rate limit hits",
        ["path", "client_type"],
    )

    auth_attempts = Counter(
        "auth_attempts_total",
        "Authentication attempts",
        ["result", "method"],
    )

    security_violations = Counter(
        "security_violations_total",
        "Security violations",
        ["type", "severity"],
    )

    active_connections = Gauge("active_connections", "Active connections")

except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning(
        "prometheus_client not installed, MetricsMiddleware will not collect metrics"
    )


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Collect metrics for monitoring.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.path_patterns = self._compile_path_patterns()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip metrics endpoint
        if request.url.path == "/metrics":
            if PROMETHEUS_AVAILABLE:
                return Response(content=generate_latest())
            else:
                return Response(
                    content="Prometheus metrics not available",
                    status_code=503,
                )

        # Track timing
        start_time = time.time()

        # Track active connections
        if PROMETHEUS_AVAILABLE:
            active_connections.inc()

        try:
            # Process request
            response = await call_next(request)

            if PROMETHEUS_AVAILABLE:
                # Record metrics
                duration = time.time() - start_time
                path_pattern = self._get_path_pattern(request.url.path)

                request_count.labels(
                    method=request.method, path=path_pattern, status=response.status_code
                ).inc()

                request_duration.labels(method=request.method, path=path_pattern).observe(
                    duration
                )

                # Track security events
                if response.status_code == 429:
                    rate_limit_hits.labels(
                        path=path_pattern,
                        client_type=(
                            "user"
                            if hasattr(request.state, "user_id")
                            else "anonymous"
                        ),
                    ).inc()

                if response.status_code == 401:
                    auth_attempts.labels(result="failed", method="jwt").inc()

                if response.status_code == 403:
                    security_violations.labels(
                        type="access_denied", severity="medium"
                    ).inc()

            return response

        finally:
            if PROMETHEUS_AVAILABLE:
                active_connections.dec()

    def _compile_path_patterns(self) -> Dict[str, str]:
        """Compile common path patterns for grouping."""
        return {
            r"^/api/users/\d+$": "/api/users/{id}",
            r"^/api/posts/\d+$": "/api/posts/{id}",
            r"^/api/items/[\w-]+$": "/api/items/{id}",
        }

    def _get_path_pattern(self, path: str) -> str:
        """Get path pattern for metrics grouping."""

        for pattern, replacement in self.path_patterns.items():
            if re.match(pattern, path):
                return replacement

        return path


class AlertingMiddleware(BaseHTTPMiddleware):
    """
    Send alerts for critical security events.
    """

    def __init__(self, app: ASGIApp, alert_threshold: Dict[str, int] | None = None):
        super().__init__(app)
        self.thresholds = alert_threshold or {
            "rate_limit": 100,  # Alert after 100 rate limit hits
            "auth_failures": 50,  # Alert after 50 auth failures
            "large_payloads": 10,  # Alert after 10 large payload attempts
        }

        self.counters: Dict[str, int] = defaultdict(int)
        self.last_alert: Dict[str, float] = {}
        self.alert_cooldown = 300  # 5 minutes
        self.alert_dispatcher = AlertDispatcher()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # Check for security events
        if response.status_code == 429:
            self._check_alert("rate_limit", request)

        if response.status_code == 401:
            self._check_alert("auth_failures", request)

        if response.status_code == 413:
            self._check_alert("large_payloads", request)

        return response

    def _check_alert(self, event_type: str, request: Request):
        """Check if we should send an alert."""

        self.counters[event_type] += 1

        if self.counters[event_type] >= self.thresholds.get(event_type, 100):
            now = time.time()
            last_alert = self.last_alert.get(event_type, 0)

            if now - last_alert > self.alert_cooldown:
                self._send_alert(event_type, request)
                self.last_alert[event_type] = now
                self.counters[event_type] = 0

    def _send_alert(self, event_type: str, request: Request):
        """Send alert to monitoring system."""

        alert_count = self.counters[event_type]
        logger.critical(
            "security.alert",
            event_type=event_type,
            count=alert_count,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        self.alert_dispatcher.dispatch(
            {
                "event_type": event_type,
                "count": alert_count,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
                "method": request.method,
            }
        )
