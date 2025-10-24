import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from app.core.config import AppSettings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def app() -> FastAPI:
    settings = AppSettings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
    )
    return create_app(settings=settings)


@pytest.fixture()
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, Any]:
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver",
        ) as client:
            yield client
