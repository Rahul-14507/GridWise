"""Tests for GridSimulator."""

from datetime import datetime, timezone
import pytest
from app.simulation.grid_simulator import GridSimulator


def test_grid_simulator_profile_interpolation():
    """Verify linear demand interpolation across the 24-hour profile without noise."""
    sim = GridSimulator(noise_percent=0.0)

    # 00:00 -> 3.0 kW
    t_midnight = datetime(2026, 9, 18, 0, 0, 0, tzinfo=timezone.utc)
    assert sim.get_building_demand_kw(t_midnight) == 3.0

    # 06:00 -> 4.5 kW
    t_morning = datetime(2026, 9, 18, 6, 0, 0, tzinfo=timezone.utc)
    assert sim.get_building_demand_kw(t_morning) == 4.5

    # 03:00 (midpoint between 00:00 and 06:00) -> 3.75 kW
    t_3am = datetime(2026, 9, 18, 3, 0, 0, tzinfo=timezone.utc)
    assert sim.get_building_demand_kw(t_3am) == 3.75


def test_grid_simulator_deterministic_noise_with_seed():
    """Verify seeded random noise produces deterministic results."""
    t = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    sim1 = GridSimulator(noise_percent=0.05, random_seed=123)
    val1 = sim1.get_building_demand_kw(t)

    sim2 = GridSimulator(noise_percent=0.05, random_seed=123)
    val2 = sim2.get_building_demand_kw(t)

    assert val1 == val2


def test_grid_simulator_override():
    """Verify explicit demand override replaces profile calculation."""
    sim = GridSimulator()
    sim.set_demand_override(18.5)
    t = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    assert sim.get_building_demand_kw(t) == 18.5

    sim.set_demand_override(None)
    assert sim.get_building_demand_kw(t) != 18.5
