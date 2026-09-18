"""Tests for BatteryService charge/discharge physics."""

import pytest
from app.domain.models.battery import VirtualBattery
from app.domain.services.battery_service import BatteryService


@pytest.fixture
def standard_battery() -> VirtualBattery:
    return VirtualBattery(
        capacity_kwh=50.0,
        soc_percent=50.0,
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
        efficiency_percent=95.0,
        minimum_soc_percent=20.0,
    )


def test_battery_service_charge_standard(standard_battery):
    """Verify standard charging increments battery energy accounting for efficiency."""
    # 10 kW for 1 hour @ 95% efficiency -> 9.5 kWh stored.
    # 50 kWh capacity, initial 50% (25 kWh). New: 25 + 9.5 = 34.5 kWh -> 69.0% SoC.
    updated, applied_power, stored_energy = BatteryService.apply_charge(
        battery=standard_battery,
        power_kw=10.0,
        duration_hours=1.0,
    )
    assert applied_power == 10.0
    assert stored_energy == 9.5
    assert updated.soc_percent == 69.0


def test_battery_service_charge_max_rate_clamp(standard_battery):
    """Verify requested charge power is clamped to battery max_charge_power_kw."""
    # Request 25 kW, battery max is 10 kW -> clamped to 10 kW.
    updated, applied_power, stored_energy = BatteryService.apply_charge(
        battery=standard_battery,
        power_kw=25.0,
        duration_hours=0.5,
    )
    assert applied_power == 10.0
    assert stored_energy == 4.75  # 10 * 0.5 * 0.95
    assert updated.soc_percent == 59.5


def test_battery_service_charge_100_percent_cap(standard_battery):
    """Verify battery charging cannot exceed 100% SoC."""
    # Initial 50% (needs 25 kWh stored). Request 50 kW for 2 hours.
    updated, applied_power, stored_energy = BatteryService.apply_charge(
        battery=standard_battery,
        power_kw=10.0,
        duration_hours=5.0,
    )
    assert updated.soc_percent == 100.0
    assert stored_energy == 25.0  # Exactly the headroom


def test_battery_service_discharge_standard(standard_battery):
    """Verify standard discharging delivers requested power and decrements battery energy."""
    # Deliver 10 kW for 1 hour @ 95% efficiency.
    # Internal energy removed = 10 / 0.95 = 10.5263 kWh.
    # Initial 25 kWh -> New energy: 14.4737 kWh -> 28.9474% SoC.
    updated, delivered_power, delivered_energy = BatteryService.apply_discharge(
        battery=standard_battery,
        power_kw=10.0,
        duration_hours=1.0,
    )
    assert delivered_power == 10.0
    assert delivered_energy == 10.0
    assert 28.94 <= updated.soc_percent <= 28.95


def test_battery_service_discharge_min_soc_floor(standard_battery):
    """Verify discharging cannot deplete battery below configured minimum_soc_percent (20%)."""
    # Usable energy above 20%: (50% - 20%) * 50 = 15.0 kWh.
    updated, delivered_power, delivered_energy = BatteryService.apply_discharge(
        battery=standard_battery,
        power_kw=10.0,
        duration_hours=5.0,
    )
    assert updated.soc_percent == 20.0
    assert delivered_energy == 15.0 * 0.95  # 14.25 kWh


def test_battery_service_zero_power_or_duration(standard_battery):
    """Verify zero power or zero duration leaves battery completely unchanged."""
    b1, p1, e1 = BatteryService.apply_charge(standard_battery, 0.0, 1.0)
    assert b1.soc_percent == 50.0 and p1 == 0.0 and e1 == 0.0

    b2, p2, e2 = BatteryService.apply_discharge(standard_battery, 10.0, 0.0)
    assert b2.soc_percent == 50.0 and p2 == 0.0 and e2 == 0.0


def test_battery_service_negative_inputs_raise(standard_battery):
    """Verify negative power or duration raises ValueError."""
    with pytest.raises(ValueError):
        BatteryService.apply_charge(standard_battery, -5.0, 1.0)

    with pytest.raises(ValueError):
        BatteryService.apply_discharge(standard_battery, 5.0, -1.0)
