"""Unit tests for MQTT telemetry subscriber service and ESP32 payload ingestion."""

import json
from unittest.mock import MagicMock
import pytest

from app.domain.models.hardware import HardwareTelemetry
from app.infrastructure.hardware.mqtt_service import MQTTTelemetrySubscriber
from app.infrastructure.hardware.telemetry_service import HardwareTelemetryService


def test_esp32_json_payload_parsing():
    """Verify that ESP32 JSON telemetry payload parses into HardwareTelemetry."""
    payload = {
        "device_id": "ESP32-001",
        "timestamp": "2026-09-18T12:30:00Z",
        "temperature_c": 35.0,
        "rain_raw": 3200,
        "rain_status": "DRY",
        "solar_voltage_v": 2.50,
        "solar_status": "BRIGHT",
    }

    telemetry = HardwareTelemetry.model_validate(payload)

    assert telemetry.device_id == "ESP32-001"
    assert telemetry.temperature_c == 35.0
    assert telemetry.solar_voltage_v == 2.50
    assert telemetry.solar_status == "BRIGHT"
    assert telemetry.rain_raw == 3200.0
    assert telemetry.rain_status == "DRY"
    assert telemetry.rain_detected is False
    assert telemetry.humidity_percent == 50.0


def test_esp32_wet_payload_parsing():
    """Verify that ESP32 WET rain status automatically sets rain_detected to True."""
    payload = {
        "device_id": "ESP32-001",
        "timestamp": "2026-09-18T12:35:00Z",
        "temperature_c": 22.5,
        "rain_raw": 800,
        "rain_status": "WET",
        "solar_voltage_v": 0.40,
        "solar_status": "DARK",
    }

    telemetry = HardwareTelemetry.model_validate(payload)

    assert telemetry.rain_detected is True
    assert telemetry.rain_intensity == 1.0
    assert telemetry.solar_status == "DARK"


def test_mqtt_on_message_callback():
    """Verify that MQTT on_message callback successfully parses and records telemetry."""
    hw_service = HardwareTelemetryService()
    subscriber = MQTTTelemetrySubscriber(telemetry_service=hw_service)

    msg_payload = json.dumps(
        {
            "device_id": "ESP32-001",
            "timestamp": "2026-09-18T12:30:00Z",
            "temperature_c": 35.0,
            "rain_raw": 3200,
            "rain_status": "DRY",
            "solar_voltage_v": 2.50,
            "solar_status": "BRIGHT",
        }
    ).encode("utf-8")

    mock_msg = MagicMock()
    mock_msg.topic = "gridwise/telemetry"
    mock_msg.payload = msg_payload

    subscriber._on_message(client=MagicMock(), userdata=None, msg=mock_msg)

    latest = hw_service.get_latest_telemetry("ESP32-001")
    assert latest is not None
    assert latest.device_id == "ESP32-001"
    assert latest.temperature_c == 35.0
    assert latest.solar_voltage_v == 2.50
    assert latest.rain_status == "DRY"
    assert latest.solar_status == "BRIGHT"
