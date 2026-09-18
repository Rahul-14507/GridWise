"""Comprehensive test suite for parking vision, slot ROI extraction, replay engine,
occupancy classification, temporal smoothing, and REST API endpoints.
"""

from pathlib import Path
import pytest
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.vision.models import (
    JoinedSlotState,
    ParkingVisionState,
    ReplayStatus,
    SlotCoordinates,
    SlotOccupancy,
)
from app.vision.occupancy import (
    ComputerVisionOccupancyClassifier,
    MockOccupancyClassifier,
    OccupancyPrediction,
)
from app.vision.replay import ReplayEngine
from app.vision.slots import SlotManager, rescale_coordinate
from app.vision.smoothing import TemporalSmoother
from app.vision.service import ParkingVisionService


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Slot Coordinate Rescaling Tests
# ---------------------------------------------------------------------------
def test_coordinate_rescaling():
    """Verify coordinate rescaling math from 2592x1944 to 1000x750."""
    # Slot 606: 2114, 1556, 380, 380
    x, y, w, h = rescale_coordinate(2114, 1556, 380, 380)
    assert x == int(round(2114 * 1000 / 2592))
    assert y == int(round(1556 * 750 / 1944))
    assert w == int(round(380 * 1000 / 2592))
    assert h == int(round(380 * 750 / 1944))
    assert x == 816
    assert y == 600


def test_slot_manager_csv_loading():
    """Verify SlotManager correctly parses camera4.csv."""
    slot_manager = SlotManager()
    slots = slot_manager.slots
    assert len(slots) == 37

    slot_606 = slot_manager.get_slot("606")
    assert slot_606 is not None
    assert slot_606.slot_id == "606"
    assert slot_606.orig_x == 2114
    assert slot_606.x == 816
    assert slot_606.y == 600


def test_roi_cropping_bounds():
    """Verify ROI cropping handles boundary limits safely."""
    dummy_frame = np.zeros((750, 1000, 3), dtype=np.uint8)
    slot = SlotCoordinates(
        slot_id="test",
        x=950,
        y=700,
        w=100,
        h=100,
        orig_x=2400,
        orig_y=1800,
        orig_w=200,
        orig_h=200,
    )
    roi = SlotManager.crop_roi(dummy_frame, slot)
    assert roi.shape[0] == 50  # 700 to 750
    assert roi.shape[1] == 50  # 950 to 1000


# ---------------------------------------------------------------------------
# 2. Replay Engine Tests
# ---------------------------------------------------------------------------
def test_replay_engine_manifest_and_stepping():
    """Verify ReplayEngine sequence loading and next_frame advancing."""
    engine = ReplayEngine()
    assert engine.total_frames == 20

    img1, frame_id1, capture_time1 = engine.get_current_frame()
    assert frame_id1 == "2016-01-12_0749"
    assert img1.shape == (750, 1000, 3)

    img2, frame_id2, capture_time2 = engine.next_frame()
    assert frame_id2 == "2016-01-12_0819"
    assert engine.current_index == 1

    engine.reset()
    assert engine.current_index == 0


def test_replay_engine_control_status():
    """Verify status response and controls."""
    engine = ReplayEngine()
    engine.start()
    status = engine.get_status()
    assert status.is_running is True
    assert status.total_frames == 20

    engine.pause()
    assert engine.get_status().is_running is False


# ---------------------------------------------------------------------------
# 3. Occupancy Classifier Tests
# ---------------------------------------------------------------------------
def test_cv_occupancy_classifier_empty_roi():
    """Verify CV classifier returns low score for uniform empty surface."""
    empty_roi = np.full((100, 100, 3), 120, dtype=np.uint8)
    classifier = ComputerVisionOccupancyClassifier()
    pred = classifier.predict(empty_roi)
    assert isinstance(pred, OccupancyPrediction)
    assert pred.occupied is False
    assert 0.0 <= pred.confidence <= 1.0


def test_cv_occupancy_classifier_textured_roi():
    """Verify CV classifier detects high edge contrast as occupied."""
    # Create high-contrast checkerboard image simulating vehicle details
    textured_roi = np.zeros((100, 100, 3), dtype=np.uint8)
    textured_roi[::2, ::2] = 255
    textured_roi[1::2, 1::2] = 255
    classifier = ComputerVisionOccupancyClassifier(combined_threshold=0.20)
    pred = classifier.predict(textured_roi)
    assert pred.occupied is True
    assert pred.confidence >= 0.60


