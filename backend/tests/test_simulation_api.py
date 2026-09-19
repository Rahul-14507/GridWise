"""Tests for Simulation API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_api_get_simulation_state():
    """Verify GET /api/v1/simulation/state returns complete SystemState."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/simulation/state")
    assert response.status_code == 200
    data = response.json()
    assert "environment" in data
    assert "energy" in data
    assert "thermal" in data
    assert "battery" in data
    assert "evs" in data
    assert "parking" in data


@pytest.mark.asyncio
async def test_api_simulation_tick_and_control():
    """Verify POST /api/v1/simulation/tick advances state with allocations."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Load MOCK_FLEET first
        await client.post("/api/v1/simulation/scenarios/MOCK_FLEET")

        # Step tick with EV-001 allocation
        payload = {
            "ev_allocations": {"EV-001": 7.4},
            "battery_charge_power_kw": 0.0,
            "battery_discharge_power_kw": 0.0,
        }
        response = await client.post("/api/v1/simulation/tick?interval_seconds=60", json=payload)
    assert response.status_code == 200
    data = response.json()
    ev1 = next(e for e in data["evs"] if e["id"] == "EV-001")
    assert ev1["allocated_power_kw"] == 7.4


@pytest.mark.asyncio
async def test_api_optimize_tick():
    """Verify POST /api/v1/simulation/optimize-tick runs optimizer and advances tick."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/api/v1/simulation/scenarios/MOCK_FLEET")
        response = await client.post("/api/v1/simulation/optimize-tick?interval_seconds=60")
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert "decision" in data
    assert len(data["decision"]["allocations"]) > 0
    assert data["decision"]["total_allocated_power_kw"] <= data["decision"]["available_ev_power_kw"] + 0.001


@pytest.mark.asyncio
async def test_api_list_and_load_scenarios():
    """Verify listing and switching simulation scenarios."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # List scenarios
        res_list = await client.get("/api/v1/simulation/scenarios")
        assert res_list.status_code == 200
        scenarios = res_list.json()
        assert len(scenarios) >= 8

        # Load HOT_DAY scenario
        res_load = await client.post("/api/v1/simulation/scenarios/HOT_DAY")
        assert res_load.status_code == 200
        state = res_load.json()
        assert state["environment"]["temperature_c"] > 40.0


@pytest.mark.asyncio
async def test_api_start_stop_simulation():
    """Verify POST /api/v1/simulation/start and /stop."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res_start = await client.post("/api/v1/simulation/start")
        assert res_start.status_code == 200
        assert res_start.json() == {"status": "running"}

        res_stop = await client.post("/api/v1/simulation/stop")
        assert res_stop.status_code == 200
        assert res_stop.json() == {"status": "stopped"}


@pytest.mark.asyncio
async def test_api_invalid_scenario_returns_404():
    """Verify loading unknown scenario returns 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/simulation/scenarios/NON_EXISTENT")
    assert response.status_code == 404
