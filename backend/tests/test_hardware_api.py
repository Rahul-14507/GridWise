"""FastAPI integration tests for Hardware Telemetry endpoints."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.hardware.telemetry_service import get_hardware_telemetry_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_service():
    service = get_hardware_telemetry_service()
    service.clear()
    yield
    service.clear()


def test_post_telemetry_success():
    payload = {
        "device_id": "ESP32-001",
        "timestamp": "2026-09-18T10:30:00Z",
        "temperature_c": 31.4,
        "humidity_percent": 62.1,
        "rain_detected": False,
        "rain_intensity": 0.0,
        "solar_voltage_v": 2.14,
    }
    response = client.post("/api/v1/hardware/telemetry", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert data["device_id"] == "ESP32-001"
    assert "recorded_at" in data


def test_post_telemetry_validation_errors():
    # Missing required field
    response = client.post(
        "/api/v1/hardware/telemetry",
        json={"device_id": "ESP32-001", "temperature_c": 25.0},
    )
    assert response.status_code == 422

    # Invalid humidity (> 100)
    response = client.post(
        "/api/v1/hardware/telemetry",
        json={
            "device_id": "ESP32-001",
            "timestamp": "2026-09-18T10:30:00Z",
            "temperature_c": 25.0,
            "humidity_percent": 110.0,
            "rain_detected": False,
            "rain_intensity": 0.0,
            "solar_voltage_v": 1.5,
        },
    )
    assert response.status_code == 422


def test_get_latest_telemetry():
    # 404 when no telemetry received
    response = client.get("/api/v1/hardware/telemetry/latest")
    assert response.status_code == 404

    # Post telemetry
    payload = {
        "device_id": "ESP32-001",
        "timestamp": "2026-09-18T10:30:00Z",
        "temperature_c": 28.5,
        "humidity_percent": 50.0,
        "rain_detected": False,
        "rain_intensity": 0.0,
        "solar_voltage_v": 2.0,
    }
    client.post("/api/v1/hardware/telemetry", json=payload)

    # Global latest
    response = client.get("/api/v1/hardware/telemetry/latest")
    assert response.status_code == 200
    assert response.json()["device_id"] == "ESP32-001"
    assert response.json()["temperature_c"] == 28.5

    # Filter by device_id
    response = client.get("/api/v1/hardware/telemetry/latest?device_id=ESP32-001")
    assert response.status_code == 200

    # Filter by non-existent device_id
    response = client.get("/api/v1/hardware/telemetry/latest?device_id=ESP32-NONEXISTENT")
    assert response.status_code == 404


def test_get_hardware_status():
    # Status when empty
    response = client.get("/api/v1/hardware/status")
    assert response.status_code == 200
    assert response.json()["status"] == "no_data"

    # Post telemetry
    payload = {
        "device_id": "ESP32-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_c": 25.0,
        "humidity_percent": 45.0,
        "rain_detected": False,
        "rain_intensity": 0.0,
        "solar_voltage_v": 1.8,
    }
    client.post("/api/v1/hardware/telemetry", json=payload)

    response = client.get("/api/v1/hardware/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["total_devices"] == 1
    assert data["active_devices"] == 1
    assert "ESP32-001" in data["devices"]


def test_get_individual_device_status():
    payload = {
        "device_id": "ESP32-UNIT-A",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_c": 22.0,
        "humidity_percent": 40.0,
        "rain_detected": False,
        "rain_intensity": 0.0,
        "solar_voltage_v": 1.2,
    }
    client.post("/api/v1/hardware/telemetry", json=payload)

    response = client.get("/api/v1/hardware/devices/ESP32-UNIT-A/status")
    assert response.status_code == 200
    assert response.json()["device_id"] == "ESP32-UNIT-A"
    assert response.json()["is_connected"] is True

    # Unknown device
    response = client.get("/api/v1/hardware/devices/UNKNOWN/status")
    assert response.status_code == 404
