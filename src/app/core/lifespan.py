from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from .config import AppSettings


def build_lifespan(settings: AppSettings):
    logger = structlog.get_logger("app.lifespan")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application.startup",
            environment=settings.environment.value,
            version=settings.project_version,
        )
        try:
            yield
        finally:
            logger.info("application.shutdown")

    return lifespan
