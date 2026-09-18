"""Simulation Clock abstraction.

Decouples the simulation engine from the host operating system clock,
enabling deterministic, reproducible time advancement and accelerated execution.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


class SimulationClock:
    """Synthetic timezone-aware clock for deterministic simulation advancement."""

    def __init__(self, initial_time: Optional[datetime] = None) -> None:
        """Initialize simulation clock.

        Args:
            initial_time: Starting timestamp (must be timezone-aware). Defaults to 2026-09-18 08:00:00 UTC.
        """
        if initial_time is not None:
            if initial_time.tzinfo is None or initial_time.tzinfo.utcoffset(initial_time) is None:
                raise ValueError("initial_time must be timezone-aware")
            self._current_time: datetime = initial_time
        else:
            self._current_time = datetime(2026, 9, 18, 8, 0, 0, tzinfo=timezone.utc)

        self._start_time: datetime = self._current_time

    @property
    def current_time(self) -> datetime:
        """Return the current simulation timestamp."""
        return self._current_time

    @property
    def elapsed_seconds(self) -> float:
        """Return elapsed simulation time in seconds since initialization or reset."""
        return (self._current_time - self._start_time).total_seconds()

    def advance(self, seconds: float) -> datetime:
        """Advance the simulation time by the specified number of seconds.

        Args:
            seconds: Time duration to advance in seconds (>= 0).

        Returns:
            The new current simulation datetime.
        """
        if seconds < 0.0:
            raise ValueError(f"Cannot advance clock by negative duration ({seconds}s)")
        self._current_time += timedelta(seconds=seconds)
        return self._current_time

    def reset(self, new_initial_time: Optional[datetime] = None) -> datetime:
        """Reset the simulation clock to its original starting time or a new initial time.

        Args:
            new_initial_time: Optional new starting timestamp (must be timezone-aware).

        Returns:
            The reset current simulation datetime.
        """
        if new_initial_time is not None:
            if new_initial_time.tzinfo is None or new_initial_time.tzinfo.utcoffset(new_initial_time) is None:
                raise ValueError("new_initial_time must be timezone-aware")
            self._start_time = new_initial_time
        self._current_time = self._start_time
        return self._current_time
