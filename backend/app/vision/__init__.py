"""GridWise Parking Vision Package.

Provides camera frame replay, parking slot ROI extraction, occupancy detection,
temporal state smoothing, HighGUI live visual demonstration, and REST API integration boundaries.
"""

from app.vision.renderer import (
    COLOR_ASSIGNED_ACTIVE,
    COLOR_ASSIGNED_WAITING,
    COLOR_FREE,
    COLOR_OCCUPIED,
    ParkingVisionRenderer,
    normalize_slot_id,
)
from app.vision.highgui import (
    fetch_ev_assignments_from_api,
    fetch_ev_assignments_in_process,
    run_highgui_demo,
)

__all__ = [
    "COLOR_ASSIGNED_ACTIVE",
    "COLOR_ASSIGNED_WAITING",
    "COLOR_FREE",
    "COLOR_OCCUPIED",
    "ParkingVisionRenderer",
    "fetch_ev_assignments_from_api",
    "fetch_ev_assignments_in_process",
    "normalize_slot_id",
    "run_highgui_demo",
]
