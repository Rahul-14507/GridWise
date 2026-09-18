"""Parking slot coordinate loader and ROI extraction module.

Parses camera bounding box annotations from CSV and rescales coordinates from original
high-resolution space (2592x1944) to standard replay image dimensions (1000x750).
"""

import csv
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np

from app.vision.models import SlotCoordinates

ORIG_WIDTH = 2592
ORIG_HEIGHT = 1944
TARGET_WIDTH = 1000
TARGET_HEIGHT = 750


def rescale_coordinate(x: int, y: int, w: int, h: int) -> Tuple[int, int, int, int]:
    """Rescale coordinates from 2592x1944 space to 1000x750 space."""
    x_new = int(round(x * TARGET_WIDTH / ORIG_WIDTH))
    y_new = int(round(y * TARGET_HEIGHT / ORIG_HEIGHT))
    w_new = int(round(w * TARGET_WIDTH / ORIG_WIDTH))
    h_new = int(round(h * TARGET_HEIGHT / ORIG_HEIGHT))
    return x_new, y_new, w_new, h_new


class SlotManager:
    """Manages slot coordinates and ROI extraction from full camera frames."""

    def __init__(self, csv_path: Optional[Path] = None) -> None:
        if csv_path is None:
            # Default dataset path relative to repository root
            repo_root = Path(__file__).resolve().parents[3]
            csv_path = repo_root / "CNR-EXT_FULL_IMAGE_1000x750" / "camera4.csv"
        
        self.csv_path = Path(csv_path)
        self._slots: List[SlotCoordinates] = []
        self._slots_dict: Dict[str, SlotCoordinates] = {}
        self.load_slots()

    def load_slots(self) -> None:
        """Parse CSV file and generate rescaled slot bounding boxes."""
        if not self.csv_path.is_file():
            raise FileNotFoundError(f"Slot CSV file not found at: {self.csv_path}")

        slots = []
        slots_dict = {}
        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                slot_id = row["SlotId"].strip()
                orig_x = int(row["X"])
                orig_y = int(row["Y"])
                orig_w = int(row["W"])
                orig_h = int(row["H"])

                x_new, y_new, w_new, h_new = rescale_coordinate(orig_x, orig_y, orig_w, orig_h)
                
                slot_coord = SlotCoordinates(
                    slot_id=slot_id,
                    x=x_new,
                    y=y_new,
                    w=w_new,
                    h=h_new,
                    orig_x=orig_x,
                    orig_y=orig_y,
                    orig_w=orig_w,
                    orig_h=orig_h,
                )
                slots.append(slot_coord)
                slots_dict[slot_id] = slot_coord

        self._slots = slots
        self._slots_dict = slots_dict

    @property
    def slots(self) -> List[SlotCoordinates]:
        """Return list of all loaded slot coordinates."""
        return self._slots

    def get_slot(self, slot_id: str) -> Optional[SlotCoordinates]:
        """Retrieve slot coordinates by slot ID."""
        return self._slots_dict.get(slot_id)

    @staticmethod
    def crop_roi(frame: np.ndarray, slot: SlotCoordinates) -> np.ndarray:
        """Crop region of interest (ROI) for given slot from full frame array.
        
        Clamps bounding box coordinates safely to frame boundary dimensions.
        """
        img_h, img_w = frame.shape[:2]
        x1 = max(0, min(slot.x, img_w - 1))
        y1 = max(0, min(slot.y, img_h - 1))
        x2 = max(x1 + 1, min(slot.x + slot.w, img_w))
        y2 = max(y1 + 1, min(slot.y + slot.h, img_h))

        return frame[y1:y2, x1:x2]
