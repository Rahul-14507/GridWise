"""FastAPI integration tests for Optimization API endpoints."""

from fastapi.testclient import TestClient
import pytest

from app.config.settings import get_settings
from app.main import app
from app.application.state_service import get_app_state_service
from app.simulation.engine import get_simulation_engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    engine = get_simulation_engine()
    engine.load_scenario("MOCK_FLEET")
    service = get_app_state_service()
    service.reset_decision()
    yield
    service.reset_decision()


def test_get_current_optimization_when_none():
    response = client.get("/api/v1/optimization/current")
    assert response.status_code == 404
    assert "No optimization decision" in response.json()["detail"]


def test_run_optimization_endpoint():
    response = client.post("/api/v1/optimization/run")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "available_ev_power_kw" in data
    assert "total_allocated_power_kw" in data
    assert "allocations" in data
    assert len(data["allocations"]) == 4

    # Check GET /optimization/current now returns the computed decision
    get_res = client.get("/api/v1/optimization/current")
    assert get_res.status_code == 200
    assert get_res.json()["total_allocated_power_kw"] == data["total_allocated_power_kw"]


def test_apply_optimization_decision_without_running_first():
    response = client.post("/api/v1/optimization/apply")
    assert response.status_code == 400
    assert "No optimization decision" in response.json()["detail"]


def test_run_and_apply_optimization_decision():
    # Run optimizer
    client.post("/api/v1/optimization/run")

    # Apply decision
    apply_res = client.post("/api/v1/optimization/apply")
    assert apply_res.status_code == 200
    data = apply_res.json()
    assert data["status"] == "applied"
    assert data["ev_allocations_count"] == 4
    assert data["total_allocated_kw"] > 0


def test_apply_optimization_rejected_in_hardware_mode(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "telemetry_data_source", "hardware")

    # Run optimizer
    client.post("/api/v1/optimization/run")

    # Apply decision in hardware mode -> must return 409 Conflict
    apply_res = client.post("/api/v1/optimization/apply")
    assert apply_res.status_code == 409
    assert "hardware mode" in apply_res.json()["detail"]
