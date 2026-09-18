"""Tests for ConstraintValidator independent safety checks."""

import pytest
from app.domain.models.system import SystemState
from app.domain.models.ev import EVStatus
from app.simulation.engine import SimulationEngine
from app.optimizer.constraints import ConstraintValidator, ConstraintViolationError


@pytest.fixture
def base_state() -> SystemState:
    engine = SimulationEngine(scenario_name="NORMAL_DAY")
    return engine.get_state()


def test_constraint_validator_valid_allocations(base_state):
    """Verify valid allocations pass constraint validation."""
    allocations = {"EV-001": 7.4, "EV-002": 5.5, "EV-003": 0.0, "EV-004": 3.7}
    ConstraintValidator.validate_allocations(
        system_state=base_state,
        ev_allocations=allocations,
        battery_discharge_kw=0.0,
        battery_charge_kw=0.0,
        simulation_interval_seconds=60.0,
    )


def test_constraint_validator_exceeding_available_power(base_state):
    """Verify exceeding total available EV charging capacity raises ConstraintViolationError."""
    # Available power is ~24.33 kW. Request 40 kW.
    allocations = {"EV-001": 20.0, "EV-002": 20.0}
    with pytest.raises(ConstraintViolationError) as exc_info:
        ConstraintValidator.validate_allocations(
            system_state=base_state,
            ev_allocations=allocations,
            battery_discharge_kw=0.0,
            battery_charge_kw=0.0,
            simulation_interval_seconds=60.0,
        )
    assert "exceeds available charging capacity" in str(exc_info.value)


def test_constraint_validator_exceeding_charger_limit(base_state):
    """Verify power allocation exceeding EV max_charging_power_kw is rejected."""
    # EV-001 max is 7.4 kW. Try allocating 11.0 kW.
    allocations = {"EV-001": 11.0, "EV-002": 0.0, "EV-003": 0.0, "EV-004": 0.0}
    with pytest.raises(ConstraintViolationError) as exc_info:
        ConstraintValidator.validate_allocations(
            system_state=base_state,
            ev_allocations=allocations,
            battery_discharge_kw=0.0,
            battery_charge_kw=0.0,
            simulation_interval_seconds=60.0,
        )
    assert "Charger hardware limit exceeded" in str(exc_info.value)


def test_constraint_validator_negative_power_rejected(base_state):
    """Verify negative allocation is rejected."""
    allocations = {"EV-001": -2.0}
    with pytest.raises(ConstraintViolationError) as exc_info:
        ConstraintValidator.validate_allocations(
            system_state=base_state,
            ev_allocations=allocations,
            battery_discharge_kw=0.0,
            battery_charge_kw=0.0,
            simulation_interval_seconds=60.0,
        )
    assert "Non-negativity violation" in str(exc_info.value)
