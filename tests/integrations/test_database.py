from __future__ import annotations

import pytest
from app.dependencies.database import get_async_session
from app.integrations.database import get_engine
from app.services.database_example import ExampleItem
from sqlalchemy import inspect, select


@pytest.mark.asyncio
async def test_lifespan_creates_schema(async_client) -> None:  # noqa: ARG001
    """Test that database schema is created during app lifespan startup."""
    engine = get_engine()

    async with engine.begin() as connection:
        has_table = await connection.run_sync(
            lambda sync_conn: inspect(sync_conn).has_table(ExampleItem.__tablename__),
        )

    assert has_table is True


@pytest.mark.asyncio
async def test_dependency_yields_session(async_client) -> None:  # noqa: ARG001
    """Test that get_async_session dependency yields a working session."""
    # The async_client fixture initializes the database through the app's lifespan
    session = await anext(get_async_session())
    result = await session.execute(select(1))
    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_example_route_crud_flow(async_client) -> None:
    list_response = await async_client.get("/api/v1/examples/database-example/")
    assert list_response.status_code == 200
    assert list_response.json() == []

    create_payload = {"name": "Widget", "description": "demo"}
    create_response = await async_client.post(
        "/api/v1/examples/database-example/",
        json=create_payload,
    )
    assert create_response.status_code == 201
    created_item = create_response.json()
    assert created_item["name"] == create_payload["name"]
    assert created_item["description"] == create_payload["description"]

    item_id = created_item["id"]

    get_response = await async_client.get(
        f"/api/v1/examples/database-example/{item_id}",
    )
    assert get_response.status_code == 200
    assert get_response.json() == created_item

    list_response = await async_client.get("/api/v1/examples/database-example/")
    assert list_response.status_code == 200
    items = list_response.json()
    assert any(item["id"] == item_id for item in items)
