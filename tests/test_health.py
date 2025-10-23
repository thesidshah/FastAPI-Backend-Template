import pytest


@pytest.mark.asyncio
async def test_liveness_endpoint(async_client):
    response = await async_client.get("/api/v1/health/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pass"
    assert payload["service"] == "cms-backend"
    assert "timestamp" in payload


@pytest.mark.asyncio
async def test_readiness_endpoint(async_client):
    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] in {"pass", "warn"}
    assert "checks" in payload
    assert payload["checks"]["database"] == "pass"


@pytest.mark.asyncio
async def test_metadata_endpoint(async_client):
    response = await async_client.get("/api/v1/metadata")
    assert response.status_code == 200

    payload = response.json()
    assert payload["name"]
    assert payload["version"]
    assert payload["environment"]
