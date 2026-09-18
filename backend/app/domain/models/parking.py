"""Parking domain models.

Represents parking slots and charging bay occupancy.
Computer vision / OpenCV tracking is not implemented in Milestone 1;
parking state is currently simulated.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ParkingSlot(BaseModel):
    """Represents a single designated EV parking / charging bay."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ...,
        min_length=1,
        description="Unique parking slot identifier (e.g. SLOT-01).",
    )
    occupied: bool = Field(
        default=False,
        description="Whether a vehicle currently occupies the physical parking slot.",
    )
    ev_id: Optional[str] = Field(
        default=None,
        description="Identifier of the parked vehicle, if occupied.",
    )
    charging: bool = Field(
        default=False,
        description="Whether the EV in this slot is actively drawing charge.",
    )

    @model_validator(mode="after")
    def validate_slot_consistency(self) -> "ParkingSlot":
        if self.occupied and self.ev_id is None:
            # Slot is marked occupied without specific EV ID or placeholder
            pass
        if not self.occupied and self.ev_id is not None:
            raise ValueError("Unoccupied slot cannot have an assigned ev_id")
        if not self.occupied and self.charging:
            raise ValueError("Unoccupied slot cannot be actively charging")
        return self


class ParkingState(BaseModel):
    """Aggregate facility parking status across all bays."""

    model_config = ConfigDict(frozen=True)

    total_slots: int = Field(
        ...,
        ge=0,
        description="Total number of physical parking slots in the facility.",
    )
    slots: List[ParkingSlot] = Field(
        default_factory=list,
        description="List of all individual parking slots.",
    )

    @property
    def occupied_slots(self) -> int:
        """Count of occupied slots."""
        return sum(1 for slot in self.slots if slot.occupied)

    @property
    def available_slots(self) -> int:
        """Count of available / unoccupied slots."""
        return len(self.slots) - self.occupied_slots

    def assign_ev(self, slot_id: str, ev_id: str) -> "ParkingState":
        """Returns a new ParkingState with the EV assigned to the specified slot."""
        updated_slots = []
        found = False
        for slot in self.slots:
            if slot.id == slot_id:
                found = True
                if slot.occupied:
                    raise ValueError(f"Slot '{slot_id}' is already occupied by '{slot.ev_id}'")
                updated_slots.append(
                    ParkingSlot(id=slot.id, occupied=True, ev_id=ev_id, charging=False)
                )
            else:
                updated_slots.append(slot)
        if not found:
            raise ValueError(f"Slot '{slot_id}' not found in parking state")
        return ParkingState(total_slots=self.total_slots, slots=updated_slots)

    def remove_ev(self, slot_id: str) -> "ParkingState":
        """Returns a new ParkingState with the specified slot vacated."""
        updated_slots = []
        found = False
        for slot in self.slots:
            if slot.id == slot_id:
                found = True
                updated_slots.append(
                    ParkingSlot(id=slot.id, occupied=False, ev_id=None, charging=False)
                )
            else:
                updated_slots.append(slot)
        if not found:
            raise ValueError(f"Slot '{slot_id}' not found in parking state")
        return ParkingState(total_slots=self.total_slots, slots=updated_slots)
