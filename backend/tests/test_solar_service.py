"""Tests for SolarService domain calculations."""

import pytest
from app.domain.services.solar_service import SolarService


def test_solar_service_normal_calculation():
    """Verify standard midpoint voltage availability and generation calculation."""
    # min=0.0V, max=3.0V, capacity=10.0 kW, measured=2.1V -> availability=0.70, generation=7.0 kW
    state = SolarService.calculate_solar_state(
        solar_voltage_v=2.1,
        min_voltage_v=0.0,
        max_voltage_v=3.0,
        solar_capacity_kw=10.0,
    )
    assert state.solar_voltage_v == 2.1
    assert state.availability_percent == 70.0
    assert state.estimated_generation_kw == 7.0


def test_solar_service_minimum_voltage():
    """Verify zero voltage corresponds to 0% availability and 0 kW generation."""
    state = SolarService.calculate_solar_state(
        solar_voltage_v=0.0,
        min_voltage_v=0.0,
        max_voltage_v=3.0,
        solar_capacity_kw=10.0,
    )
    assert state.availability_percent == 0.0
    assert state.estimated_generation_kw == 0.0


def test_solar_service_maximum_voltage():
    """Verify maximum voltage corresponds to 100% availability and full capacity generation."""
    state = SolarService.calculate_solar_state(
        solar_voltage_v=3.0,
        min_voltage_v=0.0,
        max_voltage_v=3.0,
        solar_capacity_kw=10.0,
    )
    assert state.availability_percent == 100.0
    assert state.estimated_generation_kw == 10.0


def test_solar_service_below_minimum_clamping():
    """Verify voltage below calibrated minimum clamps availability to 0.0%."""
    state = SolarService.calculate_solar_state(
        solar_voltage_v=0.2,
        min_voltage_v=0.5,
        max_voltage_v=3.0,
        solar_capacity_kw=10.0,
    )
    assert state.availability_percent == 0.0
    assert state.estimated_generation_kw == 0.0


def test_solar_service_above_maximum_clamping():
    """Verify voltage exceeding calibrated maximum clamps availability to 100.0%."""
    state = SolarService.calculate_solar_state(
        solar_voltage_v=3.5,
        min_voltage_v=0.0,
        max_voltage_v=3.0,
        solar_capacity_kw=10.0,
    )
    assert state.availability_percent == 100.0
    assert state.estimated_generation_kw == 10.0


def test_solar_service_invalid_calibration_raises():
    """Verify error when max_voltage <= min_voltage."""
    with pytest.raises(ValueError) as exc_info:
        SolarService.calculate_solar_state(
            solar_voltage_v=2.0,
            min_voltage_v=3.0,
            max_voltage_v=3.0,
            solar_capacity_kw=10.0,
        )
    assert "must be strictly greater than" in str(exc_info.value)


def test_solar_service_negative_voltage_raises():
    """Verify negative voltage raises ValueError."""
    with pytest.raises(ValueError):
        SolarService.calculate_solar_state(
            solar_voltage_v=-0.5,
            min_voltage_v=0.0,
            max_voltage_v=3.0,
            solar_capacity_kw=10.0,
        )
