"""Tests for SensorSimulator."""

from datetime import datetime, timezone
import pytest
from app.simulation.sensor_simulator import SensorSimulator
from app.domain.models.hardware import HardwareTelemetry


def test_sensor_simulator_generates_valid_telemetry():
    """Verify output from SensorSimulator validates as valid HardwareTelemetry."""
    sim = SensorSimulator(device_id="ESP32-SIM-001")
    t = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    telemetry = sim.generate_telemetry(t)

    assert isinstance(telemetry, HardwareTelemetry)
    assert telemetry.device_id == "ESP32-SIM-001"
    assert telemetry.timestamp == t
    assert -50.0 <= telemetry.temperature_c <= 80.0
    assert 0.0 <= telemetry.humidity_percent <= 100.0
    assert telemetry.solar_voltage_v >= 0.0


def test_sensor_simulator_night_zero_solar_voltage():
    """Verify nighttime hours (e.g. 02:00) produce 0.0V solar voltage."""
    sim = SensorSimulator()
    t_night = datetime(2026, 9, 18, 2, 0, 0, tzinfo=timezone.utc)
    telemetry = sim.generate_telemetry(t_night)
    assert telemetry.solar_voltage_v == 0.0


def test_sensor_simulator_midday_solar_voltage_peaks():
    """Verify solar voltage peaks around solar noon (12:00-14:00)."""
    sim = SensorSimulator(max_solar_voltage_v=2.85)
    t_noon = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    telemetry = sim.generate_telemetry(t_noon)
    assert telemetry.solar_voltage_v > 2.0


def test_sensor_simulator_scenario_overrides():
    """Verify scenario overrides replace simulated values."""
    sim = SensorSimulator()
    sim.set_overrides(
        temperature_c=45.0,
        humidity_percent=20.0,
        rain_detected=True,
        rain_intensity=15.0,
        solar_voltage_v=1.25,
    )
    t = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)
    telemetry = sim.generate_telemetry(t)

    assert telemetry.temperature_c == 45.0
    assert telemetry.humidity_percent == 20.0
    assert telemetry.rain_detected is True
    assert telemetry.rain_intensity == 15.0
    assert telemetry.solar_voltage_v == 1.25

    # Clear overrides restores dynamic calculation
    sim.clear_overrides()
    telemetry_restored = sim.generate_telemetry(t)
    assert telemetry_restored.rain_detected is False
