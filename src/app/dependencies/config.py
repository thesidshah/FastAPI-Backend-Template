from ..core.config import AppSettings, get_app_settings


def get_settings() -> AppSettings:
    """FastAPI dependency that returns cached application settings."""
    return get_app_settings()
