from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Awaitable
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp

from .config import AppSettings, get_security_settings, SecuritySettings


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a stable request id to each incoming request for traceability."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,  # better typing
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        logger = structlog.get_logger("middleware.request_id")
        logger.debug("request_id.assigned", path=request.url.path)

        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()

        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit structured logs for HTTP requests."""

    def __init__(self, app: ASGIApp, include_body: bool = False) -> None:  # <-- ASGIApp
        super().__init__(app)
        self.include_body = include_body

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        logger = structlog.get_logger("http.request")
        start_time = time.perf_counter()
        body_snippet: str | None = None

        if self.include_body:
            body = await request.body()
            body_snippet = body.decode("utf-8", errors="replace")[:256]
            # Allow downstream to read the body again
            request._body = body  # type: ignore[attr-defined]

        logger.info(
            "http.request.start",
            method=request.method,
            path=request.url.path,
            query=str(request.url.query or ""),
        )

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "http.request.error",
                method=request.method,
                path=request.url.path,
            )
            raise

        process_time_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "http.request.complete",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(process_time_ms, 3),
            body_snippet=body_snippet,
        )

        response.headers["X-Process-Time"] = f"{process_time_ms:.3f}"
        return response


def register_middlewares(app: FastAPI, settings: AppSettings) -> None:
    """
    Register global application middleware stack.

    Order matters! Middleware is applied in reverse order:
    - First added = outermost (processes requests last, responses first)
    - Last added = innermost (processes requests first, responses last)
    """
    logger = structlog.get_logger("middleware.registration")
    security_settings : SecuritySettings = get_security_settings()

    # Import security middleware
    from ..middleware.security import (
        ContentValidationMiddleware,
        ProxyHeadersMiddleware,
        SecurityHeadersMiddleware,
        SimpleRateLimitMiddleware,
    )

    # Phase 1: Core security middleware (always available)

    # 1. Security Headers (outermost - sets response headers)
    app.add_middleware(
        SecurityHeadersMiddleware,
        is_production=settings.environment.value == "production",
        enable_hsts=security_settings.enable_hsts,
        enable_csp=security_settings.enable_csp,
        csp_policy=security_settings.csp_policy,
    )
    logger.info("middleware.registered", name="SecurityHeadersMiddleware")

    # 2. Rate Limiting (block excessive requests early)
    if security_settings.rate_limit_enabled:
        # Try Redis rate limiter first (Phase 2)
        if security_settings.redis_enabled and security_settings.redis_url:
            try:
                from ..middleware.rate_limit import REDIS_AVAILABLE, RedisRateLimitMiddleware

                if REDIS_AVAILABLE:
                    import redis.asyncio as redis
                    redis_client = redis.from_url(
                        security_settings.redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                    )
                    app.add_middleware(
                        RedisRateLimitMiddleware,
                        redis_client=redis_client,
                        default_limit=security_settings.rate_limit_per_minute,
                        window_seconds=60,
                    )
                    logger.info("middleware.registered", name="RedisRateLimitMiddleware")
                else:
                    logger.warning("redis not available, using SimpleRateLimitMiddleware")
                    app.add_middleware(
                        SimpleRateLimitMiddleware,
                        requests_per_minute=security_settings.rate_limit_per_minute,
                        requests_per_hour=security_settings.rate_limit_per_hour,
                        burst_size=security_settings.rate_limit_burst,
                    )
                    logger.info("middleware.registered", name="SimpleRateLimitMiddleware")
            except ImportError:
                logger.warning("redis not installed, using SimpleRateLimitMiddleware")
                app.add_middleware(
                    SimpleRateLimitMiddleware,
                    requests_per_minute=security_settings.rate_limit_per_minute,
                    requests_per_hour=security_settings.rate_limit_per_hour,
                    burst_size=security_settings.rate_limit_burst,
                )
                logger.info("middleware.registered", name="SimpleRateLimitMiddleware")
        else:
            # Use in-memory rate limiter (Phase 1)
            app.add_middleware(
                SimpleRateLimitMiddleware,
                requests_per_minute=security_settings.rate_limit_per_minute,
                requests_per_hour=security_settings.rate_limit_per_hour,
                burst_size=security_settings.rate_limit_burst,
            )
            logger.info("middleware.registered", name="SimpleRateLimitMiddleware")

    # 3. Content Validation
    app.add_middleware(
        ContentValidationMiddleware,
        size_limits={
            "/api/upload": security_settings.max_upload_size,
            "/api/": security_settings.max_request_size,
            "/": 64 * 1024,
        },
        block_null_bytes=security_settings.block_null_bytes,
    )
    logger.info("middleware.registered", name="ContentValidationMiddleware")

    # 4. Proxy Headers (if behind load balancer/CDN)
    if security_settings.trust_proxy_headers:
        app.add_middleware(
            ProxyHeadersMiddleware,
            trusted_proxies=security_settings.trusted_proxies,
        )
        logger.info("middleware.registered", name="ProxyHeadersMiddleware")

    # Phase 2: Authentication (optional)
    if security_settings.jwt_secret:
        try:
            from ..middleware.auth import JWT_AVAILABLE, JWTAuthenticationMiddleware

            if JWT_AVAILABLE:
                app.add_middleware(
                    JWTAuthenticationMiddleware,
                    secret_key=security_settings.jwt_secret,
                    algorithm=security_settings.jwt_algorithm,
                )
                logger.info("middleware.registered", name="JWTAuthenticationMiddleware")
            else:
                logger.warning("PyJWT not installed, JWT authentication disabled")
        except ImportError:
            logger.warning("auth middleware not available")

    # Phase 3: Advanced features (optional)

    # Geo-blocking
    if security_settings.enable_geo_blocking and security_settings.geoip_database_path:
        try:
            from ..middleware.advanced import GeoBlockingMiddleware

            app.add_middleware(
                GeoBlockingMiddleware,
                allowed_countries=security_settings.allowed_countries,
                blocked_countries=security_settings.blocked_countries,
                geoip_database_path=security_settings.geoip_database_path,
            )
            logger.info("middleware.registered", name="GeoBlockingMiddleware")
        except ImportError:
            logger.warning("geoip2 not installed, geo-blocking disabled")

    # Circuit Breaker
    if security_settings.enable_circuit_breaker:
        try:
            from ..middleware.advanced import CircuitBreakerMiddleware

            app.add_middleware(
                CircuitBreakerMiddleware,
                failure_threshold=security_settings.circuit_breaker_threshold,
                recovery_timeout=security_settings.circuit_breaker_timeout,
            )
            logger.info("middleware.registered", name="CircuitBreakerMiddleware")
        except ImportError:
            logger.warning("circuit breaker middleware not available")

    # DDoS Protection
    if security_settings.enable_ddos_protection:
        try:
            from ..middleware.advanced import DDoSProtectionMiddleware

            app.add_middleware(
                DDoSProtectionMiddleware,
                syn_flood_threshold=security_settings.ddos_syn_threshold,
                request_rate_threshold=security_settings.ddos_rate_threshold,
            )
            logger.info("middleware.registered", name="DDoSProtectionMiddleware")
        except ImportError:
            logger.warning("ddos protection middleware not available")

    # Monitoring
    if security_settings.enable_prometheus:
        try:
            from ..middleware.monitoring import PROMETHEUS_AVAILABLE, MetricsMiddleware

            if PROMETHEUS_AVAILABLE:
                app.add_middleware(MetricsMiddleware)
                logger.info("middleware.registered", name="MetricsMiddleware")
            else:
                logger.warning("prometheus_client not installed, metrics disabled")
        except ImportError:
            logger.warning("monitoring middleware not available")

    if security_settings.enable_alerting:
        try:
            from ..middleware.monitoring import AlertingMiddleware

            app.add_middleware(
                AlertingMiddleware,
                alert_threshold={
                    "rate_limit": security_settings.alert_rate_limit_threshold,
                    "auth_failures": security_settings.alert_auth_failure_threshold,
                },
            )
            logger.info("middleware.registered", name="AlertingMiddleware")
        except ImportError:
            logger.warning("alerting middleware not available")

    # 5. Trusted Host validation
    if settings.allowed_hosts and settings.allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
        logger.info("middleware.registered", name="TrustedHostMiddleware")

    # 6. CORS (if needed)
    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=list(settings.cors_allow_methods),
            allow_headers=list(settings.cors_allow_headers),
        )
        logger.info("middleware.registered", name="CORSMiddleware")

    # 7. Request ID (core middleware)
    app.add_middleware(RequestIDMiddleware)
    logger.info("middleware.registered", name="RequestIDMiddleware")

    # 8. Request Logging (innermost - logs everything)
    app.add_middleware(RequestLoggingMiddleware, include_body=settings.debug)
    logger.info("middleware.registered", name="RequestLoggingMiddleware")

    logger.info(
        "middleware.registration.complete",
        total_middlewares=8,
        security_enabled=True,
        phase1_enabled=True,
        phase2_redis=security_settings.redis_enabled,
        phase2_jwt=bool(security_settings.jwt_secret),
        phase3_advanced=any([
            security_settings.enable_geo_blocking,
            security_settings.enable_circuit_breaker,
            security_settings.enable_ddos_protection,
        ]),
        monitoring=security_settings.enable_prometheus,
    )
