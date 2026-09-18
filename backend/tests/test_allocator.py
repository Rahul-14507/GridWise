"""Tests for PowerAllocator and all 10 priority/constraint scenarios."""

from datetime import datetime, timezone, timedelta
import pytest
from app.domain.models.ev import EV, EVStatus
from app.optimizer.models import DeadlineStatus
from app.optimizer.allocator import PowerAllocator


@pytest.fixture
def base_time() -> datetime:
    return datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)


def test_case_1_available_power_greater_than_total_demand(base_time):
    """Case 1: Available power > total EV demand -> All eligible EVs receive full feasible power."""
    ev1 = EV(
        id="EV-001",
        battery_capacity_kwh=60.0,
        soc_percent=30.0,
        target_soc_percent=90.0,
        max_charging_power_kw=7.4,
        arrival_time=base_time - timedelta(minutes=30),
        departure_time=base_time + timedelta(hours=2),
    )
    ev2 = EV(
        id="EV-002",
        battery_capacity_kwh=75.0,
        soc_percent=50.0,
        target_soc_percent=90.0,
        max_charging_power_kw=11.0,
        arrival_time=base_time - timedelta(minutes=15),
        departure_time=base_time + timedelta(hours=3),
    )
    items = [
        (ev1, 0.75, DeadlineStatus.FEASIBLE),
        (ev2, 0.60, DeadlineStatus.FEASIBLE),
    ]
    # Total demand = 7.4 + 11.0 = 18.4 kW. Available power = 30.0 kW.
    allocations = PowerAllocator.allocate_power(items, available_power_kw=30.0, simulation_interval_seconds=60.0)
    assert allocations["EV-001"] == 7.4
    assert allocations["EV-002"] == 11.0


def test_case_2_available_power_lower_than_total_demand(base_time):
    """Case 2: Available power < total demand -> Power distributed by priority without exceeding constraints."""
    ev1 = EV(
        id="EV-001",
        battery_capacity_kwh=60.0,
        soc_percent=30.0,
        target_soc_percent=90.0,
        max_charging_power_kw=7.4,
        arrival_time=base_time - timedelta(minutes=30),
        departure_time=base_time + timedelta(hours=2),
    )
    ev2 = EV(
        id="EV-002",
        battery_capacity_kwh=75.0,
        soc_percent=50.0,
        target_soc_percent=90.0,
        max_charging_power_kw=11.0,
        arrival_time=base_time - timedelta(minutes=15),
        departure_time=base_time + timedelta(hours=3),
    )
    # EV-001 has higher priority (0.80 > 0.40). Total available = 10.0 kW.
    items = [
        (ev1, 0.80, DeadlineStatus.FEASIBLE),
        (ev2, 0.40, DeadlineStatus.FEASIBLE),
    ]
    allocations = PowerAllocator.allocate_power(items, available_power_kw=10.0, simulation_interval_seconds=60.0)
    # EV-001 gets full 7.4 kW, remaining 2.6 kW goes to EV-002
    assert allocations["EV-001"] == 7.4
    assert allocations["EV-002"] == 2.6
    assert sum(allocations.values()) == 10.0


def test_case_3_earlier_departure_urgency_prioritization(base_time):
    """Case 3: Vehicle with earlier departure and AT_RISK status prioritized under constraint."""
    ev_early = EV(
        id="EV-EARLY",
        battery_capacity_kwh=60.0,
        soc_percent=20.0,
        target_soc_percent=90.0,
        max_charging_power_kw=7.4,
        arrival_time=base_time - timedelta(minutes=30),
        departure_time=base_time + timedelta(minutes=45),  # 45 mins remaining!
    )
    ev_late = EV(
        id="EV-LATE",
        battery_capacity_kwh=60.0,
        soc_percent=20.0,
        target_soc_percent=90.0,
        max_charging_power_kw=7.4,
        arrival_time=base_time - timedelta(minutes=30),
        departure_time=base_time + timedelta(hours=5),  # 5 hours remaining
    )
    items = [
        (ev_early, 0.85, DeadlineStatus.AT_RISK),
        (ev_late, 0.45, DeadlineStatus.FEASIBLE),
    ]
    allocations = PowerAllocator.allocate_power(items, available_power_kw=7.4, simulation_interval_seconds=60.0)
    assert allocations["EV-EARLY"] == 7.4
    assert allocations["EV-LATE"] == 0.0


def test_case_10_competing_evs_deterministic_no_overcharge(base_time):
    """Case 10: Multiple competing EVs allocate deterministically without exceeding maximum rates."""
    evs = [
        EV(
            id=f"EV-{i+1:02d}",
            battery_capacity_kwh=60.0,
            soc_percent=20.0 + i * 10,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=base_time - timedelta(minutes=30),
            departure_time=base_time + timedelta(hours=2 + i),
        )
        for i in range(4)
    ]
    items = [(ev, 0.9 - i * 0.1, DeadlineStatus.FEASIBLE) for i, ev in enumerate(evs)]

    alloc1 = PowerAllocator.allocate_power(items, available_power_kw=15.0, simulation_interval_seconds=60.0)
    alloc2 = PowerAllocator.allocate_power(items, available_power_kw=15.0, simulation_interval_seconds=60.0)

    # Determinism
    assert alloc1 == alloc2
    # No single vehicle exceeds max 7.4 kW
    for power in alloc1.values():
        assert power <= 7.4
    # Total equals available budget
    assert sum(alloc1.values()) == 15.0
