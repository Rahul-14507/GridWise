"""Urgency calculation module.

Calculates individual normalized urgency components for EVs:
- State of Charge (SoC) urgency
- Energy deficit fraction
- Time-to-departure urgency
- Waiting time fairness score
"""


class UrgencyCalculator:
    """Calculates bounded, normalized [0.0, 1.0] urgency components for Electric Vehicles."""

    @staticmethod
    def calculate_soc_urgency(soc_percent: float, target_soc_percent: float) -> float:
        """Calculate normalized SoC urgency based on relative deficit to target.

        Formula:
            soc_urgency = 1.0 - (soc_percent / target_soc_percent)

        Args:
            soc_percent: Current vehicle State of Charge (0.0% to 100.0%).
            target_soc_percent: Target vehicle State of Charge (0.0% to 100.0%).

        Returns:
            Normalized urgency float in range [0.0, 1.0].
        """
        if target_soc_percent <= 0.0 or soc_percent >= target_soc_percent:
            return 0.0
        val = 1.0 - (soc_percent / target_soc_percent)
        return round(max(0.0, min(1.0, val)), 4)

    @staticmethod
    def calculate_energy_deficit_score(energy_required_kwh: float, battery_capacity_kwh: float) -> float:
        """Calculate normalized energy deficit score representing fraction of total capacity still required.

        Formula:
            energy_deficit_score = energy_required_kwh / battery_capacity_kwh

        Args:
            energy_required_kwh: Energy remaining to reach target SoC in kWh (>= 0).
            battery_capacity_kwh: Total battery storage capacity in kWh (> 0).

        Returns:
            Normalized score float in range [0.0, 1.0].
        """
        if battery_capacity_kwh <= 0.0 or energy_required_kwh <= 0.0:
            return 0.0
        score = energy_required_kwh / battery_capacity_kwh
        return round(max(0.0, min(1.0, score)), 4)

    @staticmethod
    def calculate_departure_urgency(
        remaining_time_hours: float,
        horizon_hours: float = 4.0,
        critical_horizon_hours: float = 1.0,
    ) -> float:
        """Calculate normalized departure urgency as scheduled departure approaches.

        Uses a piecewise continuous monotonic function bounded in [0.0, 1.0]:
            - remaining <= 0: 1.0 (deadline passed / immediate)
            - 0 < remaining <= critical_horizon (e.g. <= 1h): High to critical urgency [0.8, 1.0]
            - critical_horizon < remaining <= horizon (e.g. 1h..4h): Moderate to high urgency [0.1, 0.8]
            - remaining > horizon (e.g. > 4h): Low urgency [0.0, 0.1]

        Args:
            remaining_time_hours: Time until scheduled departure in hours.
            horizon_hours: Outer horizon where departure urgency starts becoming relevant in hours.
            critical_horizon_hours: Inner critical horizon threshold in hours.

        Returns:
            Normalized departure urgency float in range [0.0, 1.0].
        """
        if remaining_time_hours <= 0.0:
            return 1.0

        if remaining_time_hours <= critical_horizon_hours:
            # Scale linearly from 1.0 (at 0h) down to 0.8 (at critical_horizon)
            ratio = remaining_time_hours / critical_horizon_hours
            urgency = 1.0 - (0.2 * ratio)
        elif remaining_time_hours <= horizon_hours:
            # Scale linearly from 0.8 (at critical_horizon) down to 0.1 (at horizon)
            span = horizon_hours - critical_horizon_hours
            ratio = (remaining_time_hours - critical_horizon_hours) / span
            urgency = 0.8 - (0.7 * ratio)
        else:
            # Taper off gently below 0.1 for very long stays
            excess = remaining_time_hours - horizon_hours
            urgency = max(0.0, 0.1 / (1.0 + 0.2 * excess))

        return round(max(0.0, min(1.0, urgency)), 4)

    @staticmethod
    def calculate_waiting_score(waiting_minutes: float, reference_minutes: float = 60.0) -> float:
        """Calculate normalized waiting score to promote fairness for vehicles waiting without charge.

        Formula:
            waiting_score = min(waiting_minutes / reference_minutes, 1.0)

        Args:
            waiting_minutes: Duration vehicle has been connected in minutes (>= 0).
            reference_minutes: Benchmark duration in minutes considered full waiting credit (> 0).

        Returns:
            Normalized waiting score float in range [0.0, 1.0].
        """
        if waiting_minutes <= 0.0:
            return 0.0
        if reference_minutes <= 0.0:
            return 1.0
        score = waiting_minutes / reference_minutes
        return round(max(0.0, min(1.0, score)), 4)
