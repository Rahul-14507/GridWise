"""Tests for Hardware Telemetry domain models."""

import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from pydantic import ValidationError

from app.domain.models.hardware import HardwareTelemetry


def test_hardware_telemetry_valid():
    """Verify valid telemetry payload creates instance properly."""
    telemetry = HardwareTelemetry(
        device_id="ESP32-001",
        timestamp=datetime.now(timezone.utc),
        temperature_c=25.5,
        humidity_percent=55.0,
        rain_detected=False,
        rain_intensity=0.0,
        solar_voltage_v=2.45,
    )
    assert telemetry.device_id == "ESP32-001"
    assert telemetry.temperature_c == 25.5
    assert telemetry.humidity_percent == 55.0
    assert telemetry.rain_detected is False
    assert telemetry.solar_voltage_v == 2.45


def test_hardware_telemetry_from_fixture():
    """Verify loading from tests/fixtures/hardware.json contract."""
    fixture_path = Path(__file__).parent / "fixtures" / "hardware.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    telemetry = HardwareTelemetry.model_validate(data)
    assert telemetry.device_id == "ESP32-001"
    assert telemetry.temperature_c == 31.4
    assert telemetry.humidity_percent == 62.1
    assert telemetry.rain_detected is False
    assert telemetry.solar_voltage_v == 2.14
    assert telemetry.timestamp.tzinfo is not None


@pytest.mark.parametrize("humidity", [-1.0, 100.1, -50.0, 150.0])
def test_hardware_telemetry_invalid_humidity(humidity):
    """Verify out-of-range humidity is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        HardwareTelemetry(
            device_id="ESP32-001",
            timestamp=datetime.now(timezone.utc),
            temperature_c=25.0,
            humidity_percent=humidity,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=1.5,
        )
    assert "humidity_percent" in str(exc_info.value)


def test_hardware_telemetry_negative_solar_voltage():
    """Verify negative solar panel voltage is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        HardwareTelemetry(
            device_id="ESP32-001",
            timestamp=datetime.now(timezone.utc),
            temperature_c=25.0,
            humidity_percent=50.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=-0.1,
        )
    assert "solar_voltage_v" in str(exc_info.value)


def test_hardware_telemetry_negative_rain_intensity():
    """Verify negative rain intensity is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        HardwareTelemetry(
            device_id="ESP32-001",
            timestamp=datetime.now(timezone.utc),
            temperature_c=25.0,
            humidity_percent=50.0,
            rain_detected=False,
            rain_intensity=-1.0,
            solar_voltage_v=1.0,
        )
    assert "rain_intensity" in str(exc_info.value)


@pytest.mark.parametrize("empty_id", ["", "   ", "\t\n"])
def test_hardware_telemetry_empty_device_id(empty_id):
    """Verify empty or whitespace-only device ID is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        HardwareTelemetry(
            device_id=empty_id,
            timestamp=datetime.now(timezone.utc),
            temperature_c=25.0,
            humidity_percent=50.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=1.0,
        )
    assert "device_id" in str(exc_info.value)


def test_hardware_telemetry_naive_timestamp_rejected():
    """Verify naive timestamp without timezone is strictly rejected."""
    naive_dt = datetime(2026, 9, 18, 10, 30, 0)
    with pytest.raises(ValidationError) as exc_info:
        HardwareTelemetry(
            device_id="ESP32-001",
            timestamp=naive_dt,
            temperature_c=25.0,
            humidity_percent=50.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=1.0,
        )
    assert "timezone-aware" in str(exc_info.value)


@pytest.mark.parametrize("temp", [-55.0, 95.0])
def test_hardware_telemetry_extreme_temperature(temp):
    """Verify unreasonable ambient temperatures are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        HardwareTelemetry(
            device_id="ESP32-001",
            timestamp=datetime.now(timezone.utc),
            temperature_c=temp,
            humidity_percent=50.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=1.0,
        )
    assert "temperature_c" in str(exc_info.value)
