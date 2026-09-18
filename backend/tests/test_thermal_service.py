"""Tests for ThermalService grid capacity derating domain calculations."""

import pytest
from app.domain.models.simulation import ThermalStatus
from app.domain.services.thermal_service import ThermalService


def test_thermal_service_normal_temperature():
    """Verify temperature at or below derating start experiences zero derating."""
    state = ThermalService.calculate_thermal_derating(
        temperature_c=25.0,
        base_capacity_kw=25.0,
        derating_start_c=35.0,
        critical_temp_c=50.0,
        min_capacity_kw=10.0,
    )
    assert state.effective_capacity_kw == 25.0
    assert state.derating_factor == 1.0
    assert state.thermal_status == ThermalStatus.NORMAL


def test_thermal_service_at_derating_threshold():
    """Verify temperature exactly at derating start is considered NORMAL with 1.0 factor."""
    state = ThermalService.calculate_thermal_derating(
        temperature_c=35.0,
        base_capacity_kw=25.0,
        derating_start_c=35.0,
        critical_temp_c=50.0,
        min_capacity_kw=10.0,
    )
    assert state.effective_capacity_kw == 25.0
    assert state.derating_factor == 1.0
    assert state.thermal_status == ThermalStatus.NORMAL


def test_thermal_service_intermediate_derating():
    """Verify linear capacity reduction at intermediate temperatures."""
    # Midpoint: (50 - 35)/2 + 35 = 42.5°C
    # Expected capacity: 25 - 0.5 * (25 - 10) = 17.5 kW
    # Expected factor: 17.5 / 25.0 = 0.70
    state = ThermalService.calculate_thermal_derating(
        temperature_c=42.5,
        base_capacity_kw=25.0,
        derating_start_c=35.0,
        critical_temp_c=50.0,
        min_capacity_kw=10.0,
    )
    assert state.effective_capacity_kw == 17.5
    assert state.derating_factor == 0.7
    assert state.thermal_status == ThermalStatus.ELEVATED


def test_thermal_service_critical_temperature():
    """Verify critical temperature triggers minimum capacity and CRITICAL status."""
    state = ThermalService.calculate_thermal_derating(
        temperature_c=50.0,
        base_capacity_kw=25.0,
        derating_start_c=35.0,
        critical_temp_c=50.0,
        min_capacity_kw=10.0,
    )
    assert state.effective_capacity_kw == 10.0
    assert state.derating_factor == 0.4
    assert state.thermal_status == ThermalStatus.CRITICAL


def test_thermal_service_above_critical_temperature():
    """Verify temperatures exceeding critical ceiling remain clamped at minimum capacity."""
    state = ThermalService.calculate_thermal_derating(
        temperature_c=58.0,
        base_capacity_kw=25.0,
        derating_start_c=35.0,
        critical_temp_c=50.0,
        min_capacity_kw=10.0,
    )
    assert state.effective_capacity_kw == 10.0
    assert state.derating_factor == 0.4
    assert state.thermal_status == ThermalStatus.CRITICAL


def test_thermal_service_invalid_configuration_raises():
    """Verify invalid configuration constraints raise ValueError."""
    # critical <= derating_start
    with pytest.raises(ValueError):
        ThermalService.calculate_thermal_derating(
            temperature_c=30.0,
            base_capacity_kw=25.0,
            derating_start_c=40.0,
            critical_temp_c=40.0,
            min_capacity_kw=10.0,
        )

    # min_capacity > base_capacity
    with pytest.raises(ValueError):
        ThermalService.calculate_thermal_derating(
            temperature_c=30.0,
            base_capacity_kw=20.0,
            derating_start_c=35.0,
            critical_temp_c=50.0,
            min_capacity_kw=25.0,
        )


def test_thermal_service_determinism():
    """Verify that identical inputs consistently yield identical outputs."""
    s1 = ThermalService.calculate_thermal_derating(41.2, 30.0, 35.0, 45.0, 15.0)
    s2 = ThermalService.calculate_thermal_derating(41.2, 30.0, 35.0, 45.0, 15.0)
    assert s1 == s2
