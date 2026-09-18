"""Power allocator module.

Implements a deterministic, multi-pass priority-ranked charging power allocator.
Distributes available power budget among connected EVs ordered by priority score and deadline risk,
respecting individual charger limits and energy deficits without starvation.
"""

from typing import Dict, List, Tuple
from app.domain.models.ev import EV, EVStatus
from app.optimizer.models import DeadlineStatus


class PowerAllocator:
    """Allocates available charging power to vehicles based on priority rankings and hard constraints."""

    @staticmethod
    def allocate_power(
        ev_items: List[Tuple[EV, float, DeadlineStatus]],  # List of (EV, priority_score, deadline_status)
        available_power_kw: float,
        simulation_interval_seconds: float,
    ) -> Dict[str, float]:
        """Allocate available power budget across EVs.

        Algorithm:
            1. Filter eligible EVs (connected, arrived, soc < target_soc).
            2. Compute each EV's maximum feasible charging power for this interval:
               P_max_feasible = min(ev.max_charging_power_kw, ev.energy_required_kwh / duration_hours)
            3. Sort eligible vehicles descending by:
               - Deadline urgency: AT_RISK prioritized
               - Priority score (higher score first)
            4. Iteratively allocate power up to P_max_feasible.
            5. Decrement remaining power.
            6. Ineligible vehicles receive 0.0 kW.

        Args:
            ev_items: List of tuples containing (EV domain model, computed priority score, deadline status).
            available_power_kw: Total available electrical capacity budget in kW (>= 0).
            simulation_interval_seconds: Duration of the time interval in seconds (> 0).

        Returns:
            Dictionary mapping EV ID -> allocated power in kW (float >= 0.0).
        """
        allocations: Dict[str, float] = {ev.id: 0.0 for ev, _, _ in ev_items}

        if available_power_kw <= 0.0 or simulation_interval_seconds <= 0.0:
            return allocations

        duration_hours = simulation_interval_seconds / 3600.0
        remaining_power = available_power_kw

        # 1. Identify and prepare eligible candidates
        eligible_candidates = []
        for ev, score, status in ev_items:
            # Check eligibility
            if ev.status == EVStatus.DISCONNECTED or ev.soc_percent >= ev.target_soc_percent or ev.energy_required_kwh <= 0.0:
                continue

            # Interval power required to reach target SoC
            power_for_target = ev.energy_required_kwh / duration_hours if duration_hours > 0 else 0.0
            max_feasible_power = min(ev.max_charging_power_kw, power_for_target)

            # Deadline sorting priority rank (AT_RISK=2, FEASIBLE=1, other=0)
            deadline_rank = 2 if status == DeadlineStatus.AT_RISK else (1 if status == DeadlineStatus.FEASIBLE else 0)

            eligible_candidates.append({
                "ev": ev,
                "priority_score": score,
                "deadline_rank": deadline_rank,
                "max_feasible_power": max_feasible_power,
            })

        # 2. Sort candidates: primary by deadline_rank, secondary by priority_score
        eligible_candidates.sort(
            key=lambda x: (x["deadline_rank"], x["priority_score"]),
            reverse=True,
        )

        # 3. Constrained multi-pass distribution
        for candidate in eligible_candidates:
            if remaining_power <= 0.0001:
                break

            ev = candidate["ev"]
            requested_power = candidate["max_feasible_power"]
            granted_power = min(requested_power, remaining_power)

            allocations[ev.id] = round(granted_power, 4)
            remaining_power -= granted_power

        return allocations
