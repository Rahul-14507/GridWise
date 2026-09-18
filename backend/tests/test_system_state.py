"""Tests for SystemState domain model serialization and derived properties."""

import json
from datetime import datetime, timezone
from app.simulation.engine import SimulationEngine
from app.domain.models.system import SystemState


def test_system_state_serialization_roundtrip():
    """Verify that SystemState can be serialized to JSON and deserialized cleanly."""
    engine = SimulationEngine(scenario_name="NORMAL_DAY")
    state = engine.get_state()

    json_str = state.model_dump_json()
    assert isinstance(json_str, str)
    data = json.loads(json_str)

    restored = SystemState.model_validate(data)
    assert restored.timestamp == state.timestamp
    assert restored.environment.temperature_c == state.environment.temperature_c
    assert restored.energy.grid.max_capacity_kw == state.energy.grid.max_capacity_kw
    assert len(restored.evs) == len(state.evs)


def test_system_state_derived_properties():
    """Verify helper properties on SystemState compute expected aggregates."""
    engine = SimulationEngine(scenario_name="NORMAL_DAY")
    state = engine.get_state()

    assert state.available_ev_charging_capacity_kw == state.energy.available_ev_charging_capacity_kw
    assert state.available_parking_slots == state.parking.available_slots
    assert state.occupied_parking_slots == state.parking.occupied_slots
    assert state.total_ev_allocated_power_kw == 0.0
    assert state.active_charging_ev_count == 0


def test_thermal_overload_alert_warning_at_50c():
    """Verify that ambient temperature >= 50°C triggers critical THERMAL_OVERLOAD_ALERT."""
    from app.application.warnings import WarningService
    from app.domain.models.hardware import HardwareTelemetry
    from app.domain.services.system_state_service import SystemStateService

    engine = SimulationEngine(scenario_name="NORMAL_DAY")
    base_state = engine.get_state()

    # Create telemetry with temperature >= 50.0°C
    overload_telemetry = HardwareTelemetry(
        device_id="ESP32-001",
        timestamp=datetime.now(timezone.utc),
        temperature_c=52.5,
        humidity_percent=40.0,
        rain_detected=False,
        rain_intensity=0.0,
        solar_voltage_v=2.8,
    )

    overload_state = SystemStateService.build_system_state(
        timestamp=datetime.now(timezone.utc),
        environment=overload_telemetry,
        base_grid_capacity_kw=25.0,
        solar_min_voltage_v=0.0,
        solar_max_voltage_v=3.0,
        solar_capacity_kw=10.0,
        thermal_derating_start_c=35.0,
        thermal_critical_temp_c=50.0,
        thermal_min_capacity_kw=10.0,
        building_demand_kw=5.0,
        battery=base_state.battery,
        evs=base_state.evs,
        parking=base_state.parking,
    )

    warnings = WarningService.evaluate_warnings(overload_state)
    codes = [w.code for w in warnings]
    assert "THERMAL_OVERLOAD_ALERT" in codes
    overload_warning = next(w for w in warnings if w.code == "THERMAL_OVERLOAD_ALERT")
    assert overload_warning.severity == "critical"
    assert "50°C" in overload_warning.message
    assert "52.5°C" in overload_warning.message
