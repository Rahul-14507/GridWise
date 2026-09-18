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
