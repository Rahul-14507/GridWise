"""Electric Vehicle (EV) fleet simulator.

Applies externally supplied power allocations to vehicles over simulation intervals,
updates battery State of Charge, enforces vehicle hardware limits, and tracks lifecycle state transitions.
Note: EVSimulator does NOT decide power allocations; it only simulates the physics of applied allocations.
"""

from datetime import datetime
from typing import Dict, List, Optional
from app.domain.models.ev import EV, EVStatus


class EVSimulator:
    """Simulates charging dynamics and state transitions for a fleet of Electric Vehicles."""

    def __init__(self, initial_evs: Optional[List[EV]] = None) -> None:
        """Initialize EV Simulator.

        Args:
            initial_evs: Initial list of EV domain entities.
        """
        self._evs: Dict[str, EV] = {ev.id: ev for ev in (initial_evs or [])}

    @property
    def evs(self) -> List[EV]:
        """Return the current list of all simulated EVs."""
        return list(self._evs.values())

    def get_ev(self, ev_id: str) -> Optional[EV]:
        """Retrieve an EV by ID."""
        return self._evs.get(ev_id)

    def set_evs(self, evs: List[EV]) -> None:
        """Replace the entire EV fleet."""
        self._evs = {ev.id: ev for ev in evs}

    def add_or_update_ev(self, ev: EV) -> None:
        """Add or update an individual EV."""
        self._evs[ev.id] = ev

    def step(
        self,
        current_time: datetime,
        duration_seconds: float,
        allocations: Dict[str, float],
    ) -> List[EV]:
        """Simulate one time step for all vehicles applying the given power allocations.

        Args:
            current_time: Current simulation timestamp after advancing the clock.
            duration_seconds: Step interval in seconds (> 0).
            allocations: Mapping of EV ID -> allocated charging power in kW.

        Returns:
            Updated list of EV domain models.
        """
        if duration_seconds < 0.0:
            raise ValueError(f"duration_seconds must be non-negative (got {duration_seconds})")

        duration_hours = duration_seconds / 3600.0
        updated_fleet: Dict[str, EV] = {}

        # Validate allocation IDs
        for ev_id, power in allocations.items():
            if ev_id not in self._evs:
                raise ValueError(f"Unknown EV ID '{ev_id}' specified in power allocations")
            if power < 0.0:
                raise ValueError(f"Allocated power for '{ev_id}' cannot be negative ({power} kW)")
            ev = self._evs[ev_id]
            if power > ev.max_charging_power_kw:
                raise ValueError(
                    f"Allocated power ({power} kW) exceeds maximum charging power "
                    f"({ev.max_charging_power_kw} kW) for vehicle '{ev_id}'"
                )

        for ev_id, ev in self._evs.items():
            # 1. Check arrival / departure lifecycle boundaries
            if current_time < ev.arrival_time:
                # Vehicle has not arrived yet
                updated_fleet[ev_id] = EV(
                    id=ev.id,
                    slot_id=ev.slot_id,
                    battery_capacity_kwh=ev.battery_capacity_kwh,
                    soc_percent=ev.soc_percent,
                    target_soc_percent=ev.target_soc_percent,
                    max_charging_power_kw=ev.max_charging_power_kw,
                    arrival_time=ev.arrival_time,
                    departure_time=ev.departure_time,
                    allocated_power_kw=0.0,
                    status=EVStatus.WAITING,
                )
                continue

            if current_time >= ev.departure_time:
                # Vehicle has departed / disconnected
                updated_fleet[ev_id] = EV(
                    id=ev.id,
                    slot_id=None,
                    battery_capacity_kwh=ev.battery_capacity_kwh,
                    soc_percent=ev.soc_percent,
                    target_soc_percent=ev.target_soc_percent,
                    max_charging_power_kw=ev.max_charging_power_kw,
                    arrival_time=ev.arrival_time,
                    departure_time=ev.departure_time,
                    allocated_power_kw=0.0,
                    status=EVStatus.DISCONNECTED,
                )
                continue

            # 2. Check if already completed
            if ev.soc_percent >= ev.target_soc_percent:
                updated_fleet[ev_id] = EV(
                    id=ev.id,
                    slot_id=ev.slot_id,
                    battery_capacity_kwh=ev.battery_capacity_kwh,
                    soc_percent=ev.soc_percent,
                    target_soc_percent=ev.target_soc_percent,
                    max_charging_power_kw=ev.max_charging_power_kw,
                    arrival_time=ev.arrival_time,
                    departure_time=ev.departure_time,
                    allocated_power_kw=0.0,
                    status=EVStatus.COMPLETED,
                )
                continue

            # 3. Apply active allocation
            allocated_power = allocations.get(ev_id, 0.0)

            if allocated_power == 0.0:
                # Idle or paused
                new_status = EVStatus.PAUSED if ev.status == EVStatus.CHARGING else ev.status
                updated_fleet[ev_id] = EV(
                    id=ev.id,
                    slot_id=ev.slot_id,
                    battery_capacity_kwh=ev.battery_capacity_kwh,
                    soc_percent=ev.soc_percent,
                    target_soc_percent=ev.target_soc_percent,
                    max_charging_power_kw=ev.max_charging_power_kw,
                    arrival_time=ev.arrival_time,
                    departure_time=ev.departure_time,
                    allocated_power_kw=0.0,
                    status=new_status,
                )
                continue

            # Positive charging power application
            potential_energy_kwh = allocated_power * duration_hours
            energy_needed_kwh = ev.energy_required_kwh

            if potential_energy_kwh >= energy_needed_kwh:
                # Vehicle reaches target SoC during this step
                new_soc = ev.target_soc_percent
                new_status = EVStatus.COMPLETED
                effective_power = 0.0  # Finished charging
            else:
                delta_soc = (potential_energy_kwh / ev.battery_capacity_kwh) * 100.0
                new_soc = min(ev.target_soc_percent, round(ev.soc_percent + delta_soc, 4))
                new_status = EVStatus.CHARGING
                effective_power = allocated_power

            updated_fleet[ev_id] = EV(
                id=ev.id,
                slot_id=ev.slot_id,
                battery_capacity_kwh=ev.battery_capacity_kwh,
                soc_percent=new_soc,
                target_soc_percent=ev.target_soc_percent,
                max_charging_power_kw=ev.max_charging_power_kw,
                arrival_time=ev.arrival_time,
                departure_time=ev.departure_time,
                allocated_power_kw=effective_power,
                status=new_status,
            )

        self._evs = updated_fleet
        return self.evs
