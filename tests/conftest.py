from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
import sys

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from app.core.config import AppSettings
from app.main import create_app


@pytest.fixture(scope="session")
def app() -> FastAPI:
    settings = AppSettings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
    )
    return create_app(settings=settings)


@pytest.fixture()
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, Any]:
    transport = ASGITransport(app=app, lifespan="on")
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
