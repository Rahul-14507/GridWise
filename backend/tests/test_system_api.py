"""FastAPI integration tests for System API endpoints."""

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


def test_get_system_state():
    response = client.get("/api/v1/system/state")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "environment" in data
    assert "energy" in data
    assert "thermal" in data
    assert "battery" in data
    assert "evs" in data
    assert "parking" in data
    assert len(data["evs"]) == 4


def test_get_system_summary():
    response = client.get("/api/v1/system/summary")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "system_status" in data
    assert data["system_status"] in ["operational", "warning", "degraded", "no_data"]
    assert "energy" in data
    assert data["energy"]["grid_capacity_kw"] == 25.0
    assert "battery" in data
    assert "evs" in data
    assert data["evs"]["total"] == 4
    assert "parking" in data
    assert "hardware" in data
    assert "warnings" in data


def test_get_system_status():
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "data_source" in data
    assert "simulation_running" in data
    assert "hardware_devices_online" in data
    assert "warnings" in data
    assert isinstance(data["warnings"], list)


def test_system_warnings_under_thermal_stress():
    engine = get_simulation_engine()
    engine.load_scenario("HOT_DAY")

    response = client.get("/api/v1/system/summary")
    assert response.status_code == 200
    data = response.json()
    warning_codes = [w["code"] for w in data["warnings"]]
    assert "THERMAL_DERATING_ACTIVE" in warning_codes


def test_get_network_info():
    response = client.get("/api/v1/system/network-info")
    assert response.status_code == 200
    data = response.json()
    assert "host_ip" in data
    assert "frontend_port" in data
    assert "backend_port" in data
    assert "driver_base_url" in data
    assert data["frontend_port"] == 3000
    assert data["backend_port"] == 8000
    assert data["driver_base_url"].startswith("http://")

