"""Parking vision orchestrator service.

Connects camera frame replay engine, slot ROI extractor, occupancy classifier,
and temporal smoother to produce live parking vision state snapshots.
"""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import threading
from typing import Dict, List, Optional

from app.vision.models import (
    JoinedSlotState,
    ParkingVisionState,
    ParkingVisionSummary,
    ReplayStatus,
    SlotOccupancy,
)
from app.vision.occupancy import ComputerVisionOccupancyClassifier, OccupancyClassifier
from app.vision.replay import ReplayEngine
from app.vision.slots import SlotManager
from app.vision.smoothing import TemporalSmoother


class ParkingVisionService:
    """Thread-safe service managing camera vision occupancy pipeline and state."""

    def __init__(
        self,
        replay_engine: Optional[ReplayEngine] = None,
        slot_manager: Optional[SlotManager] = None,
        classifier: Optional[OccupancyClassifier] = None,
        smoother: Optional[TemporalSmoother] = None,
    ) -> None:
        self.slot_manager = slot_manager or SlotManager()
        self.replay_engine = replay_engine or ReplayEngine()
        self.classifier = classifier or ComputerVisionOccupancyClassifier()
        self.smoother = smoother or TemporalSmoother()

        self._lock = threading.Lock()
        self._cached_state: Optional[ParkingVisionState] = None

    def process_current_frame(self) -> ParkingVisionState:
        """Process the frame currently loaded in replay engine."""
        with self._lock:
            frame, frame_id, capture_time = self.replay_engine.get_current_frame()

            slot_results: List[SlotOccupancy] = []
            for slot_coord in self.slot_manager.slots:
                # 1. Crop slot ROI
                roi = self.slot_manager.crop_roi(frame, slot_coord)
                
                # 2. Predict raw occupancy
                raw_pred = self.classifier.predict(roi)

                # 3. Apply temporal state smoothing
                smoothed_result = self.smoother.process_prediction(slot_coord.slot_id, raw_pred)
                slot_results.append(smoothed_result)

            occupied_count = sum(1 for s in slot_results if s.occupied)
            total_count = len(slot_results)
            free_count = total_count - occupied_count

            summary = ParkingVisionSummary(
                total_slots=total_count,
                occupied_slots=occupied_count,
                free_slots=free_count,
            )

            state = ParkingVisionState(
                timestamp=datetime.now(timezone.utc),
                source_capture_time=capture_time,
                source="cnrpark_camera4_replay",
                camera_id="camera4",
                frame_id=frame_id,
                slots=slot_results,
                summary=summary,
            )

            self._cached_state = state
            return state

    def next_frame(self) -> ParkingVisionState:
        """Advance replay cursor to next frame and process it."""
        with self._lock:
            self.replay_engine.next_frame()
        return self.process_current_frame()

    def get_current_state(self) -> ParkingVisionState:
        """Retrieve current processed vision state (processing if cache empty)."""
        with self._lock:
            if self._cached_state is None:
                pass
        if self._cached_state is None:
            return self.process_current_frame()
        return self._cached_state

    def get_slot_occupancy(self, slot_id: str) -> Optional[SlotOccupancy]:
        """Lookup occupancy for a specific slot ID."""
        state = self.get_current_state()
        for slot in state.slots:
            if slot.slot_id == slot_id:
                return slot
        return None

    def control_replay(
        self, action: str, interval_seconds: Optional[float] = None
    ) -> ReplayStatus:
        """Execute replay playback control command (play, pause, reset, next)."""
        with self._lock:
            if interval_seconds is not None:
                self.replay_engine.set_interval(interval_seconds)

            action_clean = action.strip().lower()
            if action_clean == "play" or action_clean == "start":
                self.replay_engine.start()
            elif action_clean == "pause" or action_clean == "stop":
                self.replay_engine.pause()
            elif action_clean == "reset":
                self.replay_engine.reset()
                self.smoother.reset()
                self._cached_state = None
            elif action_clean == "next":
                self.replay_engine.next_frame()
                self._cached_state = None

            status = self.replay_engine.get_status()

        # Update cached state after action if cursor shifted
        if action_clean in ("reset", "next"):
            self.process_current_frame()

        return status

    def evaluate_joined_qr_state(
        self, ev_assignments: Dict[str, str]
    ) -> List[JoinedSlotState]:
        """Join physical vision occupancy with QR/driver session slot assignments.

        Args:
            ev_assignments: Dict mapping slot_id -> ev_id (e.g. {"606": "EV-023"})

        Returns:
            List of JoinedSlotState evaluating vision + session state consistency.
        """
        vision_state = self.get_current_state()
        slot_map = {s.slot_id: s for s in vision_state.slots}

        joined_results: List[JoinedSlotState] = []
        all_slot_ids = sorted(list(set(list(slot_map.keys()) + list(ev_assignments.keys()))))

        for slot_id in all_slot_ids:
            slot_vision = slot_map.get(slot_id)
            is_occupied = slot_vision.occupied if slot_vision else False
            confidence = slot_vision.confidence if slot_vision else 0.0

            assigned_ev = ev_assignments.get(slot_id)

            if assigned_ev and is_occupied:
                assessment = "normal_charging"
            elif assigned_ev and not is_occupied:
                assessment = "possible_departure"
            elif not assigned_ev and is_occupied:
                assessment = "unexpected_occupancy"
            else:
                assessment = "available"

            joined_results.append(
                JoinedSlotState(
                    slot_id=slot_id,
                    ev_id=assigned_ev,
                    slot_occupied=is_occupied,
                    confidence=confidence,
                    status_assessment=assessment,
                )
            )

        return joined_results


@lru_cache()
def get_parking_vision_service() -> ParkingVisionService:
    """Retrieve singleton ParkingVisionService instance."""
    return ParkingVisionService()
