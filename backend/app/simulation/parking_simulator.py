"""Parking Simulator.

Manages physical parking slot reservations and bay status synchronization.
Note: Computer Vision (OpenCV) will provide real occupancy in later milestones;
parking state is currently simulated.
"""

from typing import List, Optional
from app.domain.models.parking import ParkingSlot, ParkingState
from app.domain.models.ev import EV, EVStatus


class ParkingSimulator:
    """Maintains and updates parking bay occupancy and slot allocations."""

    def __init__(self, initial_state: Optional[ParkingState] = None) -> None:
        """Initialize Parking Simulator.

        Args:
            initial_state: Initial ParkingState or default 4-bay configuration.
        """
        if initial_state is not None:
            self._state = initial_state
        else:
            slots = [
                ParkingSlot(id="SLOT-01", occupied=False),
                ParkingSlot(id="SLOT-02", occupied=False),
                ParkingSlot(id="SLOT-03", occupied=False),
                ParkingSlot(id="SLOT-04", occupied=False),
            ]
            self._state = ParkingState(total_slots=len(slots), slots=slots)

    @property
    def state(self) -> ParkingState:
        """Return the current ParkingState."""
        return self._state

    def set_state(self, state: ParkingState) -> None:
        """Set or replace current parking state."""
        self._state = state

    def sync_with_evs(self, evs: List[EV]) -> ParkingState:
        """Synchronize parking slot occupancies and active charging flags with the EV fleet list."""
        ev_map = {ev.slot_id: ev for ev in evs if ev.slot_id is not None}
        updated_slots: List[ParkingSlot] = []

        for slot in self._state.slots:
            if slot.id in ev_map:
                ev = ev_map[slot.id]
                is_charging = ev.status == EVStatus.CHARGING and ev.allocated_power_kw > 0.0
                is_connected = ev.status != EVStatus.DISCONNECTED
                if is_connected:
                    updated_slots.append(
                        ParkingSlot(
                            id=slot.id,
                            occupied=True,
                            ev_id=ev.id,
                            charging=is_charging,
                        )
                    )
                else:
                    updated_slots.append(
                        ParkingSlot(id=slot.id, occupied=False, ev_id=None, charging=False)
                    )
            else:
                updated_slots.append(
                    ParkingSlot(id=slot.id, occupied=False, ev_id=None, charging=False)
                )

        self._state = ParkingState(total_slots=self._state.total_slots, slots=updated_slots)
        return self._state

    def assign_slot(self, slot_id: str, ev_id: str) -> ParkingState:
        """Assign an EV to a specific parking slot."""
        self._state = self._state.assign_ev(slot_id, ev_id)
        return self._state

    def vacate_slot(self, slot_id: str) -> ParkingState:
        """Vacate an assigned parking slot."""
        self._state = self._state.remove_ev(slot_id)
        return self._state
