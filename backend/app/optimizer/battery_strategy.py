"""Battery operational strategy module.

Determines whether to dispatch stationary battery energy to supplement EV charging capacity
during solar deficits or grid constraint periods, respecting electrochemical bounds.
"""

from typing import Tuple
from app.domain.models.battery import VirtualBattery
from app.optimizer.models import BatteryAction


class BatteryStrategy:
    """Evaluates stationary battery discharge decisions to support charging cluster demand."""

    @staticmethod
    def evaluate_battery_dispatch(
        battery: VirtualBattery,
        unmet_ev_demand_kw: float,
        simulation_interval_seconds: float,
        enable_battery_support: bool = True,
    ) -> Tuple[BatteryAction, float]:
        """Determine permissible battery discharge power to support EV charging deficit.

        Args:
            battery: Current VirtualBattery state.
            unmet_ev_demand_kw: Total EV charging demand exceeding available grid+solar power in kW (>= 0).
            simulation_interval_seconds: Current time step duration in seconds (> 0).
            enable_battery_support: Configuration flag enabling battery dispatch.

        Returns:
            Tuple of (BatteryAction, battery_power_kw).
        """
        if not enable_battery_support or unmet_ev_demand_kw <= 0.0 or simulation_interval_seconds <= 0.0:
            return BatteryAction.IDLE, 0.0

        # Check reserve floor
        if battery.soc_percent <= battery.minimum_soc_percent:
            return BatteryAction.IDLE, 0.0

        duration_hours = simulation_interval_seconds / 3600.0
        efficiency = battery.efficiency_percent / 100.0

        # Usable energy in battery above minimum SoC reserve in kWh
        usable_internal_kwh = battery.capacity_kwh * ((battery.soc_percent - battery.minimum_soc_percent) / 100.0)
        usable_deliverable_kwh = usable_internal_kwh * efficiency

        # Maximum deliverable power sustained over the interval duration
        max_duration_power_kw = usable_deliverable_kwh / duration_hours if duration_hours > 0 else 0.0

        # Max discharge is limited by hardware inverter rating and remaining energy
        discharge_limit = min(battery.max_discharge_power_kw, max_duration_power_kw)
        actual_discharge_kw = min(unmet_ev_demand_kw, discharge_limit)

        if actual_discharge_kw > 0.001:
            return BatteryAction.DISCHARGE, round(actual_discharge_kw, 4)

        return BatteryAction.IDLE, 0.0
