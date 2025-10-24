from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import structlog
from fastapi import FastAPI

from .config import AppSettings
from ..integrations.database import init_database, shutdown_database
from ..services.database_example import create_example_schema


def build_lifespan(
    settings: AppSettings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    logger = structlog.get_logger("app.lifespan")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application.startup",
            environment=settings.environment.value,
            version=settings.project_version,
        )
        engine = await init_database(settings)
        await create_example_schema(engine)
        try:
            yield
        finally:
            await shutdown_database()
            logger.info("application.shutdown")

    return lifespan
