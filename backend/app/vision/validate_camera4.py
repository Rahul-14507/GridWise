"""Geometry validation script for Camera 4 parking slots.

Loads a sample Camera 4 frame, rescales slot bounding box coordinates from camera4.csv,
draws bounding box overlays with original SlotIds, and saves the output image to verify alignment.
"""

from pathlib import Path
import cv2
import numpy as np

from app.vision.slots import SlotManager, TARGET_WIDTH, TARGET_HEIGHT


def validate_camera4_geometry(
    frame_path: Path = None,
    csv_path: Path = None,
    output_path: Path = None,
) -> Path:
    """Draw slot overlays on a Camera 4 frame and save to output path."""
    repo_root = Path(__file__).resolve().parents[3]

    if csv_path is None:
        csv_path = repo_root / "CNR-EXT_FULL_IMAGE_1000x750" / "camera4.csv"

    if frame_path is None:
        frame_path = (
            repo_root
            / "CNR-EXT_FULL_IMAGE_1000x750"
            / "FULL_IMAGE_1000x750"
            / "SUNNY"
            / "2016-01-12"
            / "camera4"
            / "2016-01-12_0749.jpg"
        )

    if output_path is None:
        output_path = repo_root / "outputs" / "parking_vision" / "camera4_overlay.jpg"

    if not frame_path.is_file():
        raise FileNotFoundError(f"Sample frame image not found at: {frame_path}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load frame image
    image = cv2.imread(str(frame_path))
    if image is None:
        raise ValueError(f"Failed to read image at path: {frame_path}")

    # Verify frame size
    img_h, img_w = image.shape[:2]
    if (img_w, img_h) != (TARGET_WIDTH, TARGET_HEIGHT):
        # Resize to target resolution if needed
        image = cv2.resize(image, (TARGET_WIDTH, TARGET_HEIGHT))

    # 2. Load slot coordinates & rescale
    slot_manager = SlotManager(csv_path=csv_path)
    slots = slot_manager.slots

    # Create visual overlay
    annotated = image.copy()

    # Draw semi-transparent background overlay for visual readability
    overlay = annotated.copy()

    for slot in slots:
        x, y, w, h = slot.x, slot.y, slot.w, slot.h
        
        # Bounding box coordinates
        pt1 = (x, y)
        pt2 = (x + w, y + h)

        # Fill box with subtle highlight
        cv2.rectangle(overlay, pt1, pt2, (0, 220, 255), -1)

        # Draw box border
        cv2.rectangle(annotated, pt1, pt2, (0, 255, 0), 2)

        # Prepare label text
        label = f"S{slot.slot_id}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.4
        thickness = 1
        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        # Draw label background box
        lbl_bg_pt1 = (x, max(0, y - text_h - 4))
        lbl_bg_pt2 = (x + text_w + 4, y)
        cv2.rectangle(annotated, lbl_bg_pt1, lbl_bg_pt2, (0, 0, 0), -1)

        # Draw label text
        cv2.putText(
            annotated,
            label,
            (x + 2, y - 2 if y - text_h - 4 >= 0 else y + text_h + 2),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )

    # Blend transparent fill
    cv2.addWeighted(overlay, 0.15, annotated, 0.85, 0, annotated)

    # Add header banner
    banner_text = f"CNR-EXT Camera 4 - Slot Geometry Overlay ({len(slots)} slots mapped)"
    cv2.rectangle(annotated, (0, 0), (TARGET_WIDTH, 30), (30, 30, 30), -1)
    cv2.putText(
        annotated,
        banner_text,
        (10, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 255, 255),
        1,
        cv2.LINE_AA,
    )

    # Save output image
    success = cv2.imwrite(str(output_path), annotated)
    if not success:
        raise IOError(f"Failed to write output overlay image to: {output_path}")

    print(f"[OK] Successfully created Camera 4 slot overlay image:")
    print(f"   Input frame:  {frame_path}")
    print(f"   Output file:  {output_path}")
    print(f"   Total slots:  {len(slots)}")

    return output_path


if __name__ == "__main__":
    validate_camera4_geometry()
