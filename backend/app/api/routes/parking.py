"""FastAPI REST routes for parking vision and frame replay integration."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.vision.models import (
    JoinedSlotState,
    ParkingVisionState,
    ReplayStatus,
    SlotOccupancy,
)
from app.vision.service import ParkingVisionService, get_parking_vision_service

router = APIRouter(prefix="/parking", tags=["Parking Vision"])


class ReplayControlRequest(BaseModel):
    """Payload for controlling frame replay playback state."""

    action: str = Field(
        ...,
        description="Replay command action: 'play', 'pause', 'reset', or 'next'.",
        json_schema_extra={"example": "next"},
    )
    interval_seconds: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Optional new replay interval delay in seconds.",
        json_schema_extra={"example": 1.0},
    )


class MockSessionAssignment(BaseModel):
    """Payload representing QR driver session slot assignments for testing the boundary."""

    ev_id: str = Field(..., description="Unique EV identifier (e.g. EV-023).")
    assigned_slot: str = Field(..., description="Target parking slot ID (e.g. 606).")


@router.get(
    "/state",
    response_model=ParkingVisionState,
    summary="Get parking vision occupancy state",
    description="Returns the physical parking-slot occupancy state evaluated from CNR-EXT Camera 4 replay frames.",
)
async def get_parking_vision_state(
    auto_advance: bool = Query(
        default=False,
        description="If True, automatically advances to next frame before returning state.",
    )
) -> ParkingVisionState:
    """Retrieve full facility parking vision state."""
    service = get_parking_vision_service()
    if auto_advance:
        return service.next_frame()
    return service.get_current_state()


@router.get(
    "/slots/{slot_id}",
    response_model=SlotOccupancy,
    summary="Get single parking slot vision status",
    description="Returns physical occupancy and confidence for a specific parking slot.",
)
async def get_slot_vision_status(slot_id: str) -> SlotOccupancy:
    """Retrieve single slot vision status."""
    service = get_parking_vision_service()
    slot_occupancy = service.get_slot_occupancy(slot_id)
    if slot_occupancy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parking slot '{slot_id}' not found in vision state",
        )
    return slot_occupancy


@router.post(
    "/replay/control",
    response_model=ReplayStatus,
    summary="Control frame replay engine",
    description="Start, pause, reset, or advance the prerecorded Camera 4 frame replay engine.",
)
async def control_frame_replay(payload: ReplayControlRequest) -> ReplayStatus:
    """Control frame replay execution."""
    service = get_parking_vision_service()
    try:
        return service.control_replay(
            action=payload.action, interval_seconds=payload.interval_seconds
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/combined",
    response_model=List[JoinedSlotState],
    summary="Get joined QR session + physical vision state",
    description=(
        "Evaluates integration boundary between QR driver session slot assignments "
        "and physical vision slot occupancy state."
    ),
)
async def get_joined_qr_vision_state(
    assignments: List[MockSessionAssignment],
) -> List[JoinedSlotState]:
    """Combine QR session EV assignments with vision slot state."""
    service = get_parking_vision_service()
    ev_map = {item.assigned_slot: item.ev_id for item in assignments}
    return service.evaluate_joined_qr_state(ev_map)
