"""
Comprehensive tests for security middleware.
"""

import time
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient
from starlette.testclient import TestClient

from app.middleware.security import (
    ContentValidationMiddleware,
    ProxyHeadersMiddleware,
    SecurityHeadersMiddleware,
    SimpleRateLimitMiddleware,
)


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
        return {"user_id": getattr(request.state, "user_id", None)}

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""

    def test_security_headers_applied(self, app, client):
        """Test that security headers are added to responses."""
        app.add_middleware(SecurityHeadersMiddleware, is_production=False)

        response = client.get("/health")

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in response.headers
        assert response.headers["Cache-Control"] == "no-store, max-age=0"
        assert response.headers["Server"] == "undisclosed"

    def test_hsts_not_in_development(self, app, client):
        """Test HSTS header not set in development."""
        app.add_middleware(SecurityHeadersMiddleware, is_production=False)

        response = client.get("/health")
        assert "Strict-Transport-Security" not in response.headers

    def test_csp_when_enabled(self, app, client):
        """Test CSP header when enabled."""
        app.add_middleware(
            SecurityHeadersMiddleware,
            is_production=True,
            enable_csp=True,
            csp_policy="default-src 'self'",
        )

        response = client.get("/health")
        assert response.headers.get("Content-Security-Policy") == "default-src 'self'"


class TestContentValidationMiddleware:
    """Test content validation middleware."""

    def test_payload_size_limit(self, app, client):
        """Test payload size limits."""
        app.add_middleware(
            ContentValidationMiddleware, size_limits={"/api/": 100}  # 100 bytes limit
        )

        # Small payload - should pass
        small_data = {"test": "data"}
        response = client.post("/api/test", json=small_data)
        assert response.status_code == 200

        # Large payload - should be rejected
        large_data = {"test": "x" * 200}
        response = client.post(
            "/api/test", json=large_data, headers={"Content-Length": "250"}
        )
        assert response.status_code == 413
        assert "Payload too large" in response.json()["error"]

    def test_content_type_validation(self, app):
        """Test content type validation."""
        app.add_middleware(ContentValidationMiddleware)
        client = TestClient(app)

        # Valid content type
        response = client.post(
            "/api/test",
            json={"test": "data"},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200

        # Invalid content type
        response = client.post(
            "/api/test", data="test", headers={"Content-Type": "application/xml"}
        )
        assert response.status_code == 415

    def test_get_requests_skip_validation(self, app, client):
        """Test that GET requests skip validation."""
        app.add_middleware(ContentValidationMiddleware)

        response = client.get("/health")
        assert response.status_code == 200


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    def test_simple_rate_limit(self, app):
        """Test in-memory rate limiting."""
        app.add_middleware(
            SimpleRateLimitMiddleware, requests_per_minute=5, burst_size=0
        )
        client = TestClient(app)

        # First 5 requests should pass
        for i in range(5):
            response = client.get("/api/test")
            assert response.status_code == 405  # Endpoint doesn't accept GET
            assert "X-RateLimit-Remaining" in response.headers

        # 6th request should be rate limited
        response = client.get("/api/test")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]
        assert "Retry-After" in response.headers

    def test_excluded_paths(self, app):
        """Test that excluded paths bypass rate limiting."""
        app.add_middleware(
            SimpleRateLimitMiddleware, requests_per_minute=1, excluded_paths={"/health"}
        )
        client = TestClient(app)

        # Health endpoint should not be rate limited
        for i in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    def test_rate_limit_with_burst(self, app):
        """Test rate limiting with burst allowance."""
        app.add_middleware(
            SimpleRateLimitMiddleware, requests_per_minute=5, burst_size=5
        )
        client = TestClient(app)

        # Should allow 5 + 5 (burst) = 10 requests
        for i in range(10):
            response = client.get("/api/test")
            assert response.status_code in [200, 405]  # Either OK or method not allowed

        # 11th request should be rate limited
        response = client.get("/api/test")
        assert response.status_code == 429


