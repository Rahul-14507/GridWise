"""Energy domain service.

Provides foundational energy calculations for facility power management.
Optimization algorithms, priority scoring, and load-shedding scheduling are
deferred to subsequent milestones.
"""


class EnergyService:
    """Service providing core facility power balance and available capacity calculations."""

    @staticmethod
    def calculate_available_ev_power(
        grid_capacity_kw: float,
        building_demand_kw: float,
        solar_generation_kw: float = 0.0,
        battery_discharge_kw: float = 0.0,
    ) -> float:
        """Calculate the total net electrical power available for EV charging infrastructure.

        Formula:
            Net Available = (Grid Capacity - Building Demand) + Solar Generation + Battery Discharge

        Constraints:
            - Clamped to minimum 0.0 kW (never returns negative available power).
            - Does not partition or allocate power among individual EV charging points.

        Args:
            grid_capacity_kw: Maximum/effective grid power limit in kW (>= 0).
            building_demand_kw: Baseload facility power consumed by building in kW (>= 0).
            solar_generation_kw: Estimated/modelled solar generation in kW (>= 0).
            battery_discharge_kw: Active battery power contribution in kW (>= 0).

        Returns:
            Available power in kW for EV charging (float >= 0.0).
        """
        if grid_capacity_kw < 0.0:
            raise ValueError("grid_capacity_kw must be non-negative")
        if building_demand_kw < 0.0:
            raise ValueError("building_demand_kw must be non-negative")
        if solar_generation_kw < 0.0:
            raise ValueError("solar_generation_kw must be non-negative")
        if battery_discharge_kw < 0.0:
            raise ValueError("battery_discharge_kw must be non-negative")

        net_power = (grid_capacity_kw - building_demand_kw) + solar_generation_kw + battery_discharge_kw
        return max(0.0, float(net_power))
