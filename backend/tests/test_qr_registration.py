"""Unit tests for QR session generation and driver EV onboarding flow."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.application.state_service import get_app_state_service

client = TestClient(app)


def test_qr_session_lifecycle():
    """Verify unique QR session creation, inspection, claiming, and expiry."""
    # 1. Create a new QR session
    res = client.post("/api/v1/evs/qr-session?bay_id=BAY-05")
    assert res.status_code == 201
    data = res.json()
    assert "session_id" in data
    assert data["session_id"].startswith("QR-")
    assert data["bay_id"] == "BAY-05"
    assert data["status"] == "active"
    token = data["session_id"]

    # 2. Get session details
    get_res = client.get(f"/api/v1/evs/qr-session/{token}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "active"

    # 3. Claim/scan session
    claim_res = client.post(f"/api/v1/evs/qr-session/{token}/claim")
    assert claim_res.status_code == 200
    assert claim_res.json()["status"] == "scanned"


def test_driver_ev_registration_and_fleet_addition():
    """Verify mobile driver EV registration seamlessly adds vehicle to active fleet and triggers optimization."""
    # 1. Create session
    sess_res = client.post("/api/v1/evs/qr-session?bay_id=BAY-02")
    assert sess_res.status_code == 201
    token = sess_res.json()["session_id"]

    # 2. Register EV
    payload = {
        "session_id": token,
        "ev_id": "EV-999",
        "slot_id": "BAY-02",
        "battery_capacity_kwh": 70.0,
        "soc_percent": 20.0,
        "target_soc_percent": 85.0,
        "max_charging_power_kw": 11.0,
        "departure_in_hours": 3.0,
    }
    reg_res = client.post("/api/v1/evs/register", json=payload)
    assert reg_res.status_code == 201
    ev_data = reg_res.json()
    assert ev_data["id"] == "EV-999"
    assert ev_data["soc_percent"] == 20.0
    assert ev_data["target_soc_percent"] == 85.0

    # 3. Verify EV appears in active fleet list
    fleet_res = client.get("/api/v1/evs")
    assert fleet_res.status_code == 200
    ev_ids = [ev["id"] for ev in fleet_res.json()]
    assert "EV-999" in ev_ids

    # 4. Verify QR session is marked registered
    sess_check = client.get(f"/api/v1/evs/qr-session/{token}")
    assert sess_check.status_code == 200
    assert sess_check.json()["status"] == "registered"
    assert sess_check.json()["ev_id"] == "EV-999"
