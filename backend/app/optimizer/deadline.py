"""Deadline risk analysis module.

Evaluates whether an EV can physically reach its target SoC before scheduled departure
under its maximum onboard charging power constraint.
"""

from typing import Tuple
from app.optimizer.models import DeadlineStatus


class DeadlineAnalyzer:
    """Evaluates EV charging feasibility against departure deadlines."""

    @staticmethod
    def analyze_deadline(
        energy_required_kwh: float,
        remaining_time_hours: float,
        max_charging_power_kw: float,
    ) -> Tuple[DeadlineStatus, float]:
        """Analyze whether the vehicle can reach its target SoC before departure.

        Rules:
            1. If energy_required <= 0: COMPLETE, required_avg_power = 0.0 kW
            2. If remaining_time <= 0 and energy_required > 0: EXPIRED, required_avg_power = 0.0 kW
            3. If required_avg_power > max_charging_power: AT_RISK (deadline infeasible under charger rate)
            4. Otherwise: FEASIBLE

        Args:
            energy_required_kwh: Remaining energy needed to reach target SoC in kWh (>= 0).
            remaining_time_hours: Time until scheduled departure in hours.
            max_charging_power_kw: Maximum charging rate supported by EV charger in kW (> 0).

        Returns:
            Tuple of (DeadlineStatus, required_average_power_kw).
        """
        if energy_required_kwh <= 0.0:
            return DeadlineStatus.COMPLETE, 0.0

        if remaining_time_hours <= 0.0:
            return DeadlineStatus.EXPIRED, 0.0

        required_avg_power = energy_required_kwh / remaining_time_hours

        if required_avg_power > max_charging_power_kw:
            status = DeadlineStatus.AT_RISK
        else:
            status = DeadlineStatus.FEASIBLE

        return status, round(required_avg_power, 4)
