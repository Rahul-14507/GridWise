"""Tests for Energy models, Virtual Battery, and EnergyService."""

import pytest
from pydantic import ValidationError

from app.domain.models.energy import GridState, SolarState, EnergyState
from app.domain.models.battery import VirtualBattery
from app.domain.services.energy_service import EnergyService


def test_grid_state_valid():
    """Verify GridState model validation with valid values."""
    grid = GridState(
        max_capacity_kw=25.0,
        building_demand_kw=8.0,
        effective_capacity_kw=17.0,
    )
    assert grid.max_capacity_kw == 25.0
    assert grid.building_demand_kw == 8.0
    assert grid.effective_capacity_kw == 17.0


def test_grid_state_negative_capacity():
    """Verify negative grid capacity is rejected."""
    with pytest.raises(ValidationError):
        GridState(
            max_capacity_kw=-5.0,
            building_demand_kw=8.0,
            effective_capacity_kw=17.0,
        )


def test_solar_state_valid():
    """Verify SolarState validation with valid values."""
    solar = SolarState(
        solar_voltage_v=2.14,
        availability_percent=42.8,
        estimated_generation_kw=5.0,
    )
    assert solar.solar_voltage_v == 2.14
    assert solar.availability_percent == 42.8
    assert solar.estimated_generation_kw == 5.0


def test_solar_state_invalid_availability():
    """Verify availability percentage must be between 0 and 100."""
    with pytest.raises(ValidationError):
        SolarState(
            solar_voltage_v=2.14,
            availability_percent=110.0,
            estimated_generation_kw=5.0,
        )


def test_energy_state_combined():
    """Verify composite EnergyState model."""
    grid = GridState(
        max_capacity_kw=25.0,
        building_demand_kw=8.0,
        effective_capacity_kw=17.0,
    )
    solar = SolarState(
        solar_voltage_v=2.14,
        availability_percent=42.8,
        estimated_generation_kw=5.0,
    )
    energy = EnergyState(
        grid=grid,
        solar=solar,
        available_ev_charging_capacity_kw=24.0,
    )
    assert energy.grid.max_capacity_kw == 25.0
    assert energy.solar.estimated_generation_kw == 5.0
    assert energy.available_ev_charging_capacity_kw == 24.0


def test_virtual_battery_valid():
    """Verify VirtualBattery model with standard valid parameters."""
    battery = VirtualBattery(
        capacity_kwh=50.0,
        soc_percent=60.0,
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
        efficiency_percent=95.0,
        minimum_soc_percent=20.0,
    )
    assert battery.capacity_kwh == 50.0
    assert battery.soc_percent == 60.0
    assert battery.minimum_soc_percent == 20.0


def test_virtual_battery_soc_below_minimum():
    """Verify error when current SoC is below configured minimum SoC."""
    with pytest.raises(ValidationError) as exc_info:
        VirtualBattery(
            capacity_kwh=50.0,
            soc_percent=15.0,
            max_charge_power_kw=10.0,
            max_discharge_power_kw=10.0,
            efficiency_percent=95.0,
            minimum_soc_percent=20.0,
        )
    assert "minimum_soc_percent (20.0%) cannot exceed current soc_percent (15.0%)" in str(exc_info.value)


@pytest.mark.parametrize("invalid_val", [-5.0, 105.0])
def test_virtual_battery_invalid_efficiency(invalid_val):
    """Verify efficiency must be 0-100%."""
    with pytest.raises(ValidationError):
        VirtualBattery(
            capacity_kwh=50.0,
            soc_percent=50.0,
            max_charge_power_kw=10.0,
            max_discharge_power_kw=10.0,
            efficiency_percent=invalid_val,
            minimum_soc_percent=20.0,
        )


def test_energy_service_available_capacity_baseline():
    """Test standard power availability calculation.

    Grid = 25 kW, Building = 8 kW, Solar = 5 kW, Battery = 2 kW.
    Expected = 24 kW.
    """
    available = EnergyService.calculate_available_ev_power(
        grid_capacity_kw=25.0,
        building_demand_kw=8.0,
        solar_generation_kw=5.0,
        battery_discharge_kw=2.0,
    )
    assert available == 24.0


def test_energy_service_negative_clamping():
    """Verify available power is never negative when demand exceeds total supply."""
    available = EnergyService.calculate_available_ev_power(
        grid_capacity_kw=10.0,
        building_demand_kw=20.0,
        solar_generation_kw=2.0,
        battery_discharge_kw=1.0,
    )
    assert available == 0.0


def test_energy_service_rejects_negative_inputs():
    """Verify EnergyService raises ValueError for negative inputs."""
    with pytest.raises(ValueError):
        EnergyService.calculate_available_ev_power(
            grid_capacity_kw=-10.0,
            building_demand_kw=5.0,
        )
