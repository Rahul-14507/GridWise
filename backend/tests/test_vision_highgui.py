"""Tests for OpenCV HighGUI visual demonstration layer, renderer, and assignment bridge."""

from datetime import datetime, timezone
import json
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from app.vision.models import (
    ParkingVisionState,
    ParkingVisionSummary,
    ReplayStatus,
    SlotCoordinates,
    SlotOccupancy,
)
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
)


# =========================================================================
# Slot ID Normalization Tests
# =========================================================================

def test_normalize_slot_id_various_formats():
    """Verify that slot IDs across domains/datasets are normalized to canonical string."""
    assert normalize_slot_id("606") == "606"
    assert normalize_slot_id("SLOT-606") == "606"
    assert normalize_slot_id("BAY-606") == "606"
    assert normalize_slot_id("bay-606") == "606"
    assert normalize_slot_id("BAY-06") == "6"
    assert normalize_slot_id("  Slot-42  ") == "42"
    assert normalize_slot_id(606) == "606"
    assert normalize_slot_id(None) == "NONE"


# =========================================================================
# Renderer Tests (Headless np.ndarray generation)
# =========================================================================

@pytest.fixture
def base_frame():
    """Create a synthetic 1000x750 BGR test frame."""
    return np.zeros((750, 1000, 3), dtype=np.uint8)


@pytest.fixture
def sample_slots():
    """Create sample parking slot coordinate definitions."""
    return [
        SlotCoordinates(
            slot_id="606",
            x=100,
            y=100,
            w=80,
            h=60,
            orig_x=259,
            orig_y=259,
            orig_w=207,
            orig_h=155,
        ),
        SlotCoordinates(
            slot_id="607",
            x=200,
            y=100,
            w=80,
            h=60,
            orig_x=518,
            orig_y=259,
            orig_w=207,
            orig_h=155,
        ),
        SlotCoordinates(
            slot_id="608",
            x=300,
            y=100,
            w=80,
            h=60,
            orig_x=777,
            orig_y=259,
            orig_w=207,
            orig_h=155,
        ),
    ]


@pytest.fixture
def sample_vision_state():
    """Create sample ParkingVisionState with 3 slots."""
    return ParkingVisionState(
        source_capture_time="2016-01-12_1000",
        frame_id="frame_001.jpg",
        slots=[
            SlotOccupancy(slot_id="606", occupied=True, confidence=0.95),
            SlotOccupancy(slot_id="607", occupied=False, confidence=0.88),
            SlotOccupancy(slot_id="608", occupied=False, confidence=0.92),
        ],
        summary=ParkingVisionSummary(
            total_slots=3,
            occupied_slots=1,
            free_slots=2,
        ),
    )


@pytest.fixture
def sample_replay_status():
    """Create sample ReplayStatus."""
    return ReplayStatus(
        is_running=True,
        current_frame_index=5,
        total_frames=100,
        frame_id="frame_005.jpg",
        source_capture_time="2016-01-12_1130",
        replay_interval_seconds=1.0,
    )


def test_renderer_composite_canvas_dimensions(base_frame, sample_slots, sample_vision_state, sample_replay_status):
    """Ensure the renderer generates a composite image of shape (750, 1380, 3) and dtype uint8."""
    renderer = ParkingVisionRenderer()
    ev_assignments = {"606": "EV-023", "608": "EV-005"}

    rendered = renderer.render(
        frame=base_frame,
        slots=sample_slots,
        vision_state=sample_vision_state,
        ev_assignments=ev_assignments,
        replay_status=sample_replay_status,
        debug_mode=False,
    )

    assert rendered.shape == (750, 1380, 3)
    assert rendered.dtype == np.uint8
    assert np.any(rendered > 0)


def test_renderer_with_debug_mode_overlay(base_frame, sample_slots, sample_vision_state, sample_replay_status):
    """Test renderer execution with debug confidence overlay enabled."""
    renderer = ParkingVisionRenderer()
    rendered = renderer.render(
        frame=base_frame,
        slots=sample_slots,
        vision_state=sample_vision_state,
        ev_assignments={"606": "EV-023"},
        replay_status=sample_replay_status,
        debug_mode=True,
    )

    assert rendered.shape == (750, 1380, 3)
    assert rendered.dtype == np.uint8


def test_renderer_without_vision_state_or_replay(base_frame, sample_slots):
    """Renderer gracefully handles None vision_state and None replay_status."""
    renderer = ParkingVisionRenderer()
    rendered = renderer.render(
        frame=base_frame,
        slots=sample_slots,
        vision_state=None,
        ev_assignments={},
        replay_status=None,
        debug_mode=False,
    )

    assert rendered.shape == (750, 1380, 3)
    assert rendered.dtype == np.uint8


def test_renderer_resizes_arbitrary_resolution():
    """Renderer automatically resizes any incoming frame resolution to 1000x750."""
    renderer = ParkingVisionRenderer()
    odd_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    rendered = renderer.render(
        frame=odd_frame,
        slots=[],
        vision_state=None,
        ev_assignments={},
    )

    assert rendered.shape == (750, 1380, 3)


# =========================================================================
# API & In-Process Assignment Fetcher Tests
# =========================================================================

def test_fetch_ev_assignments_from_api_mocked():
    """Test polling EV assignments from mock HTTP endpoint."""
    fake_response_data = [
        {"id": "EV-023", "slot_id": 606, "status": "CHARGING"},
        {"id": "EV-005", "slot_id": "608", "status": "WAITING"},
        {"id": "EV-999", "slot_id": None, "status": "QUEUED"},
    ]
    
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(fake_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assignments = fetch_ev_assignments_from_api("http://testserver/api/v1")
        assert assignments is not None
        assert assignments.get("606") == "EV-023"
        assert assignments.get("608") == "EV-005"
        assert "None" not in assignments
        assert len(assignments) == 2


def test_fetch_ev_assignments_from_api_failure_returns_none():
    """Test API fetch returns None on connection error."""
    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        assignments = fetch_ev_assignments_from_api("http://nonexistent:9999/api/v1")
        assert assignments is None


def test_fetch_ev_assignments_in_process_mocked():
    """Test retrieving assignments directly from AppStateService in-process."""
    mock_ev1 = MagicMock()
    mock_ev1.id = "EV-023"
    mock_ev1.slot_id = "606"

    mock_ev2 = MagicMock()
    mock_ev2.id = "EV-999"
    mock_ev2.slot_id = None

    mock_service = MagicMock()
    mock_service.get_evs_detail.return_value = [mock_ev1, mock_ev2]

    with patch("app.vision.highgui.get_app_state_service", return_value=mock_service):
        assignments = fetch_ev_assignments_in_process()
        assert assignments.get("606") == "EV-023"
        assert len(assignments) == 1
