from collections.abc import AsyncGenerator
from typing import Any

import pytest
from app.main import create_app
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def app() -> FastAPI:
    return create_app()


@pytest.fixture()
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, Any]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
