from __future__ import annotations

import platform
import socket
from datetime import UTC, datetime

import structlog

from ..core.config import AppSettings
from ..schemas.health import HealthResponse, ProbeStatus, ReadinessResponse


class HealthService:
    """Provide health and readiness checks for the API."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._logger = structlog.get_logger(self.__class__.__name__)

    async def liveness(self) -> HealthResponse:
        """Return basic liveness metadata indicating the service is running."""
        response = HealthResponse(
            environment=self._settings.environment.value,
            version=self._settings.project_version,
            details={
                "hostname": socket.gethostname(),
                "python_version": platform.python_version(),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        self._logger.debug("liveness.probed", response=response.model_dump())
        return response

    async def readiness(self) -> ReadinessResponse:
        """
        Perform lightweight dependency checks to assert readiness.

        In a real application this is where database connections, cache availability,
        or external service connectivity would be verified.
        """
        checks = {
            "database": ProbeStatus.PASS,
            "cache": ProbeStatus.PASS,
        }
        is_degraded = (
            ProbeStatus.FAIL in checks.values()
            or ProbeStatus.WARN in checks.values()
        )
        status = ProbeStatus.WARN if is_degraded else ProbeStatus.PASS

        response = ReadinessResponse(
            status=status,
            environment=self._settings.environment.value,
            version=self._settings.project_version,
            checks=checks,
        )
        self._logger.debug("readiness.probed", response=response.model_dump())
        return response
