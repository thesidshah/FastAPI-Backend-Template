from fastapi import APIRouter, FastAPI

from ...core.config import AppSettings
from .health import router as health_router
from .meta import router as meta_router


def build_api_router(_: AppSettings) -> APIRouter:
    router = APIRouter()
    router.include_router(meta_router)
    router.include_router(health_router, prefix="/health", tags=["Health"])
    return router


def register_routes(app: FastAPI, settings: AppSettings) -> None:
    """Register API routers on the FastAPI application."""
    api_router = build_api_router(settings)
    app.include_router(api_router, prefix=settings.api_prefix)