def test_mock_classifier():
    """Verify mock classifier fixture interface."""
    mock_cls = MockOccupancyClassifier(default_occupied=True, confidence=0.95)
    roi = np.zeros((50, 50, 3), dtype=np.uint8)
    pred = mock_cls.predict(roi)
    assert pred.occupied is True
    assert pred.confidence == 0.95


# ---------------------------------------------------------------------------
# 4. Temporal State Smoothing Tests
# ---------------------------------------------------------------------------
def test_temporal_smoother_prevents_single_frame_flicker():
    """Verify N consecutive frames are required before state flips."""
    smoother = TemporalSmoother(
        occupied_confirmation_frames=2, free_confirmation_frames=2
    )
    slot_id = "606"

    # Frame 1: FREE
    s1 = smoother.process_prediction(slot_id, OccupancyPrediction(occupied=False, confidence=0.90))
    assert s1.occupied is False

    # Frame 2: Single OCCUPIED glitch -> should remain FREE
    s2 = smoother.process_prediction(slot_id, OccupancyPrediction(occupied=True, confidence=0.85))
    assert s2.occupied is False

    # Frame 3: Second consecutive OCCUPIED -> state flips to OCCUPIED
    s3 = smoother.process_prediction(slot_id, OccupancyPrediction(occupied=True, confidence=0.88))
    assert s3.occupied is True


# ---------------------------------------------------------------------------
# 5. Parking Vision Service & Integration Tests
# ---------------------------------------------------------------------------
def test_parking_vision_service_pipeline():
    """Test orchestration of frame processing, slot iteration, and summary."""
    service = ParkingVisionService()
    state = service.process_current_frame()

    assert isinstance(state, ParkingVisionState)
    assert state.camera_id == "camera4"
    assert len(state.slots) == 37
    assert state.summary.total_slots == 37
    assert state.summary.occupied_slots + state.summary.free_slots == 37


def test_evaluate_joined_qr_state():
    """Verify QR session assignment boundary joined with vision occupancy."""
    service = ParkingVisionService()
    assignments = {"606": "EV-023", "192": "EV-099"}
    joined = service.evaluate_joined_qr_state(assignments)

    assert len(joined) == 37
    slot_606 = next(s for s in joined if s.slot_id == "606")
    assert slot_606.ev_id == "EV-023"
    assert slot_606.status_assessment in ("normal_charging", "possible_departure")


# ---------------------------------------------------------------------------
# 6. REST API Endpoint Integration Tests
# ---------------------------------------------------------------------------
def test_api_get_parking_state(client):
    """GET /api/v1/parking/state returns valid ParkingVisionState JSON."""
    response = client.get("/api/v1/parking/state")
    assert response.status_code == 200
    data = response.json()
    assert data["camera_id"] == "camera4"
    assert data["source"] == "cnrpark_camera4_replay"
    assert len(data["slots"]) == 37
    assert data["summary"]["total_slots"] == 37


def test_api_get_single_slot(client):
    """GET /api/v1/parking/slots/{slot_id} returns single slot occupancy."""
    response = client.get("/api/v1/parking/slots/606")
    assert response.status_code == 200
    data = response.json()
    assert data["slot_id"] == "606"
    assert "occupied" in data
    assert "confidence" in data


def test_api_get_single_slot_not_found(client):
    """GET /api/v1/parking/slots/invalid returns 404."""
    response = client.get("/api/v1/parking/slots/999999")
    assert response.status_code == 404


def test_api_replay_control(client):
    """POST /api/v1/parking/replay/control executes playback commands."""
    response = client.post(
        "/api/v1/parking/replay/control",
        json={"action": "next", "interval_seconds": 1.5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["replay_interval_seconds"] == 1.5
    assert data["current_frame_index"] == 1


def test_api_joined_state(client):
    """POST /api/v1/parking/combined joins QR sessions with physical occupancy."""
    payload = [
        {"ev_id": "EV-023", "assigned_slot": "606"},
        {"ev_id": "EV-045", "assigned_slot": "192"},
    ]
    response = client.post("/api/v1/parking/combined", json=payload)
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) == 37
