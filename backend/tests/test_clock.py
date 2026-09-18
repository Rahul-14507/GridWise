"""Tests for SimulationClock."""

from datetime import datetime, timezone, timedelta
import pytest
from app.simulation.clock import SimulationClock


def test_simulation_clock_initialization_default():
    """Verify default initial time starts in UTC."""
    clock = SimulationClock()
    assert clock.current_time.tzinfo is not None
    assert clock.elapsed_seconds == 0.0


def test_simulation_clock_initialization_custom():
    """Verify custom initial timestamp is respected."""
    t0 = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    clock = SimulationClock(initial_time=t0)
    assert clock.current_time == t0
    assert clock.elapsed_seconds == 0.0


def test_simulation_clock_advance():
    """Verify clock advances by exact duration in seconds."""
    t0 = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)
    clock = SimulationClock(initial_time=t0)

    t1 = clock.advance(60.0)
    assert t1 == t0 + timedelta(seconds=60)
    assert clock.elapsed_seconds == 60.0

    t2 = clock.advance(120.0)
    assert t2 == t0 + timedelta(seconds=180)
    assert clock.elapsed_seconds == 180.0


def test_simulation_clock_reset():
    """Verify clock reset returns to initial starting time."""
    t0 = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)
    clock = SimulationClock(initial_time=t0)
    clock.advance(500.0)
    assert clock.elapsed_seconds == 500.0

    reset_time = clock.reset()
    assert reset_time == t0
    assert clock.elapsed_seconds == 0.0


def test_simulation_clock_naive_datetime_rejected():
    """Verify non-timezone-aware datetimes raise ValueError."""
    naive_t = datetime(2026, 9, 18, 10, 0, 0)
    with pytest.raises(ValueError):
        SimulationClock(initial_time=naive_t)


def test_simulation_clock_negative_advance_rejected():
    """Verify advancing by negative duration raises ValueError."""
    clock = SimulationClock()
    with pytest.raises(ValueError):
        clock.advance(-10.0)
