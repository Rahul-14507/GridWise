"""Temporal state smoothing for slot occupancy detection.

Filters raw single-frame vision predictions across consecutive frames to prevent
transient noise, shadow flickers, or temporary occlusions from causing instant state flips.
"""

from typing import Dict
from app.vision.models import SlotOccupancy
from app.vision.occupancy import OccupancyPrediction


class SlotStateHistory:
    """Tracks state history and confirmation counts for an individual slot."""

    def __init__(self, initial_occupied: bool = False, initial_confidence: float = 0.90) -> None:
        self.confirmed_occupied: bool = initial_occupied
        self.confirmed_confidence: float = initial_confidence
        self.pending_occupied: bool = initial_occupied
        self.consecutive_count: int = 0


class TemporalSmoother:
    """Applies temporal state confirmation rules across frame sequences."""

    def __init__(
        self,
        occupied_confirmation_frames: int = 2,
        free_confirmation_frames: int = 2,
    ) -> None:
        self.occupied_confirmation_frames = max(1, int(occupied_confirmation_frames))
        self.free_confirmation_frames = max(1, int(free_confirmation_frames))
        self._history: Dict[str, SlotStateHistory] = {}

    def process_prediction(
        self, slot_id: str, prediction: OccupancyPrediction
    ) -> SlotOccupancy:
        """Process raw slot prediction and return temporally smoothed slot state."""
        if slot_id not in self._history:
            self._history[slot_id] = SlotStateHistory(
                initial_occupied=prediction.occupied,
                initial_confidence=prediction.confidence,
            )

        hist = self._history[slot_id]
        raw_occupied = prediction.occupied
        raw_conf = prediction.confidence

        # Check if raw prediction matches current confirmed state
        if raw_occupied == hist.confirmed_occupied:
            # Confirmed state remains unchanged, update confidence with exponential moving average
            hist.confirmed_confidence = round(
                (hist.confirmed_confidence * 0.7) + (raw_conf * 0.3), 2
            )
            hist.pending_occupied = raw_occupied
            hist.consecutive_count = 0
        else:
            # Raw prediction differs from confirmed state
            if raw_occupied == hist.pending_occupied:
                hist.consecutive_count += 1
            else:
                hist.pending_occupied = raw_occupied
                hist.consecutive_count = 1

            # Required confirmation count depending on target state
            required_count = (
                self.occupied_confirmation_frames
                if raw_occupied
                else self.free_confirmation_frames
            )

            # Flip confirmed state once required consecutive frame count is reached
            if hist.consecutive_count >= required_count:
                hist.confirmed_occupied = raw_occupied
                hist.confirmed_confidence = raw_conf
                hist.consecutive_count = 0

        return SlotOccupancy(
            slot_id=slot_id,
            occupied=hist.confirmed_occupied,
            confidence=hist.confirmed_confidence,
        )

    def reset(self) -> None:
        """Reset state histories."""
        self._history.clear()
