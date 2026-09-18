"""Tests for BatteryStrategy dispatch decision logic."""

import pytest
from app.domain.models.battery import VirtualBattery
from app.optimizer.models import BatteryAction
from app.optimizer.battery_strategy import BatteryStrategy


def test_battery_strategy_discharge_under_deficit():
    """Verify battery discharges when unmet EV demand exists and battery has headroom above reserve."""
    battery = VirtualBattery(
        capacity_kwh=50.0,
        soc_percent=60.0,
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
        efficiency_percent=95.0,
        minimum_soc_percent=20.0,
    )
    # Unmet demand of 6.0 kW over 60 seconds
    action, power = BatteryStrategy.evaluate_battery_dispatch(
        battery=battery,
        unmet_ev_demand_kw=6.0,
        simulation_interval_seconds=60.0,
        enable_battery_support=True,
    )
    assert action == BatteryAction.DISCHARGE
    assert power == 6.0


def test_battery_strategy_clamped_to_max_discharge_rate():
    """Verify discharge cannot exceed battery max_discharge_power_kw."""
    battery = VirtualBattery(
        capacity_kwh=50.0,
        soc_percent=60.0,
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
        efficiency_percent=95.0,
        minimum_soc_percent=20.0,
    )
    # Unmet demand of 25.0 kW > max 10.0 kW
    action, power = BatteryStrategy.evaluate_battery_dispatch(
        battery=battery,
        unmet_ev_demand_kw=25.0,
        simulation_interval_seconds=60.0,
        enable_battery_support=True,
    )
    assert action == BatteryAction.DISCHARGE
    assert power == 10.0


def test_battery_strategy_idle_at_minimum_soc():
    """Verify battery remains IDLE when at or below minimum reserve SoC."""
    battery = VirtualBattery(
        capacity_kwh=50.0,
        soc_percent=20.0,
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
        efficiency_percent=95.0,
        minimum_soc_percent=20.0,
    )
    action, power = BatteryStrategy.evaluate_battery_dispatch(
        battery=battery,
        unmet_ev_demand_kw=10.0,
        simulation_interval_seconds=60.0,
        enable_battery_support=True,
    )
    assert action == BatteryAction.IDLE
    assert power == 0.0


def test_battery_strategy_idle_when_disabled():
    """Verify battery remains IDLE when enable_battery_support is False."""
    battery = VirtualBattery(
        capacity_kwh=50.0,
        soc_percent=60.0,
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
        efficiency_percent=95.0,
        minimum_soc_percent=20.0,
    )
    action, power = BatteryStrategy.evaluate_battery_dispatch(
        battery=battery,
        unmet_ev_demand_kw=10.0,
        simulation_interval_seconds=60.0,
        enable_battery_support=False,
    )
    assert action == BatteryAction.IDLE
    assert power == 0.0
