"""Integration test for full simulation engine progression and physical consistency."""

import pytest
from app.domain.models.simulation import SimulationControlInput
from app.domain.models.ev import EVStatus
from app.simulation.engine import SimulationEngine


def test_simulation_multi_tick_integration():
    """Verify multi-tick simulation execution respecting energy balance and EV SoC progression."""
    engine = SimulationEngine(scenario_name="NORMAL_DAY")
    initial_state = engine.get_state()

    # Verify initial conditions
    assert initial_state.energy.grid.max_capacity_kw == 25.0
    assert len(initial_state.evs) == 4

    ev1_start_soc = engine.ev_sim.get_ev("EV-001").soc_percent
    ev2_start_soc = engine.ev_sim.get_ev("EV-002").soc_percent
    ev4_start_soc = engine.ev_sim.get_ev("EV-004").soc_percent
    initial_battery_soc = initial_state.battery.soc_percent

    # External allocations supplied by test (not decided by optimizer)
    allocations = {
        "EV-001": 7.0,
        "EV-002": 4.0,
        "EV-003": 0.0,
        "EV-004": 2.0,
    }
    control = SimulationControlInput(
        ev_allocations=allocations,
        battery_charge_power_kw=0.0,
        battery_discharge_power_kw=0.0,
    )

    # Run 10 ticks of 60 seconds (600 seconds total = 10 minutes = 0.1667 hours)
    for _ in range(10):
        state = engine.tick(control_input=control, interval_seconds=60.0)

    # 1. SystemState validity
    assert state.timestamp > initial_state.timestamp
    assert state.energy.available_ev_charging_capacity_kw >= 0.0

    # 2. EV SoCs increased for allocated vehicles
    ev1 = engine.ev_sim.get_ev("EV-001")
    ev2 = engine.ev_sim.get_ev("EV-002")
    ev3 = engine.ev_sim.get_ev("EV-003")
    ev4 = engine.ev_sim.get_ev("EV-004")

    assert ev1.soc_percent > ev1_start_soc
    assert ev2.soc_percent > ev2_start_soc
    assert ev4.soc_percent > ev4_start_soc
    # EV-003 was allocated 0 kW, so its SoC must not have changed
    assert ev3.soc_percent == 34.0
    assert ev3.status in [EVStatus.WAITING, EVStatus.PAUSED]

    # 3. No EV exceeds its maximum charging power
    for ev in state.evs:
        assert ev.allocated_power_kw <= ev.max_charging_power_kw
        assert ev.soc_percent <= ev.target_soc_percent

    # 4. Battery remained unchanged since no battery command was given
    assert state.battery.soc_percent == initial_battery_soc

    # 5. Parking slot synchronization
    assert state.occupied_parking_slots == 4
    assert state.active_charging_ev_count == 3
