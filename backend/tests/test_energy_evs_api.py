"""FastAPI integration tests for Energy and EVs endpoints."""

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.application.state_service import get_app_state_service
from app.simulation.engine import get_simulation_engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    engine = get_simulation_engine()
    engine.load_scenario("NORMAL_DAY")
    service = get_app_state_service()
    service.reset_decision()
    yield
    service.reset_decision()


def test_get_energy_endpoint():
    response = client.get("/api/v1/energy")
    assert response.status_code == 200
    data = response.json()
    assert data["base_grid_capacity_kw"] == 25.0
    assert data["effective_grid_capacity_kw"] >= 0.0
    assert data["building_demand_kw"] >= 0.0
    assert data["solar_voltage_v"] >= 0.0
    assert "solar_availability_percent" in data
    assert "estimated_solar_generation_kw" in data
    assert "available_ev_charging_power_kw" in data
    assert "infrastructure_load_kw" in data


def test_get_evs_endpoint():
    response = client.get("/api/v1/evs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 4

    ev1 = data[0]
    assert ev1["id"] == "EV-001"
    assert "battery_capacity_kwh" in ev1
    assert "soc_percent" in ev1
    assert "target_soc_percent" in ev1
    assert "energy_required_kwh" in ev1
    assert "remaining_time_minutes" in ev1
    assert "required_average_power_kw" in ev1


def test_get_single_ev_success():
    response = client.get("/api/v1/evs/EV-001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "EV-001"
    assert data["battery_capacity_kwh"] == 60.0
    assert data["soc_percent"] == 22.0


def test_get_single_ev_not_found():
    response = client.get("/api/v1/evs/EV-NONEXISTENT")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_evs_reflect_optimizer_metadata_after_run():
    # Before optimizer run
    res_before = client.get("/api/v1/evs/EV-001")
    assert res_before.json()["priority_score"] is None

    # Run optimizer
    res_opt = client.post("/api/v1/optimization/run")
    assert res_opt.status_code == 200

    # After optimizer run
    res_after = client.get("/api/v1/evs/EV-001")
    assert res_after.json()["priority_score"] is not None
    assert res_after.json()["deadline_status"] is not None
    assert res_after.json()["reason"] is not None
