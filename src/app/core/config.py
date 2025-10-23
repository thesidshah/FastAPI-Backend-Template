from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class LogFormat(str, Enum):
    JSON = "json"
    CONSOLE = "console"


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        env_prefix="APP_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    project_name: str = "CMS Backend API"
    project_description: str = "Commission Management System Backend API"
    project_version: str = "0.1.0"

    environment: Environment = Environment.LOCAL
    debug: bool = False

    api_prefix: str = "/api/v1"
    default_pagination_limit: int = Field(default=50, ge=1, le=500)

    cors_allow_origins: list[str] = Field(default_factory=list)
    cors_allow_methods: Sequence[str] = (
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    )
    cors_allow_headers: Sequence[str] = (
        "Authorization",
        "Content-Type",
        "X-Request-ID",
    )
    cors_allow_credentials: bool = True
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])

    log_level: str = "INFO" # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_format: LogFormat = LogFormat.JSON
    log_include_caller: bool = False

    request_timeout_seconds: int = Field(default=60, ge=1)

    enable_tracing: bool = False
    enable_metrics: bool = False

    @computed_field
    @property
    def docs_url(self) -> str | None:  # pragma: no cover
        return (
            "/docs"
            if self.environment in {Environment.LOCAL, Environment.STAGING}
            else None
        )

    @computed_field
    @property
    def redoc_url(self) -> str | None:  # pragma: no cover
        return (
            "/redoc"
            if self.environment in {Environment.LOCAL, Environment.STAGING}
            else None
        )

    @computed_field
    @property
    def openapi_url(self) -> str | None:  # pragma: no cover - simple computed property
        return "/openapi.json"


class SecuritySettings(BaseSettings):
    """Security-specific configuration."""

    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        env_prefix="SECURITY_",
        extra="ignore",
    )

    # Rate limiting (Phase 1)
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = Field(default=60, ge=1)
    rate_limit_per_hour: int = Field(default=1000, ge=1)
    rate_limit_burst: int = Field(default=10, ge=0)

    # Content validation (Phase 1)
    max_upload_size: int = Field(default=50 * 1024 * 1024, ge=1024)  # 50MB
    max_request_size: int = Field(default=1 * 1024 * 1024, ge=1024)  # 1MB
    block_null_bytes: bool = True

    # Security headers (Phase 1)
    enable_hsts: bool = True
    enable_csp: bool = False
    csp_policy: str = "default-src 'self'; script-src 'self' 'unsafe-inline'"

    # Proxy settings (Phase 1)
    trusted_proxies: set[str] = Field(default_factory=lambda: {"127.0.0.1", "::1"})
    trust_proxy_headers: bool = False

    # Redis (Phase 2)
    redis_url: str | None = None
    redis_enabled: bool = False

    # JWT Authentication (Phase 2)
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = Field(default=60, ge=1)

    # API Keys (Phase 2)
    api_key_header: str = "X-API-Key"

    # Advanced features (Phase 3)
    enable_geo_blocking: bool = False
    geoip_database_path: str | None = None
    allowed_countries: set[str] | None = None
    blocked_countries: set[str] = Field(default_factory=set)

    enable_circuit_breaker: bool = False
    circuit_breaker_threshold: int = Field(default=5, ge=1)
    circuit_breaker_timeout: int = Field(default=60, ge=1)

    enable_ddos_protection: bool = False
    ddos_syn_threshold: int = Field(default=100, ge=1)
    ddos_rate_threshold: int = Field(default=1000, ge=1)

    # Monitoring (Phase 3)
    enable_prometheus: bool = False
    enable_alerting: bool = False
    alert_rate_limit_threshold: int = Field(default=100, ge=1)
    alert_auth_failure_threshold: int = Field(default=50, ge=1)


@lru_cache
def get_app_settings() -> AppSettings:
    """Return cached application settings instance."""
    return AppSettings()


@lru_cache
def get_security_settings() -> SecuritySettings:
    """Return cached security settings instance."""
    return SecuritySettings()
