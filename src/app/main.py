from fastapi import FastAPI

from .api.routes import register_routes
from .core.config import AppSettings, get_app_settings
from .core.lifespan import build_lifespan
from .core.logging import configure_logging
from .core.middleware import register_middlewares


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """
    Factory function to create and configure a FastAPI application instance.

    This function is designed to be used with uvicorn's --factory flag, which
    delays application instantiation until the server starts. This pattern
    provides several benefits:

    - Delayed initialization: The app is created when uvicorn calls this function
    - Configuration flexibility: Different settings can be passed for different environments
    - Testing support: Fresh app instances can be created for each test with custom settings
    - Cleaner separation: Setup logic is encapsulated in a callable factory

    Args:
        settings: Optional AppSettings instance. If not provided, settings will be
                 loaded from environment variables via get_app_settings().

    Returns:
        Configured FastAPI application instance ready to handle requests.

    Example:
        # Using with uvicorn CLI (factory pattern):
        uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000

        # Creating an instance directly (e.g., for testing):
        from app.core.config import AppSettings
        test_settings = AppSettings(debug=True, environment="test")
        app = create_app(settings=test_settings)
    """
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
