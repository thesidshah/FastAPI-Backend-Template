"""
Authentication middleware for JWT token validation.
Phase 2: Production authentication with multiple providers.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)

# Try to import JWT libraries, but make them optional
try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT not installed, JWT authentication not available")


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
            "/health",
            "/health/ready",
            "/docs",
            "/openapi.json",
            "/api/auth/",
        ]
        self.jwks_url = jwks_url

        if not JWT_AVAILABLE:
            logger.error("JWT library not available, authentication will not work")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
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

        if token and JWT_AVAILABLE:
            try:
                payload = await self._validate_token(token)

                # Set user state
                request.state.user = payload
                request.state.user_id = payload.get("sub") or payload.get("user_id")
                request.state.user_tier = payload.get("tier", "free")
                request.state.scopes = payload.get("scopes", [])
                request.state.is_authenticated = True

                logger.info("auth.success", user_id=request.state.user_id, path=path)

            except jwt.ExpiredSignatureError:
                logger.warning("auth.token_expired", path=path)
                if requires_auth:
                    return Response(
                        content=json.dumps({"error": "Token expired"}),
                        status_code=401,
                        headers={"WWW-Authenticate": "Bearer"},
                        media_type="application/json",
                    )

            except jwt.InvalidTokenError as e:
                logger.warning("auth.invalid_token", error=str(e), path=path)
                if requires_auth:
                    return Response(
                        content=json.dumps({"error": "Invalid token"}),
                        status_code=401,
                        headers={"WWW-Authenticate": "Bearer"},
                        media_type="application/json",
                    )

        # Check if authentication is required
        if requires_auth and not request.state.is_authenticated:
            return Response(
                content=json.dumps({"error": "Authentication required"}),
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
                media_type="application/json",
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

        if not JWT_AVAILABLE:
            raise ValueError("JWT library not available")

        # Decode token
        payload = jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
            options={"verify_exp": True},
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
        validate_key_func: Optional[Any] = None,
    ):
        super().__init__(app)
        self.header_name = header_name
        self.query_param = query_param
        self.validate_key_func = validate_key_func

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract API key
        api_key = request.headers.get(self.header_name) or request.query_params.get(
            self.query_param
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
        api_key_validator: Optional[Any] = None,
    ):
        super().__init__(app)
        self.jwt_middleware = JWTAuthenticationMiddleware(app, jwt_secret)
        self.api_key_middleware = APIKeyAuthenticationMiddleware(
            app, validate_key_func=api_key_validator
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Initialize request state
        request.state.user = None
        request.state.user_id = None
        request.state.is_authenticated = False

        # Extract JWT token
        jwt_token = self.jwt_middleware._extract_token(request)

        if jwt_token and JWT_AVAILABLE:
            try:
                payload = await self.jwt_middleware._validate_token(jwt_token)
                request.state.user = payload
                request.state.user_id = payload.get("sub") or payload.get("user_id")
                request.state.user_tier = payload.get("tier", "free")
                request.state.scopes = payload.get("scopes", [])
                request.state.is_authenticated = True
                logger.info("auth.jwt_success", user_id=request.state.user_id)
            except Exception as e:
                logger.warning("auth.jwt_failed", error=str(e))

        # Try API key if JWT failed
        if not request.state.is_authenticated:
            api_key = request.headers.get(
                self.api_key_middleware.header_name
            ) or request.query_params.get(self.api_key_middleware.query_param)

            if api_key and self.api_key_middleware.validate_key_func:
                try:
                    key_info = await self.api_key_middleware.validate_key_func(api_key)
                    if key_info:
                        request.state.api_key_info = key_info
                        request.state.is_api_authenticated = True
                        request.state.is_authenticated = True
                        logger.info("auth.api_key_success")
                except Exception as e:
                    logger.error("auth.api_key_failed", error=str(e))

        # Check if any auth succeeded
        is_authenticated = request.state.is_authenticated or getattr(
            request.state, "is_api_authenticated", False
        )

        if not is_authenticated and self._requires_auth(request):
            return Response(
                content=json.dumps({"error": "Authentication required"}),
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)

    def _requires_auth(self, request: Request) -> bool:
        """Check if request requires authentication."""
        public_paths = ["/health", "/health/ready", "/docs", "/api/auth/"]
        path = request.url.path

        for public_path in public_paths:
            if path.startswith(public_path):
                return False

        return path.startswith("/api/")
