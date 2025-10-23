from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProbeStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class HealthResponse(BaseModel):
    status: ProbeStatus = Field(default=ProbeStatus.PASS)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    environment: str = Field(..., description="Current runtime environment")
    version: str = Field(..., description="Service version")
    service: str = Field(default="cms-backend")
    details: dict[str, Any] = Field(default_factory=dict)


class ReadinessResponse(HealthResponse):
    checks: dict[str, ProbeStatus] = Field(default_factory=dict)
