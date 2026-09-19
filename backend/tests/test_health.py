"""Tests for FastAPI endpoints and health checks."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Verify GET /health returns 200 with status ok."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_root_index_endpoint():
    """Verify GET / returns service metadata."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok" if "status" in data else data["milestone"] == "Milestone 1 - Backend Foundation"


@pytest.mark.asyncio
async def test_api_v1_energy_endpoint():
    """Verify GET /api/v1/energy returns valid EnergyDetailResponse payload."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/energy")
    assert response.status_code == 200
    data = response.json()
    assert "base_grid_capacity_kw" in data
    assert "effective_grid_capacity_kw" in data
    assert "solar_voltage_v" in data
    assert "available_ev_charging_power_kw" in data
    assert data["base_grid_capacity_kw"] == 25.0
    assert data["available_ev_charging_power_kw"] >= 0.0


@pytest.mark.asyncio
async def test_api_v1_evs_endpoint():
    """Verify GET /api/v1/evs returns list of connected EVs."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/evs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
