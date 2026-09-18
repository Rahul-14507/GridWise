"""Tests for UrgencyCalculator domain calculations."""

import pytest
from app.optimizer.urgency import UrgencyCalculator


def test_soc_urgency_calculation():
    """Verify lower SoC produces higher SoC urgency."""
    # 20% SoC with 80% target: 1 - (20/80) = 0.75
    urgency_low = UrgencyCalculator.calculate_soc_urgency(20.0, 80.0)
    assert urgency_low == 0.75

    # 60% SoC with 80% target: 1 - (60/80) = 0.25
    urgency_high = UrgencyCalculator.calculate_soc_urgency(60.0, 80.0)
    assert urgency_high == 0.25

    # Already at or above target SoC -> 0.0
    assert UrgencyCalculator.calculate_soc_urgency(80.0, 80.0) == 0.0
    assert UrgencyCalculator.calculate_soc_urgency(85.0, 80.0) == 0.0


def test_soc_urgency_zero_target():
    """Verify zero target SoC safely returns 0.0 without division-by-zero."""
    assert UrgencyCalculator.calculate_soc_urgency(0.0, 0.0) == 0.0


def test_energy_deficit_score():
    """Verify energy deficit fraction computation."""
    # 30 kWh required for 60 kWh battery -> 0.50
    assert UrgencyCalculator.calculate_energy_deficit_score(30.0, 60.0) == 0.5
    # 0 kWh required -> 0.0
    assert UrgencyCalculator.calculate_energy_deficit_score(0.0, 60.0) == 0.0


def test_departure_urgency_monotonic_curve():
    """Verify departure urgency increases monotonically as departure approaches."""
    u_expired = UrgencyCalculator.calculate_departure_urgency(0.0)
    u_30m = UrgencyCalculator.calculate_departure_urgency(0.5)
    u_1h = UrgencyCalculator.calculate_departure_urgency(1.0)
    u_2h = UrgencyCalculator.calculate_departure_urgency(2.0)
    u_4h = UrgencyCalculator.calculate_departure_urgency(4.0)
    u_8h = UrgencyCalculator.calculate_departure_urgency(8.0)

    assert u_expired == 1.0
    assert u_30m > u_1h
    assert u_1h >= 0.8
    assert u_1h > u_2h
    assert u_2h > u_4h
    assert u_4h > u_8h
    assert 0.0 <= u_8h <= 0.1


def test_waiting_score():
    """Verify waiting score increases with wait duration up to reference cap."""
    # 0 mins -> 0.0
    assert UrgencyCalculator.calculate_waiting_score(0.0, reference_minutes=60.0) == 0.0
    # 30 mins / 60 mins -> 0.50
    assert UrgencyCalculator.calculate_waiting_score(30.0, reference_minutes=60.0) == 0.5
    # 60 mins -> 1.0
    assert UrgencyCalculator.calculate_waiting_score(60.0, reference_minutes=60.0) == 1.0
    # 120 mins -> clamped to 1.0
    assert UrgencyCalculator.calculate_waiting_score(120.0, reference_minutes=60.0) == 1.0
