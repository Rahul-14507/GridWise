"""Grid and Building Electricity Demand simulator.

Simulates facility non-EV baseload electricity demand across diurnal operating profiles
using deterministic interpolation and pseudo-random noise.
"""

import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class GridSimulator:
    """Simulates facility building electricity demand and grid supply limits."""

    # Default 24-hour building demand curve (Hour -> Baseload in kW)
    DEFAULT_LOAD_PROFILE: List[Tuple[float, float]] = [
        (0.0, 3.0),   # 00:00 - Night minimum
        (6.0, 4.5),   # 06:00 - Facility morning ramp-up
        (9.0, 9.0),   # 09:00 - Workday operations peak
        (12.0, 7.5),  # 12:00 - Midday lull
        (15.0, 8.5),  # 15:00 - Afternoon operations
        (17.0, 11.0), # 17:00 - Early evening peak
        (19.0, 13.5), # 19:00 - Evening peak demand
        (22.0, 6.0),  # 22:00 - Facility winding down
        (24.0, 3.0),  # 24:00 - Night baseline return
    ]

    def __init__(
        self,
        base_grid_capacity_kw: float = 25.0,
        load_profile: Optional[List[Tuple[float, float]]] = None,
        noise_percent: float = 0.05,
        random_seed: int = 42,
    ) -> None:
        """Initialize GridSimulator.

        Args:
            base_grid_capacity_kw: Configured maximum grid interconnection capacity in kW.
            load_profile: List of (hour, demand_kw) keypoints defining 24-hour diurnal profile.
            noise_percent: Fractional random noise perturbation applied to demand (e.g. 0.05 = ±5%).
            random_seed: Seed for deterministic pseudo-random noise generation.
        """
        self.base_grid_capacity_kw = base_grid_capacity_kw
        self.load_profile = sorted(load_profile or self.DEFAULT_LOAD_PROFILE, key=lambda x: x[0])
        self.noise_percent = noise_percent
        self._rng = random.Random(random_seed)

        # Scenario overrides
        self.override_demand_kw: Optional[float] = None

    def set_demand_override(self, demand_kw: Optional[float]) -> None:
        """Set explicit building demand override (used by scenarios)."""
        self.override_demand_kw = demand_kw

    def reset_seed(self, seed: int) -> None:
        """Reset the random number generator seed for deterministic reproducibility."""
        self._rng = random.Random(seed)

    def _interpolate_profile(self, hour: float) -> float:
        """Linearly interpolate the building demand at the given fractional hour."""
        normalized_hour = hour % 24.0

        for i in range(len(self.load_profile) - 1):
            h1, d1 = self.load_profile[i]
            h2, d2 = self.load_profile[i + 1]
            if h1 <= normalized_hour <= h2:
                fraction = (normalized_hour - h1) / (h2 - h1)
                return d1 + fraction * (d2 - d1)

        return self.load_profile[0][1]

    def get_building_demand_kw(self, timestamp: datetime) -> float:
        """Calculate the simulated building electricity demand for the given timestamp.

        Args:
            timestamp: Current simulation timestamp (timezone-aware).

        Returns:
            Building demand in kW (float >= 0.0).
        """
        if self.override_demand_kw is not None:
            return round(max(0.0, self.override_demand_kw), 4)

        hour = timestamp.hour + timestamp.minute / 60.0 + timestamp.second / 3600.0
        base_demand = self._interpolate_profile(hour)

        # Apply deterministic pseudo-random noise
        if self.noise_percent > 0.0:
            noise_factor = self._rng.uniform(-self.noise_percent, self.noise_percent)
            demand = base_demand * (1.0 + noise_factor)
        else:
            demand = base_demand

        return round(max(0.0, demand), 4)
