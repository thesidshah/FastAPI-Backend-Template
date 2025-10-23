from fastapi import FastAPI

from .api.routes import register_routes
from .core.config import AppSettings, get_app_settings
from .core.lifespan import build_lifespan
from .core.logging import configure_logging
from .core.middleware import register_middlewares


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Create and configure a FastAPI application instance."""
    app_settings = settings or get_app_settings()
    configure_logging(app_settings)

    app = FastAPI(
        title=app_settings.project_name,
        description=app_settings.project_description,
        version=app_settings.project_version,
        debug=app_settings.debug,
        docs_url=app_settings.docs_url,
        redoc_url=app_settings.redoc_url,
        openapi_url=app_settings.openapi_url,
        lifespan=build_lifespan(app_settings),
    )

    register_middlewares(app, app_settings)
    register_routes(app, app_settings)

    return app


app = create_app()
