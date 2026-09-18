"""Deterministic camera frame replay engine.

Sequences pre-recorded parking lot image frames from CNR-EXT Camera 4 dataset
to simulate a continuous camera feed without live hardware dependencies.
"""

from pathlib import Path
import threading
import time
from typing import List, Optional, Tuple
import cv2
import numpy as np

from app.vision.models import ReplayStatus


class ReplayEngine:
    """Manages sequential playback of pre-recorded camera frames."""

    def __init__(
        self,
        frames_dir: Optional[Path] = None,
        replay_interval_seconds: float = 1.0,
        loop: bool = True,
    ) -> None:
        if frames_dir is None:
            repo_root = Path(__file__).resolve().parents[3]
            frames_dir = (
                repo_root
                / "CNR-EXT_FULL_IMAGE_1000x750"
                / "FULL_IMAGE_1000x750"
                / "SUNNY"
                / "2016-01-12"
                / "camera4"
            )

        self.frames_dir = Path(frames_dir)
        self.replay_interval_seconds = max(0.1, float(replay_interval_seconds))
        self.loop = loop

        self._frame_paths: List[Path] = []
        self._current_index: int = 0
        self._is_running: bool = False
        self._cached_frames: dict[int, Tuple[np.ndarray, str, str]] = {}
        self._lock = threading.Lock()

        self._load_frame_manifest()

    def _load_frame_manifest(self) -> None:
        """Find and sort all .jpg image frame files in the target directory."""
        if not self.frames_dir.is_dir():
            raise FileNotFoundError(f"Frames directory not found: {self.frames_dir}")

        image_files = sorted([p for p in self.frames_dir.glob("*.jpg") if p.is_file()])
        if not image_files:
            raise FileNotFoundError(f"No .jpg image frames found in directory: {self.frames_dir}")

        self._frame_paths = image_files
        self._current_index = 0

    @property
    def total_frames(self) -> int:
        """Total number of frames available in replay manifest."""
        return len(self._frame_paths)

    @property
    def current_index(self) -> int:
        """Index of the currently active frame."""
        with self._lock:
            return self._current_index

    def _read_frame_at_index(self, index: int) -> Tuple[np.ndarray, str, str]:
        """Load image array and extract frame metadata at specified index."""
        if not (0 <= index < len(self._frame_paths)):
            raise IndexError(f"Frame index {index} out of bounds (0-{len(self._frame_paths)-1})")

        if index in self._cached_frames:
            return self._cached_frames[index]

        file_path = self._frame_paths[index]
        frame_id = file_path.stem  # e.g., "2016-01-12_0749"
        capture_time = frame_id  # e.g., "2016-01-12_0749"

        img = cv2.imread(str(file_path))
        if img is None:
            raise ValueError(f"Failed to decode image frame at path: {file_path}")

        result = (img, frame_id, capture_time)
        self._cached_frames[index] = result
        return result

    def get_current_frame(self) -> Tuple[np.ndarray, str, str]:
        """Retrieve current frame without advancing the playback cursor."""
        with self._lock:
            return self._read_frame_at_index(self._current_index)

    def next_frame(self) -> Tuple[np.ndarray, str, str]:
        """Advance playback index to the next frame and return its content."""
        with self._lock:
            if self.total_frames == 0:
                raise RuntimeError("Replay engine has no frames available")

            if self._current_index + 1 < self.total_frames:
                self._current_index += 1
            elif self.loop:
                self._current_index = 0

            return self._read_frame_at_index(self._current_index)

    def set_frame_index(self, index: int) -> Tuple[np.ndarray, str, str]:
        """Seek to a specific frame index."""
        with self._lock:
            if not (0 <= index < self.total_frames):
                raise ValueError(f"Invalid frame index {index}. Valid range: 0 to {self.total_frames - 1}")
            self._current_index = index
            return self._read_frame_at_index(self._current_index)

    def start(self) -> None:
        """Enable auto-advance replay state."""
        with self._lock:
            self._is_running = True

    def pause(self) -> None:
        """Pause auto-advance replay state."""
        with self._lock:
            self._is_running = False

    def reset(self) -> Tuple[np.ndarray, str, str]:
        """Reset playback cursor to the first frame (index 0)."""
        with self._lock:
            self._current_index = 0
            return self._read_frame_at_index(0)

    def set_interval(self, seconds: float) -> None:
        """Update playback interval timing."""
        with self._lock:
            self.replay_interval_seconds = max(0.1, float(seconds))

    def get_status(self) -> ReplayStatus:
        """Return current status overview of the replay engine."""
        with self._lock:
            _, frame_id, capture_time = self._read_frame_at_index(self._current_index)
            return ReplayStatus(
                is_running=self._is_running,
                current_frame_index=self._current_index,
                total_frames=self.total_frames,
                frame_id=frame_id,
                source_capture_time=capture_time,
                replay_interval_seconds=self.replay_interval_seconds,
            )
