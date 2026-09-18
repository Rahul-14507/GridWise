"""Tests for Parking domain models."""

import pytest
from pydantic import ValidationError

from app.domain.models.parking import ParkingSlot, ParkingState


def test_parking_slot_valid():
    """Verify standard parking slot creation."""
    slot = ParkingSlot(id="SLOT-01", occupied=True, ev_id="EV-001", charging=True)
    assert slot.id == "SLOT-01"
    assert slot.occupied is True
    assert slot.ev_id == "EV-001"
    assert slot.charging is True


def test_parking_slot_unoccupied_with_ev_id_rejected():
    """Verify unoccupied slot cannot have an assigned ev_id."""
    with pytest.raises(ValidationError):
        ParkingSlot(id="SLOT-01", occupied=False, ev_id="EV-001")


def test_parking_slot_unoccupied_charging_rejected():
    """Verify unoccupied slot cannot be actively charging."""
    with pytest.raises(ValidationError):
        ParkingSlot(id="SLOT-01", occupied=False, charging=True)


def test_parking_state_metrics():
    """Verify available and occupied slot calculations."""
    slots = [
        ParkingSlot(id="SLOT-01", occupied=True, ev_id="EV-001", charging=True),
        ParkingSlot(id="SLOT-02", occupied=True, ev_id="EV-002", charging=False),
        ParkingSlot(id="SLOT-03", occupied=False),
        ParkingSlot(id="SLOT-04", occupied=False),
    ]
    state = ParkingState(total_slots=4, slots=slots)
    assert state.total_slots == 4
    assert state.occupied_slots == 2
    assert state.available_slots == 2


def test_parking_state_assign_and_remove_ev():
    """Verify assigning and vacating slots via immutable updates."""
    initial_slots = [
        ParkingSlot(id="SLOT-01", occupied=False),
        ParkingSlot(id="SLOT-02", occupied=False),
    ]
    state = ParkingState(total_slots=2, slots=initial_slots)
    assert state.available_slots == 2

    # Assign EV-001 to SLOT-01
    assigned_state = state.assign_ev("SLOT-01", "EV-001")
    assert assigned_state.occupied_slots == 1
    assert assigned_state.available_slots == 1
    assert assigned_state.slots[0].occupied is True
    assert assigned_state.slots[0].ev_id == "EV-001"

    # Vacate SLOT-01
    vacated_state = assigned_state.remove_ev("SLOT-01")
    assert vacated_state.occupied_slots == 0
    assert vacated_state.available_slots == 2
    assert vacated_state.slots[0].occupied is False
    assert vacated_state.slots[0].ev_id is None


def test_parking_state_assign_to_occupied_slot_fails():
    """Verify assigning an EV to an already occupied slot raises ValueError."""
    slots = [
        ParkingSlot(id="SLOT-01", occupied=True, ev_id="EV-001"),
    ]
    state = ParkingState(total_slots=1, slots=slots)
    with pytest.raises(ValueError) as exc_info:
        state.assign_ev("SLOT-01", "EV-002")
    assert "already occupied" in str(exc_info.value)
