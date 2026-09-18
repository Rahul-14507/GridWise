"""Virtual Battery Simulator.

Manages the operational lifecycle and state evolution of the simulated Battery Energy Storage System (BESS)
by delegating mathematical operations to BatteryService based on external commands.
"""

from typing import Optional, Tuple
from app.domain.models.battery import VirtualBattery
from app.domain.services.battery_service import BatteryService


class BatterySimulator:
    """State wrapper and simulator for the Virtual Battery (BESS)."""

    def __init__(self, initial_battery: Optional[VirtualBattery] = None) -> None:
        """Initialize Battery Simulator.

        Args:
            initial_battery: Initial VirtualBattery state or default configuration.
        """
        self._battery = initial_battery or VirtualBattery(
            capacity_kwh=50.0,
            soc_percent=60.0,
            max_charge_power_kw=10.0,
            max_discharge_power_kw=10.0,
            efficiency_percent=95.0,
            minimum_soc_percent=20.0,
        )
        self.last_charge_power_kw: float = 0.0
        self.last_discharge_power_kw: float = 0.0
        self.last_energy_delta_kwh: float = 0.0

    @property
    def battery(self) -> VirtualBattery:
        """Return the current VirtualBattery state."""
        return self._battery

    def set_battery(self, battery: VirtualBattery) -> None:
        """Set or replace current battery state."""
        self._battery = battery

    def step(
        self,
        duration_seconds: float,
        charge_power_kw: float = 0.0,
        discharge_power_kw: float = 0.0,
    ) -> Tuple[VirtualBattery, float, float]:
        """Apply charge or discharge commands for the duration of the time step.

        Note: A battery cannot simultaneously charge and discharge in the same physical interval.
        If both are specified > 0, ValueError is raised.

        Args:
            duration_seconds: Step interval duration in seconds.
            charge_power_kw: Requested charging power in kW (>= 0).
            discharge_power_kw: Requested discharge power in kW (>= 0).

        Returns:
            Tuple of:
                1. Updated VirtualBattery state.
                2. Actual active charge/discharge power applied in kW.
                3. Actual net energy transfer in kWh (positive for charge, negative for discharge).
        """
        if charge_power_kw > 0.0 and discharge_power_kw > 0.0:
            raise ValueError(
                f"Battery cannot simultaneously charge ({charge_power_kw} kW) and discharge ({discharge_power_kw} kW)"
            )

        duration_hours = duration_seconds / 3600.0

        if charge_power_kw > 0.0:
            updated_battery, applied_power, stored_energy = BatteryService.apply_charge(
                battery=self._battery,
                power_kw=charge_power_kw,
                duration_hours=duration_hours,
            )
            self._battery = updated_battery
            self.last_charge_power_kw = applied_power
            self.last_discharge_power_kw = 0.0
            self.last_energy_delta_kwh = stored_energy
            return self._battery, applied_power, stored_energy

        elif discharge_power_kw > 0.0:
            updated_battery, delivered_power, delivered_energy = BatteryService.apply_discharge(
                battery=self._battery,
                power_kw=discharge_power_kw,
                duration_hours=duration_hours,
            )
            self._battery = updated_battery
            self.last_charge_power_kw = 0.0
            self.last_discharge_power_kw = delivered_power
            self.last_energy_delta_kwh = -delivered_energy
            return self._battery, delivered_power, -delivered_energy

        else:
            self.last_charge_power_kw = 0.0
            self.last_discharge_power_kw = 0.0
            self.last_energy_delta_kwh = 0.0
            return self._battery, 0.0, 0.0
