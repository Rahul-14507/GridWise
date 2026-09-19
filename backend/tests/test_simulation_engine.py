"""Tests for SimulationEngine orchestration and end-to-end simulation pipeline."""

import pytest
from app.domain.models.simulation import SimulationControlInput, SimulationRunStatus
from app.domain.models.ev import EVStatus
from app.simulation.engine import SimulationEngine


def test_simulation_engine_initialization():
    """Verify SimulationEngine initializes correctly with NORMAL_DAY scenario."""
    engine = SimulationEngine(scenario_name="NORMAL_DAY")
    state = engine.get_state()

    assert state.environment.device_id == "ESP32-SIM-001"
    assert state.energy.grid.max_capacity_kw == 25.0
    assert len(state.evs) == 0
    assert state.parking.total_slots == 4
    assert engine.status == SimulationRunStatus.STOPPED


def test_simulation_engine_single_tick_advances_time():
    """Verify tick advances clock and updates SystemState."""
    engine = SimulationEngine(scenario_name="NORMAL_DAY")
    t0 = engine.clock.current_time

    state = engine.tick(interval_seconds=60.0)
    assert engine.clock.elapsed_seconds == 60.0
    assert state.timestamp > t0


def test_simulation_engine_apply_ev_allocations():
    """Verify externally supplied EV charging allocations evolve vehicle SoCs."""
    engine = SimulationEngine(scenario_name="MOCK_FLEET")
    initial_soc_ev1 = engine.ev_sim.get_ev("EV-001").soc_percent

    # Apply 7.4 kW to EV-001 for 10 ticks of 60 seconds (600s = 0.1667h)
    # Energy: 7.4 * 0.1667 = 1.233 kWh. (1.233 / 60) * 100 = 2.05% increase.
    control = SimulationControlInput(ev_allocations={"EV-001": 7.4})

    for _ in range(10):
        state = engine.tick(control_input=control, interval_seconds=60.0)

    ev1 = next(e for e in state.evs if e.id == "EV-001")
    assert ev1.soc_percent > initial_soc_ev1
    assert ev1.status == EVStatus.CHARGING
    assert state.total_ev_allocated_power_kw == 7.4
    assert state.active_charging_ev_count == 1


def test_simulation_engine_battery_command():
    """Verify externally supplied battery discharge command contributes to available EV power."""
    engine = SimulationEngine(scenario_name="NORMAL_DAY")
    initial_battery_soc = engine.battery_sim.battery.soc_percent

    # Command 5 kW battery discharge
    control = SimulationControlInput(battery_discharge_power_kw=5.0)
    state = engine.tick(control_input=control, interval_seconds=300.0)

    assert state.battery.soc_percent < initial_battery_soc
    # Available EV power should include the 5 kW battery contribution
    assert state.available_ev_charging_capacity_kw > 0.0


def test_simulation_engine_scenario_switching():
    """Verify switching scenarios updates environmental and grid state."""
    engine = SimulationEngine(scenario_name="NORMAL_DAY")
    assert engine.get_state().environment.temperature_c < 35.0

    hot_state = engine.load_scenario("HOT_DAY")
    assert engine.current_scenario_name == "HOT_DAY"
    assert hot_state.environment.temperature_c > 40.0
    assert hot_state.thermal.derating_factor < 1.0


def test_simulation_engine_determinism():
    """Verify that resetting and running the exact same ticks produces identical results."""
    engine1 = SimulationEngine(scenario_name="MOCK_FLEET")
    engine2 = SimulationEngine(scenario_name="MOCK_FLEET")

    control = SimulationControlInput(ev_allocations={"EV-001": 7.4, "EV-002": 3.7})

    for _ in range(5):
        s1 = engine1.tick(control, interval_seconds=60.0)
        s2 = engine2.tick(control, interval_seconds=60.0)

    assert s1.timestamp == s2.timestamp
    assert s1.energy.available_ev_charging_capacity_kw == s2.energy.available_ev_charging_capacity_kw
    assert s1.evs[0].soc_percent == s2.evs[0].soc_percent
