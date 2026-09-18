"""Data models for parking vision, slot occupancy, replay status, and integration boundaries."""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SlotCoordinates(BaseModel):
    """Rescaled parking slot bounding box coordinates."""

    model_config = ConfigDict(frozen=True)

    slot_id: str = Field(..., description="Original slot ID from CNR dataset (e.g., '606').")
    x: int = Field(..., description="Rescaled X coordinate (top-left).")
    y: int = Field(..., description="Rescaled Y coordinate (top-left).")
    w: int = Field(..., description="Rescaled bounding box width.")
    h: int = Field(..., description="Rescaled bounding box height.")
    orig_x: int = Field(..., description="Original X coordinate in 2592x1944 space.")
    orig_y: int = Field(..., description="Original Y coordinate in 2592x1944 space.")
    orig_w: int = Field(..., description="Original width in 2592x1944 space.")
    orig_h: int = Field(..., description="Original height in 2592x1944 space.")


class SlotOccupancy(BaseModel):
    """Vision occupancy result for an individual parking slot."""

    model_config = ConfigDict(frozen=True)

    slot_id: str = Field(..., description="Unique parking slot identifier.")
    occupied: bool = Field(..., description="Physical occupancy status as detected by vision pipeline.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score (0.0 to 1.0).")


class ParkingVisionSummary(BaseModel):
    """Facility-wide parking vision summary metrics."""

    model_config = ConfigDict(frozen=True)

    total_slots: int = Field(..., ge=0, description="Total parking slots tracked by vision system.")
    occupied_slots: int = Field(..., ge=0, description="Count of physically occupied slots.")
    free_slots: int = Field(..., ge=0, description="Count of physically available slots.")


class ParkingVisionState(BaseModel):
    """Complete snapshot of physical parking lot occupancy state."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="System time when this vision state snapshot was processed.",
    )
    source_capture_time: str = Field(
        ..., description="Original dataset capture timestamp (e.g., '2016-01-12_0749')."
    )
    source: str = Field(
        default="cnrpark_camera4_replay",
        description="Data source identifier for this vision pipeline.",
    )
    camera_id: str = Field(
        default="camera4", description="Camera identifier supplying the frame stream."
    )
    frame_id: str = Field(..., description="Unique identifier or filename of current frame.")
    slots: List[SlotOccupancy] = Field(
        default_factory=list, description="Per-slot occupancy status list."
    )
    summary: ParkingVisionSummary = Field(
        ..., description="Aggregated slot statistics."
    )


class ReplayStatus(BaseModel):
    """Current state of the prerecorded frame replay engine."""

    model_config = ConfigDict(frozen=True)

    is_running: bool = Field(..., description="Whether frame replay auto-advancing is active.")
    current_frame_index: int = Field(..., ge=0, description="0-based index of current frame.")
    total_frames: int = Field(..., ge=0, description="Total frames available in replay dataset.")
    frame_id: str = Field(..., description="Filename/ID of currently loaded frame.")
    source_capture_time: str = Field(..., description="Capture timestamp of current frame.")
    replay_interval_seconds: float = Field(
        ..., gt=0.0, description="Delay between frame advances in auto-replay mode."
    )


class JoinedSlotState(BaseModel):
    """Combined integration view joining QR session allocation with physical vision occupancy."""

    model_config = ConfigDict(frozen=True)

    slot_id: str = Field(..., description="Parking slot identifier.")
    ev_id: Optional[str] = Field(None, description="Assigned EV ID from QR/driver session, if any.")
    slot_occupied: bool = Field(..., description="Physical occupancy status from vision module.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Vision detection confidence.")
    status_assessment: str = Field(
        ...,
        description=(
            "Derived operational state (e.g., 'normal_charging', 'available', "
            "'unexpected_occupancy', 'possible_departure', 'session_completed_occupied')"
        ),
    )
