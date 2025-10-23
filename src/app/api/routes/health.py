from fastapi import APIRouter, Depends, status

from ...dependencies import get_health_service
from ...schemas.health import HealthResponse, ReadinessResponse
from ...services.health import HealthService

router = APIRouter()


@router.get(
    "/live",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    tags=["Health"],
)
async def live(
    health_service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    """
    Lightweight liveness check used by orchestration platforms.

    Returns metadata about the running service without performing expensive
    dependency checks.
    """
    return await health_service.liveness()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    tags=["Health"],
)
async def ready(
    health_service: HealthService = Depends(get_health_service),
) -> ReadinessResponse:
    """
    Readiness check that validates critical downstream dependencies.

    Extend the underlying HealthService to include database, cache, or message
    broker checks.
    """
    return await health_service.readiness()
