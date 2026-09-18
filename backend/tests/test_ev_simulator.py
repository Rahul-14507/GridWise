"""Tests for EVSimulator and EV domain helper methods."""

from datetime import datetime, timezone, timedelta
import pytest
from app.domain.models.ev import EV, EVStatus
from app.simulation.ev_simulator import EVSimulator


@pytest.fixture
def sample_evs() -> list[EV]:
    now = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)
    return [
        EV(
            id="EV-001",
            slot_id="SLOT-01",
            battery_capacity_kwh=60.0,
            soc_percent=30.0,
            target_soc_percent=80.0,
            max_charging_power_kw=7.4,
            arrival_time=now - timedelta(minutes=30),
            departure_time=now + timedelta(hours=2),
            allocated_power_kw=0.0,
            status=EVStatus.WAITING,
        ),
        EV(
            id="EV-002",
            slot_id="SLOT-02",
            battery_capacity_kwh=75.0,
            soc_percent=80.0,
            target_soc_percent=80.0,
            max_charging_power_kw=11.0,
            arrival_time=now - timedelta(minutes=15),
            departure_time=now + timedelta(hours=3),
            allocated_power_kw=0.0,
            status=EVStatus.COMPLETED,
        ),
    ]


def test_ev_domain_helpers(sample_evs):
    """Verify energy_required_kwh, remaining_time_hours, and required_average_power_kw."""
    ev1 = sample_evs[0]
    now = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)

    # 60 kWh * (80% - 30%) = 30.0 kWh required
    assert ev1.energy_required_kwh == 30.0

    # Remaining time: 2 hours
    assert ev1.remaining_time_hours(now) == 2.0

    # Required average power: 30 kWh / 2h = 15.0 kW
    assert ev1.required_average_power_kw(now) == 15.0

    # Completed EV requires 0 kWh and 0 kW power
    ev2 = sample_evs[1]
    assert ev2.energy_required_kwh == 0.0
    assert ev2.required_average_power_kw(now) == 0.0


def test_ev_simulator_charging_step(sample_evs):
    """Verify stepping simulation with power allocation increases vehicle SoC."""
    sim = EVSimulator(sample_evs)
    current_time = datetime(2026, 9, 18, 10, 1, 0, tzinfo=timezone.utc)

    # Charge EV-001 at 7.4 kW for 1 hour (3600s)
    # Energy delivered = 7.4 kWh. Delta SoC = (7.4 / 60) * 100 = 12.3333%.
    # Initial 30% -> New SoC: 42.3333%
    updated = sim.step(
        current_time=current_time,
        duration_seconds=3600.0,
        allocations={"EV-001": 7.4},
    )

    ev1 = next(e for e in updated if e.id == "EV-001")
    assert ev1.status == EVStatus.CHARGING
    assert ev1.allocated_power_kw == 7.4
    assert round(ev1.soc_percent, 1) == 42.3


def test_ev_simulator_target_soc_cap(sample_evs):
    """Verify vehicle caps at target SoC and transitions to COMPLETED."""
    sim = EVSimulator(sample_evs)
    current_time = datetime(2026, 9, 18, 10, 5, 0, tzinfo=timezone.utc)

    # EV-001 needs 30 kWh (starts at 30%, target 80%).
    # Deliver 7.4 kW for 10 hours (74 kWh potential) -> caps at 80% and COMPLETED.
    updated = sim.step(
        current_time=current_time,
        duration_seconds=36000.0,
        allocations={"EV-001": 7.4},
    )

    ev1 = next(e for e in updated if e.id == "EV-001")
    assert ev1.soc_percent == 80.0
    assert ev1.status == EVStatus.COMPLETED
    assert ev1.allocated_power_kw == 0.0


def test_ev_simulator_zero_allocation_pauses(sample_evs):
    """Verify allocating 0 kW to an active vehicle sets status to PAUSED."""
    sim = EVSimulator(sample_evs)
    t1 = datetime(2026, 9, 18, 10, 1, 0, tzinfo=timezone.utc)
    sim.step(t1, 60.0, {"EV-001": 7.4})

    t2 = datetime(2026, 9, 18, 10, 2, 0, tzinfo=timezone.utc)
    updated = sim.step(t2, 60.0, {"EV-001": 0.0})

    ev1 = next(e for e in updated if e.id == "EV-001")
    assert ev1.status == EVStatus.PAUSED
    assert ev1.allocated_power_kw == 0.0


def test_ev_simulator_departure_disconnects(sample_evs):
    """Verify vehicle departure transitions status to DISCONNECTED."""
    sim = EVSimulator(sample_evs)
    # Departure was 12:00. Step to 12:05
    t_depart = datetime(2026, 9, 18, 12, 5, 0, tzinfo=timezone.utc)
    updated = sim.step(t_depart, 60.0, {})

    ev1 = next(e for e in updated if e.id == "EV-001")
    assert ev1.status == EVStatus.DISCONNECTED


def test_ev_simulator_exceeding_max_power_raises(sample_evs):
    """Verify requesting more power than max_charging_power_kw raises ValueError."""
    sim = EVSimulator(sample_evs)
    t = datetime(2026, 9, 18, 10, 1, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError) as exc_info:
        sim.step(t, 60.0, {"EV-001": 22.0})
    assert "exceeds maximum charging power" in str(exc_info.value)
