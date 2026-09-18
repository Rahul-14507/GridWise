"""Virtual Battery domain service.

Provides explicit charge/discharge energy balance mathematics for a software-simulated
Battery Energy Storage System (BESS).
Note: This service executes explicit external commands and does NOT decide when to charge or discharge.
"""

from typing import Tuple
from app.domain.models.battery import VirtualBattery


class BatteryService:
    """Service executing physical charge and discharge energy calculations for VirtualBattery."""

    @staticmethod
    def apply_charge(
        battery: VirtualBattery,
        power_kw: float,
        duration_hours: float,
    ) -> Tuple[VirtualBattery, float, float]:
        """Apply an external charging power command to the virtual battery over a duration.

        Constraints:
            - Clamped to battery.max_charge_power_kw.
            - Energy stored respects round-trip efficiency: stored = input * efficiency.
            - State of Charge cannot exceed 100.0%.
            - Clamps power and stored energy if full capacity is reached during interval.

        Args:
            battery: Current VirtualBattery state.
            power_kw: Requested charging power in kW (>= 0).
            duration_hours: Duration of the charging interval in hours (> 0).

        Returns:
            Tuple of:
                1. Updated VirtualBattery model.
                2. Actual average charging power consumed from grid/solar in kW.
                3. Actual net energy added to battery chemistry in kWh.
        """
        if power_kw < 0.0:
            raise ValueError(f"Charging power_kw must be non-negative (got {power_kw})")
        if duration_hours < 0.0:
            raise ValueError(f"duration_hours must be non-negative (got {duration_hours})")

        if power_kw == 0.0 or duration_hours == 0.0 or battery.soc_percent >= 100.0:
            return battery, 0.0, 0.0

        # Enforce maximum charging power limit
        charge_power = min(power_kw, battery.max_charge_power_kw)
        efficiency = battery.efficiency_percent / 100.0

        # Remaining capacity headroom in kWh
        headroom_kwh = battery.capacity_kwh * (1.0 - battery.soc_percent / 100.0)

        # Potential energy to store (after efficiency loss)
        potential_stored_kwh = charge_power * duration_hours * efficiency

        if potential_stored_kwh <= headroom_kwh:
            actual_stored_kwh = potential_stored_kwh
            actual_power_kw = charge_power
        else:
            # Reached 100% capacity during interval
            actual_stored_kwh = headroom_kwh
            actual_power_kw = (headroom_kwh / (duration_hours * efficiency)) if efficiency > 0 else 0.0

        delta_soc = (actual_stored_kwh / battery.capacity_kwh) * 100.0
        new_soc = min(100.0, round(battery.soc_percent + delta_soc, 4))

        updated_battery = VirtualBattery(
            capacity_kwh=battery.capacity_kwh,
            soc_percent=new_soc,
            max_charge_power_kw=battery.max_charge_power_kw,
            max_discharge_power_kw=battery.max_discharge_power_kw,
            efficiency_percent=battery.efficiency_percent,
            minimum_soc_percent=battery.minimum_soc_percent,
        )

        return updated_battery, round(actual_power_kw, 4), round(actual_stored_kwh, 4)

    @staticmethod
    def apply_discharge(
        battery: VirtualBattery,
        power_kw: float,
        duration_hours: float,
    ) -> Tuple[VirtualBattery, float, float]:
        """Apply an external discharge power command from the virtual battery over a duration.

        Constraints:
            - Clamped to battery.max_discharge_power_kw.
            - Energy delivered respects round-trip efficiency: internal_removed = delivered / efficiency.
            - State of Charge cannot fall below configured minimum_soc_percent.
            - Clamps delivered power and energy if minimum SoC is reached during interval.

        Args:
            battery: Current VirtualBattery state.
            power_kw: Requested discharge output power in kW (>= 0).
            duration_hours: Duration of the discharge interval in hours (> 0).

        Returns:
            Tuple of:
                1. Updated VirtualBattery model.
                2. Actual average power delivered to system in kW.
                3. Actual delivered energy in kWh.
        """
        if power_kw < 0.0:
            raise ValueError(f"Discharge power_kw must be non-negative (got {power_kw})")
        if duration_hours < 0.0:
            raise ValueError(f"duration_hours must be non-negative (got {duration_hours})")

        if power_kw == 0.0 or duration_hours == 0.0 or battery.soc_percent <= battery.minimum_soc_percent:
            return battery, 0.0, 0.0

        discharge_power = min(power_kw, battery.max_discharge_power_kw)
        efficiency = battery.efficiency_percent / 100.0

        # Usable energy in battery above minimum SoC reserve floor in kWh
        usable_internal_kwh = battery.capacity_kwh * ((battery.soc_percent - battery.minimum_soc_percent) / 100.0)

        # Potential internal energy removed to deliver requested power
        potential_delivered_kwh = discharge_power * duration_hours
        potential_removed_kwh = (potential_delivered_kwh / efficiency) if efficiency > 0 else 0.0

        if potential_removed_kwh <= usable_internal_kwh:
            actual_removed_kwh = potential_removed_kwh
            actual_delivered_kwh = potential_delivered_kwh
            actual_power_kw = discharge_power
        else:
            # Reached minimum reserve SoC floor during interval
            actual_removed_kwh = usable_internal_kwh
            actual_delivered_kwh = usable_internal_kwh * efficiency
            actual_power_kw = actual_delivered_kwh / duration_hours if duration_hours > 0 else 0.0

        delta_soc = (actual_removed_kwh / battery.capacity_kwh) * 100.0
        new_soc = max(battery.minimum_soc_percent, round(battery.soc_percent - delta_soc, 4))

        updated_battery = VirtualBattery(
            capacity_kwh=battery.capacity_kwh,
            soc_percent=new_soc,
            max_charge_power_kw=battery.max_charge_power_kw,
            max_discharge_power_kw=battery.max_discharge_power_kw,
            efficiency_percent=battery.efficiency_percent,
            minimum_soc_percent=battery.minimum_soc_percent,
        )

        return updated_battery, round(actual_power_kw, 4), round(actual_delivered_kwh, 4)
