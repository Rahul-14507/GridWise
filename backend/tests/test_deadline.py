"""Tests for DeadlineAnalyzer feasibility analysis."""

import pytest
from app.optimizer.models import DeadlineStatus
from app.optimizer.deadline import DeadlineAnalyzer


def test_deadline_analyzer_feasible():
    """Verify comfortable deadline feasibility (required avg power <= max power)."""
    # Needs 10 kWh in 2 hours -> required 5.0 kW <= max 7.4 kW -> FEASIBLE
    status, req_power = DeadlineAnalyzer.analyze_deadline(
        energy_required_kwh=10.0,
        remaining_time_hours=2.0,
        max_charging_power_kw=7.4,
    )
    assert status == DeadlineStatus.FEASIBLE
    assert req_power == 5.0


def test_deadline_analyzer_at_risk():
    """Verify deadline risk when required avg power > max charging power."""
    # Needs 20 kWh in 1 hour -> required 20.0 kW > max 7.4 kW -> AT_RISK
    status, req_power = DeadlineAnalyzer.analyze_deadline(
        energy_required_kwh=20.0,
        remaining_time_hours=1.0,
        max_charging_power_kw=7.4,
    )
    assert status == DeadlineStatus.AT_RISK
    assert req_power == 20.0


def test_deadline_analyzer_complete():
    """Verify target already reached yields COMPLETE status."""
    status, req_power = DeadlineAnalyzer.analyze_deadline(
        energy_required_kwh=0.0,
        remaining_time_hours=2.0,
        max_charging_power_kw=7.4,
    )
    assert status == DeadlineStatus.COMPLETE
    assert req_power == 0.0


def test_deadline_analyzer_expired():
    """Verify departure time passed with positive deficit yields EXPIRED status."""
    status, req_power = DeadlineAnalyzer.analyze_deadline(
        energy_required_kwh=15.0,
        remaining_time_hours=0.0,
        max_charging_power_kw=7.4,
    )
    assert status == DeadlineStatus.EXPIRED
    assert req_power == 0.0
