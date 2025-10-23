from fastapi import Depends

from ..core.config import AppSettings
from ..services.health import HealthService
from .config import get_settings


def get_health_service(settings: AppSettings = Depends(get_settings)) -> HealthService:
    """Provide a HealthService instance with configured settings."""
    return HealthService(settings=settings)