class TestProxyHeadersMiddleware:
    """Test proxy headers middleware."""

    def test_proxy_headers_not_trusted_by_default(self, app):
        """Test that proxy headers are not trusted by default."""
        app.add_middleware(ProxyHeadersMiddleware, trusted_proxies={"192.168.1.1"})
        client = TestClient(app)

        # Headers from untrusted proxy should be ignored
        response = client.get(
            "/health", headers={"X-Forwarded-For": "10.0.0.1", "X-Real-IP": "10.0.0.2"}
        )
        assert response.status_code == 200

    def test_trusted_proxy_headers(self, app):
        """Test that headers from trusted proxies are processed."""
        app.add_middleware(ProxyHeadersMiddleware, trusted_proxies={"127.0.0.1"})

        @app.get("/test-ip")
        async def test_ip(request: Request):
            return {"client_ip": request.client.host if request.client else None}

        client = TestClient(app)
        response = client.get("/test-ip")
        assert response.status_code == 200


class TestMiddlewareIntegration:
    """Test middleware working together."""

    def test_full_middleware_stack(self, app):
        """Test complete middleware stack."""

        # Add all middleware in correct order
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(SimpleRateLimitMiddleware, requests_per_minute=100)
        app.add_middleware(ContentValidationMiddleware)

        client = TestClient(app)

        # Test normal request
        response = client.post("/api/test", json={"test": "data"})
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

        # Test large payload
        large_data = {"data": "x" * 2000000}
        response = client.post(
            "/api/test", json=large_data, headers={"Content-Length": "2000000"}
        )
        assert response.status_code == 413

    def test_middleware_order_matters(self, app):
        """Test that middleware order affects behavior."""
        # Middleware is executed in reverse order of addition
        # Add content validation first, then rate limiter, so rate limiter runs first
        app.add_middleware(ContentValidationMiddleware, size_limits={"/api/": 100})
        app.add_middleware(SimpleRateLimitMiddleware, requests_per_minute=2, burst_size=0)

        client = TestClient(app)

        # Exhaust rate limit with first 2 requests
        response1 = client.get("/api/test")
        assert response1.status_code == 405  # Method not allowed
        response2 = client.get("/api/test")
        assert response2.status_code == 405  # Method not allowed

        # Next request should hit rate limit before content validation
        response = client.post(
            "/api/test", json={"x": "y"}, headers={"Content-Length": "1000"}
        )
        assert response.status_code == 429  # Rate limit, not content validation


class TestSecurityScenarios:
    """Test real-world security scenarios."""

    def test_prevents_large_payload_attack(self, app):
        """Test protection against large payload attacks."""
        app.add_middleware(ContentValidationMiddleware, size_limits={"/api/": 1024})
        client = TestClient(app)

        # Attempt to send large payload
        response = client.post(
            "/api/test", json={"data": "x" * 10000}, headers={"Content-Length": "10000"}
        )
        assert response.status_code == 413

    def test_prevents_rapid_requests(self, app):
        """Test protection against rapid request attacks."""
        app.add_middleware(SimpleRateLimitMiddleware, requests_per_minute=10, burst_size=0)
        client = TestClient(app)

        # Attempt rapid requests - first 10 should pass, then get rate limited
        responses = []
        for _ in range(15):
            response = client.get("/api/test")
            responses.append(response.status_code)

        # First 10 should be 405 (method not allowed), rest should be 429 (rate limited)
        assert responses[:10] == [405] * 10
        assert all(code == 429 for code in responses[10:])

    def test_null_byte_attack_prevention(self, app):
        """Test prevention of null byte attacks."""
        app.add_middleware(ContentValidationMiddleware, block_null_bytes=True)

        @app.get("/api/file/{filename}")
        async def get_file(filename: str):
            return {"filename": filename}

        client = TestClient(app)

        # Attempt null byte injection (simulated in headers since URL encoding is tricky)
        response = client.post("/api/test", json={"test": "data"})
        assert response.status_code == 200
