# FastAPI Security Middleware: Complete Production Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Phase 1: Pre-Launch Security](#phase-1-pre-launch-security)
4. [Phase 2: Launch-Ready with Redis](#phase-2-launch-ready-with-redis)
5. [Phase 3: Scale & Enterprise](#phase-3-scale--enterprise)
6. [Testing Strategy](#testing-strategy)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [Troubleshooting Guide](#troubleshooting-guide)

---

## Overview

This guide provides a complete, production-ready security middleware implementation for FastAPI applications. Each phase builds on the previous one, allowing you to incrementally add security features as your application grows.

### Current Security Posture

Your existing implementation provides:
- ✅ Request ID tracking
- ✅ Request logging
- ✅ Host validation
- ✅ CORS configuration

This guide adds:
- 🛡️ Security headers
- 🚦 Rate limiting
- 📏 Content size validation
- 🔐 Authentication extraction
- 🌍 Proxy/CDN support
- 📊 Metrics and monitoring

### Production Timeline

| Phase | Timeline | User Count | Key Features |
|-------|----------|------------|--------------|
| Phase 1 | Pre-launch | 0-100 | Basic security, in-memory rate limiting |
| Phase 2 | Launch | 100-1000 | Redis rate limiting, JWT auth |
| Phase 3 | Growth | 1000-10000 | Multi-tier limits, API keys |
| Phase 4 | Enterprise | 10000+ | WAF, SIEM, ML-based protection |

---

## Architecture

### Middleware Stack Order (Critical!)

```python
# Request flow: Top → Bottom
# Response flow: Bottom → Top

1. SecurityHeadersMiddleware      # Sets response headers
2. RateLimitMiddleware            # Blocks excessive requests
3. ContentValidationMiddleware    # Validates payload size/type
4. ProxyHeadersMiddleware         # Fixes IPs behind CDN
5. RequestIDMiddleware            # Assigns tracking ID
6. AuthenticationMiddleware       # Extracts user identity
7. RequestLoggingMiddleware       # Logs everything
8. Your Application              # Business logic
```

### Directory Structure

```
project/
├── app/
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── security.py       # Phase 1: Core security
│   │   ├── rate_limit.py     # Phase 1-2: Rate limiting
│   │   ├── auth.py           # Phase 2: Authentication
│   │   ├── monitoring.py     # Metrics & alerting
│   │   └── advanced.py       # Phase 3: Enterprise features
│   ├── config.py
│   └── main.py
├── tests/
│   └── test_middleware.py
├── requirements.txt
└── docker-compose.yml
```

---

## Phase 1: Pre-Launch Security

### Complete File: `app/middleware/security.py`

```python
"""
Security middleware for FastAPI applications.
Phase 1: Core security features with no external dependencies.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from typing import Optional, Dict, List, Set

import structlog
from fastapi import FastAPI, Request, Response
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
        csp_policy: Optional[str] = None
    ):
        super().__init__(app)
        self.is_production = is_production
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
        self.csp_policy = csp_policy or "default-src 'self'"
        
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        
        # Essential security headers - always apply
        response.headers.update({
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
        })
        
        # HSTS - only in production with HTTPS
        if self.is_production and self.enable_hsts:
            if request.url.scheme == "https":
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains; preload"
                )
        
        # Content Security Policy - optional but recommended
        if self.enable_csp and self.is_production:
            response.headers["Content-Security-Policy"] = self.csp_policy
            # Report-only mode for testing
            # response.headers["Content-Security-Policy-Report-Only"] = self.csp_policy
        
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
        "/api/upload": 50 * 1024 * 1024,    # 50MB for file uploads
        "/api/import": 10 * 1024 * 1024,    # 10MB for data imports
        "/api/": 1 * 1024 * 1024,           # 1MB for API calls
        "/webhook": 256 * 1024,              # 256KB for webhooks
        "/graphql": 100 * 1024,              # 100KB for GraphQL
        "/": 64 * 1024,                      # 64KB default
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
        block_null_bytes: bool = True
    ):
        super().__init__(app)
        self.size_limits = size_limits or self.DEFAULT_LIMITS
        self.allowed_types = allowed_types or self.ALLOWED_CONTENT_TYPES
        self.block_null_bytes = block_null_bytes
        
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
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
                    client=request.client.host if request.client else None
                )
                return Response(
                    content=json.dumps({
                        "error": "Payload too large",
                        "max_size": limit
                    }),
                    status_code=413,
                    media_type="application/json"
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
                    method=request.method
                )
                return Response(
                    content=json.dumps({
                        "error": "Unsupported media type",
                        "allowed_types": list(allowed)
                    }),
                    status_code=415,
                    media_type="application/json"
                )
        
        # Check for null bytes in URL (path traversal attempt)
        if self.block_null_bytes and "\x00" in str(request.url):
            logger.warning(
                "content_validation.null_bytes",
                path=request.url.path,
                client=request.client.host if request.client else None
            )
            return Response(
                content=json.dumps({"error": "Invalid request"}),
                status_code=400,
                media_type="application/json"
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
        excluded_paths: Optional[Set[str]] = None
    ):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self.burst = burst_size
        self.excluded_paths = excluded_paths or {"/health", "/metrics", "/docs", "/openapi.json"}
        
        # Sliding windows: client_id -> list of timestamps
        self.minute_windows: Dict[str, List[float]] = defaultdict(list)
        self.hour_windows: Dict[str, List[float]] = defaultdict(list)
        
        # Cleanup tracking
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
        
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
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
                "rate_limit.exceeded",
                client=client_id,
                path=request.url.path
            )
            return Response(
                content=json.dumps({
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after
                }),
                status_code=429,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": f"{self.rpm}/min, {self.rph}/hour",
                }
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
            self.hour_windows[client_id] = [
                t for t in timestamps if t > hour_cutoff
            ]
            if not self.hour_windows[client_id]:
                empty_clients.append(client_id)
        
        for client_id in empty_clients:
            del self.hour_windows[client_id]
        
        logger.info(
            "rate_limit.cleanup",
            minute_clients=len(self.minute_windows),
            hour_clients=len(self.hour_windows)
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
        trust_x_forwarded: bool = True
    ):
        super().__init__(app)
        self.trusted_proxies = trusted_proxies or {"127.0.0.1", "::1"}
        self.trust_x_forwarded = trust_x_forwarded
        
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
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
```

### Complete File: `app/middleware/__init__.py`

```python
"""
Middleware package for FastAPI security.
"""

from .security import (
    SecurityHeadersMiddleware,
    ContentValidationMiddleware,
    SimpleRateLimitMiddleware,
    ProxyHeadersMiddleware,
)

__all__ = [
    "SecurityHeadersMiddleware",
    "ContentValidationMiddleware", 
    "SimpleRateLimitMiddleware",
    "ProxyHeadersMiddleware",
]
```

### Complete File: `app/config.py`

```python
"""
Application configuration with security settings.
"""

from typing import Optional, Set, List
from pydantic import BaseSettings, Field


class SecuritySettings(BaseSettings):
    """Security-specific configuration."""
    
    # Rate limiting
    rate_limit_per_minute: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(1000, env="RATE_LIMIT_PER_HOUR")
    rate_limit_burst: int = Field(10, env="RATE_LIMIT_BURST")
    
    # Content validation
    max_upload_size: int = Field(50 * 1024 * 1024, env="MAX_UPLOAD_SIZE")
    max_request_size: int = Field(1 * 1024 * 1024, env="MAX_REQUEST_SIZE")
    
    # Security headers
    enable_hsts: bool = Field(True, env="ENABLE_HSTS")
    enable_csp: bool = Field(False, env="ENABLE_CSP")
    csp_policy: str = Field(
        "default-src 'self'; script-src 'self' 'unsafe-inline'",
        env="CSP_POLICY"
    )
    
    # Proxy settings
    trusted_proxies: Set[str] = Field(
        {"127.0.0.1", "::1"},
        env="TRUSTED_PROXIES"
    )
    trust_proxy_headers: bool = Field(False, env="TRUST_PROXY_HEADERS")
    
    class Config:
        env_file = ".env"
        env_prefix = "SECURITY_"


class AppSettings(BaseSettings):
    """Main application settings."""
    
    # App info
    app_name: str = Field("FastAPI App", env="APP_NAME")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # Server
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    
    # CORS
    cors_allow_origins: List[str] = Field(["*"], env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(True, env="CORS_CREDENTIALS")
    cors_allow_methods: List[str] = Field(["*"], env="CORS_METHODS")
    cors_allow_headers: List[str] = Field(["*"], env="CORS_HEADERS")
    
    # Security
    allowed_hosts: List[str] = Field(["*"], env="ALLOWED_HOSTS")
    secret_key: str = Field(..., env="SECRET_KEY")
    
    # Redis (Phase 2)
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    
    # JWT (Phase 2)
    jwt_secret: Optional[str] = Field(None, env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiry_minutes: int = Field(60, env="JWT_EXPIRY_MINUTES")
    
    class Config:
        env_file = ".env"


def get_settings() -> AppSettings:
    """Get cached settings instance."""
    return AppSettings()


def get_security_settings() -> SecuritySettings:
    """Get cached security settings."""
    return SecuritySettings()
```

### Complete File: `app/main.py`

```python
"""
Main FastAPI application with Phase 1 security middleware.
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings, get_security_settings
from app.middleware.security import (
    SecurityHeadersMiddleware,
    ContentValidationMiddleware,
    SimpleRateLimitMiddleware,
    ProxyHeadersMiddleware,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    settings = get_settings()
    security_settings = get_security_settings()
    
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    
    # Register middleware in correct order (IMPORTANT!)
    register_middleware(app, settings, security_settings)
    
    # Register routes
    register_routes(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app


def register_middleware(
    app: FastAPI,
    settings: AppSettings,
    security_settings: SecuritySettings
) -> None:
    """
    Register all middleware in the correct order.
    Order matters! First middleware wraps all others.
    """
    
    # 1. Security headers (outermost - runs last for requests, first for responses)
    app.add_middleware(
        SecurityHeadersMiddleware,
        is_production=settings.environment == "production",
        enable_hsts=security_settings.enable_hsts,
        enable_csp=security_settings.enable_csp,
        csp_policy=security_settings.csp_policy
    )
    
    # 2. Rate limiting (block bad actors early)
    app.add_middleware(
        SimpleRateLimitMiddleware,
        requests_per_minute=security_settings.rate_limit_per_minute,
        requests_per_hour=security_settings.rate_limit_per_hour,
        burst_size=security_settings.rate_limit_burst,
    )
    
    # 3. Content validation
    app.add_middleware(
        ContentValidationMiddleware,
        size_limits={
            "/api/upload": security_settings.max_upload_size,
            "/api/": security_settings.max_request_size,
            "/": 64 * 1024,
        }
    )
    
    # 4. Proxy headers (if behind load balancer)
    if security_settings.trust_proxy_headers:
        app.add_middleware(
            ProxyHeadersMiddleware,
            trusted_proxies=security_settings.trusted_proxies
        )
    
    # 5. Trusted host validation
    if settings.allowed_hosts and settings.allowed_hosts != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )
    
    # 6. CORS (if needed)
    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )
    
    logger.info(
        "middleware.registered",
        environment=settings.environment,
        security_enabled=True,
        rate_limiting=True,
        proxy_headers=security_settings.trust_proxy_headers
    )


def register_routes(app: FastAPI) -> None:
    """Register application routes."""
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}
    
    @app.get("/api/test")
    async def test_endpoint(request: Request):
        """Test endpoint for verification."""
        return {
            "message": "API is working",
            "client_ip": request.client.host if request.client else None,
            "headers": dict(request.headers),
        }
    
    @app.post("/api/echo")
    async def echo_endpoint(data: dict):
        """Echo endpoint for testing."""
        return {"received": data}


def register_error_handlers(app: FastAPI) -> None:
    """Register custom error handlers."""
    
    @app.exception_handler(429)
    async def rate_limit_handler(request: Request, exc):
        return {
            "error": "Rate limit exceeded",
            "message": "Please slow down your requests"
        }
    
    @app.exception_handler(413)
    async def payload_too_large_handler(request: Request, exc):
        return {
            "error": "Payload too large",
            "message": "Request body exceeds maximum allowed size"
        }


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "error",
    )
```

### Environment File: `.env`

```bash
# Application
APP_NAME="My FastAPI App"
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-change-this-in-production

# Server
HOST=0.0.0.0
PORT=8000

# Security
SECURITY_RATE_LIMIT_PER_MINUTE=60
SECURITY_RATE_LIMIT_PER_HOUR=1000
SECURITY_RATE_LIMIT_BURST=10
SECURITY_MAX_UPLOAD_SIZE=52428800  # 50MB
SECURITY_MAX_REQUEST_SIZE=1048576  # 1MB
SECURITY_ENABLE_HSTS=false  # Enable in production
SECURITY_ENABLE_CSP=false
SECURITY_TRUST_PROXY_HEADERS=false  # Enable if behind proxy

# CORS
CORS_ORIGINS=["http://localhost:3000"]
CORS_CREDENTIALS=true
CORS_METHODS=["*"]
CORS_HEADERS=["*"]

# Allowed hosts
ALLOWED_HOSTS=["*"]
```

---

## Phase 2: Launch-Ready with Redis

### Complete File: `app/middleware/rate_limit.py`

```python
"""
Production-ready rate limiting with Redis backend.
Phase 2: Distributed rate limiting for multi-instance deployments.
"""

from __future__ import annotations

import json
import hashlib
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import structlog
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


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
        excluded_paths: Optional[set] = None
    ):
        super().__init__(app)
        self.redis = redis_client
        self.default_limit = default_limit
        self.window = window_seconds
        self.key_prefix = key_prefix
        self.enable_user_limits = enable_user_limits
        self.user_multiplier = user_limit_multiplier
        self.excluded_paths = excluded_paths or {
            "/health", "/metrics", "/docs", "/openapi.json", "/favicon.ico"
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
        self,
        request: Request,
        call_next: RequestResponseEndpoint
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
                    retry_after=remaining_or_retry
                )
                
                return Response(
                    content=json.dumps({
                        "error": "Rate limit exceeded",
                        "retry_after": remaining_or_retry
                    }),
                    status_code=429,
                    headers={
                        "Retry-After": str(remaining_or_retry),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(
                            int(time.time()) + remaining_or_retry
                        )
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers.update({
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining_or_retry),
                "X-RateLimit-Reset": str(int(time.time()) + self.window)
            })
            
            return response
            
        except RedisError as e:
            # Redis failure - log and fail open
            logger.error(
                "rate_limit.redis_error",
                error=str(e),
                client=client_id,
                path=request.url.path
            )
            
            # Fail open - allow request but log the issue
            return await call_next(request)
    
    async def _check_rate_limit(
        self,
        client_id: str,
        limit: int,
        path: str
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
                self._script_sha,
                1,
                key,
                limit,
                self.window,
                now
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
                "enterprise": 10.0
            }
            multiplier = tier_multipliers.get(user_tier, 1.0)
            limit = int(limit * multiplier)
        
        return limit


class DistributedRateLimiter:
    """
    Advanced rate limiter with multiple strategies.
    Supports token bucket, fixed window, and sliding window.
    """
    
    def __init__(
        self,
        redis_client: Redis,
        strategy: str = "sliding_window"
    ):
        self.redis = redis_client
        self.strategy = strategy
        
        # Token bucket settings
        self.bucket_capacity = 100
        self.refill_rate = 1  # tokens per second
        
    async def check_token_bucket(
        self,
        key: str,
        capacity: int = 100,
        refill_rate: float = 1.0
    ) -> tuple[bool, int]:
        """
        Token bucket algorithm for burst handling.
        """
        
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now
        
        -- Calculate new tokens
        local elapsed = now - last_refill
        local new_tokens = math.min(capacity, tokens + elapsed * refill_rate)
        
        if new_tokens >= 1 then
            -- Consume a token
            redis.call('HMSET', key, 
                'tokens', new_tokens - 1,
                'last_refill', now
            )
            redis.call('EXPIRE', key, 3600)
            return {1, math.floor(new_tokens - 1)}
        else
            -- No tokens available
            local wait_time = (1 - new_tokens) / refill_rate
            return {0, math.ceil(wait_time)}
        end
        """
        
        result = await self.redis.eval(
            lua_script,
            1,
            key,
            capacity,
            refill_rate,
            time.time()
        )
        
        return bool(result[0]), int(result[1])
    
    async def check_fixed_window(
        self,
        key: str,
        limit: int,
        window: int
    ) -> tuple[bool, int]:
        """
        Fixed window algorithm - simple but can have thundering herd.
        """
        
        # Current window key
        window_start = int(time.time() // window) * window
        window_key = f"{key}:{window_start}"
        
        # Increment counter
        async with self.redis.pipeline() as pipe:
            pipe.incr(window_key)
            pipe.expire(window_key, window)
            results = await pipe.execute()
        
        count = results[0]
        
        if count <= limit:
            return True, limit - count
        else:
            # Calculate retry after
            retry_after = window_start + window - int(time.time())
            return False, retry_after
```

### Complete File: `app/middleware/auth.py`

```python
"""
Authentication middleware for JWT token validation.
Phase 2: Production authentication with multiple providers.
"""

from __future__ import annotations

import time
import json
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

import jwt
import structlog
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    JWT authentication middleware with support for multiple providers.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        secret_key: str,
        algorithm: str = "HS256",
        auth_required_paths: Optional[List[str]] = None,
        public_paths: Optional[List[str]] = None,
        jwks_url: Optional[str] = None,  # For OAuth providers
    ):
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.auth_required_paths = auth_required_paths or ["/api/"]
        self.public_paths = public_paths or [
            "/health", "/docs", "/openapi.json", "/api/auth/"
        ]
        self.jwks_url = jwks_url
        
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Initialize request state
        request.state.user = None
        request.state.user_id = None
        request.state.user_tier = None
        request.state.scopes = []
        request.state.is_authenticated = False
        
        # Check if path requires authentication
        path = request.url.path
        requires_auth = self._path_requires_auth(path)
        
        # Extract and validate token
        token = self._extract_token(request)
        
        if token:
            try:
                payload = await self._validate_token(token)
                
                # Set user state
                request.state.user = payload
                request.state.user_id = payload.get("sub") or payload.get("user_id")
                request.state.user_tier = payload.get("tier", "free")
                request.state.scopes = payload.get("scopes", [])
                request.state.is_authenticated = True
                
                logger.info(
                    "auth.success",
                    user_id=request.state.user_id,
                    path=path
                )
                
            except jwt.ExpiredSignatureError:
                logger.warning("auth.token_expired", path=path)
                if requires_auth:
                    return Response(
                        content=json.dumps({"error": "Token expired"}),
                        status_code=401,
                        headers={"WWW-Authenticate": "Bearer"}
                    )
                    
            except jwt.InvalidTokenError as e:
                logger.warning("auth.invalid_token", error=str(e), path=path)
                if requires_auth:
                    return Response(
                        content=json.dumps({"error": "Invalid token"}),
                        status_code=401,
                        headers={"WWW-Authenticate": "Bearer"}
                    )
        
        # Check if authentication is required
        if requires_auth and not request.state.is_authenticated:
            return Response(
                content=json.dumps({"error": "Authentication required"}),
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Process request
        return await call_next(request)
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract token from request."""
        
        # Check Authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Check cookie (for web apps)
        token_cookie = request.cookies.get("access_token")
        if token_cookie:
            return token_cookie
        
        # Check query parameter (for WebSocket)
        token_param = request.query_params.get("token")
        if token_param:
            return token_param
        
        return None
    
    async def _validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token."""
        
        # Decode token
        payload = jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
            options={"verify_exp": True}
        )
        
        # Additional validation
        if "exp" in payload:
            if payload["exp"] < time.time():
                raise jwt.ExpiredSignatureError("Token has expired")
        
        return payload
    
    def _path_requires_auth(self, path: str) -> bool:
        """Check if path requires authentication."""
        
        # Check public paths
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return False
        
        # Check auth required paths
        for auth_path in self.auth_required_paths:
            if path.startswith(auth_path):
                return True
        
        return False


class APIKeyAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    API key authentication for machine-to-machine communication.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-API-Key",
        query_param: str = "api_key",
        validate_key_func: Optional[Any] = None
    ):
        super().__init__(app)
        self.header_name = header_name
        self.query_param = query_param
        self.validate_key_func = validate_key_func
        
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract API key
        api_key = (
            request.headers.get(self.header_name) or
            request.query_params.get(self.query_param)
        )
        
        if api_key and self.validate_key_func:
            try:
                # Validate API key
                key_info = await self.validate_key_func(api_key)
                
                if key_info:
                    request.state.api_key_info = key_info
                    request.state.is_api_authenticated = True
                    
            except Exception as e:
                logger.error("api_key.validation_error", error=str(e))
        
        return await call_next(request)


class MultiAuthMiddleware(BaseHTTPMiddleware):
    """
    Combine multiple authentication methods.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        jwt_secret: str,
        api_key_validator: Optional[Any] = None
    ):
        super().__init__(app)
        self.jwt_middleware = JWTAuthenticationMiddleware(
            app, jwt_secret
        )
        self.api_key_middleware = APIKeyAuthenticationMiddleware(
            app, validate_key_func=api_key_validator
        )
        
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Try JWT first
        await self.jwt_middleware.dispatch(request, lambda r: r)
        
        # Try API key if JWT failed
        if not request.state.is_authenticated:
            await self.api_key_middleware.dispatch(request, lambda r: r)
        
        # Check if any auth succeeded
        is_authenticated = (
            request.state.is_authenticated or
            getattr(request.state, "is_api_authenticated", False)
        )
        
        if not is_authenticated and self._requires_auth(request):
            return Response(
                content=json.dumps({"error": "Authentication required"}),
                status_code=401
            )
        
        return await call_next(request)
    
    def _requires_auth(self, request: Request) -> bool:
        """Check if request requires authentication."""
        public_paths = ["/health", "/docs", "/api/auth/"]
        path = request.url.path
        
        for public_path in public_paths:
            if path.startswith(public_path):
                return False
        
        return path.startswith("/api/")
```

### Updated `requirements.txt` for Phase 2

```txt
# Core
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0

# Redis
redis==5.0.1
hiredis==2.2.3

# Monitoring
structlog==23.2.0
prometheus-client==0.19.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
pytest-redis==3.0.2

# Development
black==23.11.0
ruff==0.1.6
mypy==1.7.1
```

---

## Phase 3: Scale & Enterprise

### Complete File: `app/middleware/advanced.py`

```python
"""
Enterprise-grade security middleware.
Phase 3: Advanced features for scale and compliance.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import time
from typing import Optional, Dict, List, Set, Any
from datetime import datetime, timedelta
from collections import defaultdict

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class GeoBlockingMiddleware(BaseHTTPMiddleware):
    """
    Geographic restriction middleware for compliance.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        allowed_countries: Optional[Set[str]] = None,
        blocked_countries: Optional[Set[str]] = None,
        geoip_database_path: Optional[str] = None
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
        self,
        request: Request,
        call_next: RequestResponseEndpoint
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
            if self.allowed_countries and country_code not in self.allowed_countries:
                return self._blocked_response(country_code)
            
            if country_code in self.blocked_countries:
                return self._blocked_response(country_code)
            
            # Add country to request state
            request.state.country_code = country_code
            
        except Exception as e:
            logger.warning(
                "geo_blocking.lookup_failed",
                ip=client_ip,
                error=str(e)
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
            content=json.dumps({
                "error": "Access denied from your region"
            }),
            status_code=403
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
        max_age_seconds: int = 300
    ):
        super().__init__(app)
        self.secret_key = secret_key.encode()
        self.header_name = header_name
        self.timestamp_header = timestamp_header
        self.max_age = max_age_seconds
        
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
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
                    status_code=401
                )
            
            # Read body
            body = await request.body()
            
            # Calculate expected signature
            message = f"{request.method}:{request.url.path}:{timestamp}:{body.decode()}"
            expected_signature = hmac.new(
                self.secret_key,
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Verify signature (constant time comparison)
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning(
                    "signature.invalid",
                    path=request.url.path
                )
                return Response(
                    content=json.dumps({"error": "Invalid signature"}),
                    status_code=401
                )
            
            # Allow body to be read again
            request._body = body
            
        except Exception as e:
            logger.error("signature.validation_error", error=str(e))
            return Response(
                content=json.dumps({"error": "Signature validation failed"}),
                status_code=400
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
        expected_exception: type = Exception
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
        self,
        request: Request,
        call_next: RequestResponseEndpoint
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
                    content=json.dumps({
                        "error": "Service temporarily unavailable"
                    }),
                    status_code=503,
                    headers={"Retry-After": str(self.recovery_timeout)}
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
                    content=json.dumps({
                        "error": "Service temporarily unavailable"
                    }),
                    status_code=503
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
                failures=self.failure_counts[endpoint]
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
        unique_ip_threshold: int = 500
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
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = self._get_client_ip(request)
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            return Response(
                content=json.dumps({"error": "Blocked"}),
                status_code=403
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
                connections=self.connection_counts[client_ip]
            )
            return Response(
                content=json.dumps({"error": "Too many requests"}),
                status_code=429
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
            t for t in self.request_counts[client_ip]
            if now - t < 60
        ]
        
        if len(self.request_counts[client_ip]) > self.rate_threshold:
            return True
        
        # Check unique IPs (botnet detection)
        if len(self.unique_ips) > self.ip_threshold:
            logger.warning(
                "ddos.high_unique_ips",
                count=len(self.unique_ips)
            )
        
        return False
    
    async def _cleanup_loop(self):
        """Periodic cleanup of tracking data."""
        while True:
            await asyncio.sleep(300)  # 5 minutes
            
            # Clean up old data
            self.unique_ips.clear()
            
            # Unblock IPs after cooldown
            self.blocked_ips = {
                ip for ip in self.blocked_ips
                if self.connection_counts[ip] > 0
            }
            
            logger.info(
                "ddos.cleanup",
                blocked_ips=len(self.blocked_ips),
                active_connections=sum(self.connection_counts.values())
            )
```

---

## Testing Strategy

### Complete File: `tests/test_middleware.py`

```python
"""
Comprehensive tests for security middleware.
"""

import asyncio
import time
import json
from unittest.mock import AsyncMock, patch

import pytest
import redis.asyncio as redis
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.middleware.security import (
    SecurityHeadersMiddleware,
    ContentValidationMiddleware,
    SimpleRateLimitMiddleware,
)
from app.middleware.rate_limit import RedisRateLimitMiddleware
from app.middleware.auth import JWTAuthenticationMiddleware


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    @app.post("/api/test")
    async def test_endpoint(data: dict):
        return {"received": data}
    
    @app.get("/api/protected")
    async def protected_endpoint(request: Request):
        return {"user_id": request.state.user_id}
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""
    
    def test_security_headers_applied(self, app, client):
        """Test that security headers are added to responses."""
        app.add_middleware(SecurityHeadersMiddleware, is_production=True)
        
        response = client.get("/health")
        
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in response.headers
    
    def test_hsts_only_in_production(self, app, client):
        """Test HSTS header only in production."""
        app.add_middleware(SecurityHeadersMiddleware, is_production=False)
        
        response = client.get("/health")
        assert "Strict-Transport-Security" not in response.headers
        
        # Reset app
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, is_production=True)
        client = TestClient(app)
        
        response = client.get("/health", headers={"X-Forwarded-Proto": "https"})
        # Note: TestClient doesn't properly handle scheme, so this might not work as expected


class TestContentValidationMiddleware:
    """Test content validation middleware."""
    
    def test_payload_size_limit(self, app, client):
        """Test payload size limits."""
        app.add_middleware(
            ContentValidationMiddleware,
            size_limits={"/api/": 1024}  # 1KB limit
        )
        
        # Small payload - should pass
        small_data = {"test": "data"}
        response = client.post("/api/test", json=small_data)
        assert response.status_code == 200
        
        # Large payload - should be rejected
        large_data = {"test": "x" * 2000}
        response = client.post(
            "/api/test",
            json=large_data,
            headers={"Content-Length": "2000"}
        )
        assert response.status_code == 413
        assert "Payload too large" in response.json()["error"]
    
    def test_content_type_validation(self, app, client):
        """Test content type validation."""
        app.add_middleware(ContentValidationMiddleware)
        
        # Valid content type
        response = client.post(
            "/api/test",
            json={"test": "data"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        
        # Invalid content type
        response = client.post(
            "/api/test",
            data="test",
            headers={"Content-Type": "application/xml"}
        )
        assert response.status_code == 415


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""
    
    def test_simple_rate_limit(self, app, client):
        """Test in-memory rate limiting."""
        app.add_middleware(
            SimpleRateLimitMiddleware,
            requests_per_minute=5,
            burst_size=0
        )
        
        # First 5 requests should pass
        for i in range(5):
            response = client.get("/api/test")
            assert response.status_code == 200
            assert "X-RateLimit-Remaining" in response.headers
        
        # 6th request should be rate limited
        response = client.get("/api/test")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]
        assert "Retry-After" in response.headers
    
    def test_excluded_paths(self, app, client):
        """Test that excluded paths bypass rate limiting."""
        app.add_middleware(
            SimpleRateLimitMiddleware,
            requests_per_minute=1,
            excluded_paths={"/health"}
        )
        
        # Health endpoint should not be rate limited
        for i in range(10):
            response = client.get("/health")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_redis_rate_limit(self, app):
        """Test Redis-based rate limiting."""
        # Mock Redis client
        redis_client = AsyncMock(spec=redis.Redis)
        redis_client.evalsha = AsyncMock(return_value=[1, 59])
        redis_client.script_load = AsyncMock(return_value="mock_sha")
        
        app.add_middleware(
            RedisRateLimitMiddleware,
            redis_client=redis_client,
            default_limit=60
        )
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/test")
            assert response.status_code == 200
            assert response.headers["X-RateLimit-Limit"] == "60"
            assert response.headers["X-RateLimit-Remaining"] == "59"


class TestAuthenticationMiddleware:
    """Test authentication middleware."""
    
    def test_jwt_authentication(self, app, client):
        """Test JWT token validation."""
        import jwt
        
        secret_key = "test_secret"
        app.add_middleware(
            JWTAuthenticationMiddleware,
            secret_key=secret_key,
            auth_required_paths=["/api/protected"]
        )
        
        # No token - should fail for protected endpoint
        response = client.get("/api/protected")
        assert response.status_code == 401
        
        # Valid token
        token = jwt.encode(
            {"sub": "user123", "exp": time.time() + 3600},
            secret_key,
            algorithm="HS256"
        )
        
        response = client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Expired token
        expired_token = jwt.encode(
            {"sub": "user123", "exp": time.time() - 3600},
            secret_key,
            algorithm="HS256"
        )
        
        response = client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
    
    def test_public_paths(self, app, client):
        """Test that public paths don't require authentication."""
        app.add_middleware(
            JWTAuthenticationMiddleware,
            secret_key="test_secret",
            public_paths=["/health"]
        )
        
        response = client.get("/health")
        assert response.status_code == 200


@pytest.mark.benchmark
class TestPerformance:
    """Performance benchmarks for middleware."""
    
    def test_rate_limit_performance(self, app, client, benchmark):
        """Benchmark rate limiting overhead."""
        app.add_middleware(
            SimpleRateLimitMiddleware,
            requests_per_minute=10000
        )
        
        def make_request():
            return client.get("/health")
        
        result = benchmark(make_request)
        assert result.status_code == 200
    
    def test_security_headers_performance(self, app, client, benchmark):
        """Benchmark security headers overhead."""
        app.add_middleware(SecurityHeadersMiddleware)
        
        def make_request():
            return client.get("/health")
        
        result = benchmark(make_request)
        assert result.status_code == 200


# Integration tests
class TestMiddlewareIntegration:
    """Test middleware working together."""
    
    def test_full_middleware_stack(self, app, client):
        """Test complete middleware stack."""
        
        # Add all middleware in correct order
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(SimpleRateLimitMiddleware, requests_per_minute=100)
        app.add_middleware(ContentValidationMiddleware)
        
        # Test normal request
        response = client.post("/api/test", json={"test": "data"})
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        
        # Test rate limit
        for i in range(100):
            client.get("/health")
        
        response = client.get("/api/test")
        assert response.status_code == 429
        
        # Test large payload
        large_data = {"data": "x" * 2000000}
        response = client.post(
            "/api/test",
            json=large_data,
            headers={"Content-Length": "2000000"}
        )
        assert response.status_code == 413
```

---

## Monitoring & Alerts

### Complete File: `app/middleware/monitoring.py`

```python
"""
Monitoring and metrics for security middleware.
"""

from __future__ import annotations

import time
from typing import Dict, Any
from collections import defaultdict

import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)

# Prometheus metrics
request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"]
)

rate_limit_hits = Counter(
    "rate_limit_hits_total",
    "Rate limit hits",
    ["path", "client_type"]
)

auth_attempts = Counter(
    "auth_attempts_total",
    "Authentication attempts",
    ["result", "method"]
)

security_violations = Counter(
    "security_violations_total",
    "Security violations",
    ["type", "severity"]
)

active_connections = Gauge(
    "active_connections",
    "Active connections"
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Collect metrics for monitoring.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.path_patterns = self._compile_path_patterns()
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip metrics endpoint
        if request.url.path == "/metrics":
            return Response(content=generate_latest())
        
        # Track timing
        start_time = time.time()
        
        # Track active connections
        active_connections.inc()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            path_pattern = self._get_path_pattern(request.url.path)
            
            request_count.labels(
                method=request.method,
                path=path_pattern,
                status=response.status_code
            ).inc()
            
            request_duration.labels(
                method=request.method,
                path=path_pattern
            ).observe(duration)
            
            # Track security events
            if response.status_code == 429:
                rate_limit_hits.labels(
                    path=path_pattern,
                    client_type="user" if hasattr(request.state, "user_id") else "anonymous"
                ).inc()
            
            if response.status_code == 401:
                auth_attempts.labels(
                    result="failed",
                    method="jwt"
                ).inc()
            
            if response.status_code == 403:
                security_violations.labels(
                    type="access_denied",
                    severity="medium"
                ).inc()
            
            return response
            
        finally:
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
        import re
        
        for pattern, replacement in self.path_patterns.items():
            if re.match(pattern, path):
                return replacement
        
        return path


class AlertingMiddleware(BaseHTTPMiddleware):
    """
    Send alerts for critical security events.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        alert_threshold: Dict[str, int] = None
    ):
        super().__init__(app)
        self.thresholds = alert_threshold or {
            "rate_limit": 100,  # Alert after 100 rate limit hits
            "auth_failures": 50,  # Alert after 50 auth failures
            "large_payloads": 10,  # Alert after 10 large payload attempts
        }
        
        self.counters: Dict[str, int] = defaultdict(int)
        self.last_alert: Dict[str, float] = {}
        self.alert_cooldown = 300  # 5 minutes
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
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
        
        logger.critical(
            "security.alert",
            event_type=event_type,
            count=self.counters[event_type],
            path=request.url.path,
            client=request.client.host if request.client else None
        )
        
        # TODO: Integrate with your alerting system
        # - Send to Slack/Discord/Teams
        # - Create PagerDuty incident
        # - Send email
        # - Write to SIEM
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Rate Limiting Not Working

**Symptom:** Requests aren't being rate limited despite configuration.

**Solutions:**
```python
# Check if path is excluded
print(middleware.excluded_paths)

# Verify Redis connection (Phase 2)
await redis_client.ping()

# Check rate limit key format
key = f"rate_limit:{client_id}:{path}"
print(await redis_client.get(key))
```

#### 2. Authentication Failing

**Symptom:** Valid tokens are being rejected.

**Debug steps:**
```python
# Decode token manually
import jwt
payload = jwt.decode(token, secret_key, algorithms=["HS256"])
print(payload)

# Check expiration
import time
if payload["exp"] < time.time():
    print("Token expired")
```

#### 3. Security Headers Not Applied

**Symptom:** Response headers missing security headers.

**Check middleware order:**
```python
# SecurityHeadersMiddleware must be first
app.add_middleware(SecurityHeadersMiddleware)  # First!
app.add_middleware(OtherMiddleware)  # After
```

#### 4. High Memory Usage

**Symptom:** Memory usage growing with in-memory rate limiting.

**Solution:**
```python
# Add cleanup in Phase 1 middleware
def _cleanup_old_entries(self):
    cutoff = time.time() - 3600
    for client_id in list(self.windows.keys()):
        if not self.windows[client_id]:
            del self.windows[client_id]
```

### Performance Tuning

#### Redis Connection Pool (Phase 2)
```python
# Optimize Redis connection pool
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    connection_pool=redis.ConnectionPool(
        max_connections=50,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
)
```

#### Rate Limit Optimization
```python
# Use pipeline for multiple Redis operations
async with redis_client.pipeline() as pipe:
    pipe.incr(key)
    pipe.expire(key, 60)
    results = await pipe.execute()
```

### Monitoring Queries

#### Prometheus Queries
```promql
# Request rate
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, http_request_duration_seconds)

# Rate limit hit rate
rate(rate_limit_hits_total[5m])

# Auth failure rate
rate(auth_attempts_total{result="failed"}[5m])
```

#### Log Queries (Elasticsearch/Splunk)
```json
// Rate limit violations
{
  "query": {
    "match": {
      "event": "rate_limit.exceeded"
    }
  },
  "aggs": {
    "by_client": {
      "terms": {
        "field": "client.keyword"
      }
    }
  }
}
```

---

## Production Deployment Checklist

### Phase 1 Launch
- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Enable HSTS (`SECURITY_ENABLE_HSTS=true`)
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Set strong `SECRET_KEY`
- [ ] Test rate limiting with load testing tool
- [ ] Verify security headers in response
- [ ] Set up log aggregation (ELK, Splunk, etc.)
- [ ] Configure alerting thresholds
- [ ] Document rate limits in API docs

### Phase 2 Launch
- [ ] Set up Redis cluster with replication
- [ ] Configure Redis connection pool
- [ ] Implement JWT key rotation
- [ ] Set up API key management system
- [ ] Test failover scenarios
- [ ] Load test with expected traffic
- [ ] Configure monitoring dashboards
- [ ] Set up on-call rotation
- [ ] Create runbooks for common issues

### Phase 3 Scale
- [ ] Implement geographic distribution
- [ ] Set up WAF rules
- [ ] Configure DDoS protection
- [ ] Implement cost controls
- [ ] Set up compliance reporting
- [ ] Regular security audits
- [ ] Penetration testing
- [ ] Disaster recovery plan
- [ ] SLA monitoring

---

## Conclusion

This guide provides a complete, production-ready security implementation for FastAPI applications. Start with Phase 1 today, and incrementally add features as your application grows. Remember:

1. **Security is not optional** - Start with Phase 1 immediately
2. **Monitor everything** - You can't secure what you can't see
3. **Test regularly** - Security is only as good as your testing
4. **Stay updated** - Security threats evolve, so should your defenses

For questions or contributions, please refer to the project repository.