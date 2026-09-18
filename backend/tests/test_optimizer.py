"""Tests for ChargingOptimizer decisions and explainability reasons."""

import pytest
from app.simulation.engine import SimulationEngine
from app.optimizer.optimizer import ChargingOptimizer
from app.optimizer.models import OptimizationDecision, DeadlineStatus


def test_charging_optimizer_normal_day():
    """Verify optimizer execution on standard NORMAL_DAY scenario."""
    engine = SimulationEngine(scenario_name="NORMAL_DAY")
    state = engine.get_state()

    optimizer = ChargingOptimizer()
    decision = optimizer.optimize(state, simulation_interval_seconds=60.0)

    assert isinstance(decision, OptimizationDecision)
    assert decision.total_allocated_power_kw <= decision.available_ev_power_kw
    assert len(decision.allocations) == 4

    # Check that each allocation has explainability reason and priority metrics
    for item in decision.allocations:
        assert len(item.reason) > 0
        assert 0.0 <= item.priority_score <= 1.0
        assert 0.0 <= item.soc_urgency <= 1.0
        assert 0.0 <= item.departure_urgency <= 1.0
        assert item.deadline_status in [DeadlineStatus.FEASIBLE, DeadlineStatus.AT_RISK, DeadlineStatus.COMPLETE]


def test_charging_optimizer_hot_day_derating_warnings():
    """Verify thermal warnings are produced when optimizing under HOT_DAY."""
    engine = SimulationEngine(scenario_name="HOT_DAY")
    state = engine.get_state()

    optimizer = ChargingOptimizer()
    decision = optimizer.optimize(state, simulation_interval_seconds=60.0)

    assert any("Thermal Derating Active" in w for w in decision.warnings)
    assert decision.effective_capacity_kw < 25.0
