"""Hard constraints validation module.

Provides independent verification of all infrastructure, charger, battery, and vehicle constraints.
Every optimization decision is passed through this independent verification step before being returned.
"""

from typing import Dict, List
from app.domain.models.system import SystemState
from app.domain.models.ev import EV, EVStatus


class ConstraintViolationError(Exception):
    """Raised when an optimization decision violates a hard physical or infrastructure constraint."""
    pass


class ConstraintValidator:
    """Validates hard physical and electrical constraints for charging allocations."""

    @staticmethod
    def validate_allocations(
        system_state: SystemState,
        ev_allocations: Dict[str, float],
        battery_discharge_kw: float,
        battery_charge_kw: float,
        simulation_interval_seconds: float,
    ) -> None:
        """Independently verify that allocations strictly obey all physical and safety constraints.

        Raises:
            ConstraintViolationError: If any hard constraint is breached.
        """
        # 1. Non-negativity check
        for ev_id, power in ev_allocations.items():
            if power < -1e-6:
                raise ConstraintViolationError(
                    f"Non-negativity violation: EV '{ev_id}' received negative power {power} kW"
                )

        if battery_discharge_kw < -1e-6 or battery_charge_kw < -1e-6:
            raise ConstraintViolationError("Battery power cannot be negative")

        building_demand = system_state.energy.grid.building_demand_kw
        solar_gen = system_state.energy.solar.estimated_generation_kw
        effective_capacity = system_state.thermal.effective_capacity_kw

        # 2. Total EV Power vs Available EV Power (accounting for battery contribution)
        total_ev_power = sum(ev_allocations.values())
        available_ev_power = max(
            0.0,
            (effective_capacity - building_demand) + solar_gen + battery_discharge_kw - battery_charge_kw,
        )

        # Allow slight floating point tolerance (0.001 kW)
        if total_ev_power > available_ev_power + 0.001:
            raise ConstraintViolationError(
                f"Infrastructure violation: Total EV allocation ({total_ev_power:.2f} kW) "
                f"exceeds available charging capacity ({available_ev_power:.2f} kW)"
            )

        # 3. Net Infrastructure Interconnection Load Check
        net_load = building_demand + total_ev_power - solar_gen - battery_discharge_kw + battery_charge_kw
        if net_load > effective_capacity + 0.001:
            raise ConstraintViolationError(
                f"Grid capacity breach: Net infrastructure load ({net_load:.2f} kW) "
                f"exceeds effective grid capacity ({effective_capacity:.2f} kW)"
            )

        # 4. EV Specific Constraints
        ev_map = {ev.id: ev for ev in system_state.evs}
        interval_hours = simulation_interval_seconds / 3600.0

        for ev_id, power in ev_allocations.items():
            if ev_id not in ev_map:
                raise ConstraintViolationError(f"Unknown EV '{ev_id}' present in allocations")

            ev = ev_map[ev_id]

            # Ineligibility check
            if ev.status == EVStatus.DISCONNECTED and power > 0.0:
                raise ConstraintViolationError(f"Disconnected EV '{ev_id}' cannot receive power ({power} kW)")

            if ev.soc_percent >= ev.target_soc_percent and power > 0.0:
                raise ConstraintViolationError(
                    f"Completed EV '{ev_id}' at/above target SoC cannot receive power ({power} kW)"
                )

            # Charger maximum rate check
            if power > ev.max_charging_power_kw + 0.001:
                raise ConstraintViolationError(
                    f"Charger hardware limit exceeded for '{ev_id}': "
                    f"allocated {power:.2f} kW > max {ev.max_charging_power_kw:.2f} kW"
                )

            # Energy required to target SoC check
            energy_needed = ev.energy_required_kwh
            energy_to_deliver = power * interval_hours
            if energy_to_deliver > energy_needed + 0.01:
                raise ConstraintViolationError(
                    f"Overcharging violation: Power {power:.2f} kW over {interval_hours:.4f}h "
                    f"would deliver {energy_to_deliver:.3f} kWh, exceeding deficit of {energy_needed:.3f} kWh"
                )

        # 5. Battery Operating Limits
        battery = system_state.battery
        if battery_discharge_kw > battery.max_discharge_power_kw + 0.001:
            raise ConstraintViolationError(
                f"Battery max discharge limit exceeded: {battery_discharge_kw:.2f} kW > {battery.max_discharge_power_kw:.2f} kW"
            )

        if battery_charge_kw > battery.max_charge_power_kw + 0.001:
            raise ConstraintViolationError(
                f"Battery max charge limit exceeded: {battery_charge_kw:.2f} kW > {battery.max_charge_power_kw:.2f} kW"
            )

        if battery_discharge_kw > 0.0 and battery.soc_percent <= battery.minimum_soc_percent:
            raise ConstraintViolationError(
                f"Battery discharge prohibited at or below minimum reserve SoC floor ({battery.minimum_soc_percent}%)"
            )
