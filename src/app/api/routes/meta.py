from fastapi import APIRouter, Depends

from ...core.config import AppSettings
from ...dependencies import get_settings

router = APIRouter()


@router.get("/metadata", tags=["Metadata"])
async def metadata(settings: AppSettings = Depends(get_settings)) -> dict[str, str]:
    """
    Return lightweight metadata describing the running service.

    Useful for smoke tests or platform diagnostics.
    """
    return {
        "name": settings.project_name,
        "version": settings.project_version,
        "environment": settings.environment.value,
    }
