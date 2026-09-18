"""Closed-loop integration test connecting Optimizer and SimulationEngine."""

import pytest
from app.simulation.engine import SimulationEngine
from app.optimizer.optimizer import ChargingOptimizer
from app.domain.models.ev import EVStatus


def test_closed_loop_optimizer_simulation_progression():
    """Verify multi-step simulation evolution driven by the ChargingOptimizer decision loop."""
    engine = SimulationEngine(scenario_name="HIGH_EV_DEMAND")
    optimizer = ChargingOptimizer()

    initial_state = engine.get_state()
    initial_socs = {ev.id: ev.soc_percent for ev in initial_state.evs}

    # Run 10 closed-loop optimization ticks (60 seconds each)
    for _ in range(10):
        current_state = engine.get_state()
        decision = optimizer.optimize(current_state, simulation_interval_seconds=60.0)

        # Safety check on decision
        assert decision.total_allocated_power_kw <= decision.available_ev_power_kw + 0.001
        assert decision.infrastructure_load_kw <= decision.effective_capacity_kw + 0.001

        # Feed decision directly into simulation engine
        control_input = decision.to_control_input()
        updated_state = engine.tick(control_input=control_input, interval_seconds=60.0)

    # Verify state after 10 ticks
    final_state = engine.get_state()

    # Active EVs should have higher SoC
    for ev in final_state.evs:
        if ev.status != EVStatus.DISCONNECTED and initial_socs[ev.id] < ev.target_soc_percent:
            assert ev.soc_percent >= initial_socs[ev.id]
        assert ev.allocated_power_kw <= ev.max_charging_power_kw
        assert ev.soc_percent <= ev.target_soc_percent
