"""HighGUI frame renderer and HUD compositor for GridWise parking vision.

Renders Camera 4 parking lot frames, slot bounding boxes with status-dependent visual styling,
and an integrated HUD side panel displaying real-time session assignments and telemetry.
"""

from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from app.vision.models import (
    ParkingVisionState,
    ReplayStatus,
    SlotCoordinates,
    SlotOccupancy,
)

# Visual Theme Color Palette (BGR format for OpenCV)
COLOR_BG_DARK = (20, 20, 26)          # Dark slate background
COLOR_PANEL_BG = (28, 28, 38)         # Information panel background
COLOR_CARD_BG = (38, 38, 52)          # Section card background
COLOR_CARD_BORDER = (55, 55, 75)      # Card outline
COLOR_TEXT_PRIMARY = (245, 245, 250)  # Primary text (white)
COLOR_TEXT_MUTED = (150, 150, 170)    # Secondary muted text
COLOR_TEXT_ACCENT = (255, 190, 60)    # Accent / cyan text

# Slot State Colors (BGR)
COLOR_FREE = (90, 180, 90)            # Muted green (Unoccupied)
COLOR_OCCUPIED = (60, 60, 210)        # Red/crimson (Occupied by general car)
COLOR_ASSIGNED_WAITING = (40, 190, 240)  # Amber/gold (Assigned EV not yet parked)
COLOR_ASSIGNED_ACTIVE = (80, 220, 100)   # Vivid emerald green (Assigned EV parked & verified)


def normalize_slot_id(raw_id: str) -> str:
    """Normalize slot ID string for reliable cross-referencing.
    
    Handles '606', 'SLOT-606', 'BAY-606', 'bay-606', 'BAY-06' -> '606'.
    """
    clean = str(raw_id).strip().upper()
    for prefix in ("SLOT-", "SLOT_", "BAY-", "BAY_", "SLOT", "BAY"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):].strip()
    # Strip leading zero if it makes it numeric (e.g. '06' -> '6' or '023' -> '23')
    if clean.isdigit():
        return str(int(clean))
    return clean


class ParkingVisionRenderer:
    """Composites parking frames with visual bounding boxes and HUD panels."""

    HUD_WIDTH = 380
    TARGET_HEIGHT = 750
    TARGET_FRAME_WIDTH = 1000

    def __init__(self) -> None:
        pass

    def render(
        self,
        frame: np.ndarray,
        slots: List[SlotCoordinates],
        vision_state: Optional[ParkingVisionState],
        ev_assignments: Dict[str, str],
        replay_status: Optional[ReplayStatus] = None,
        debug_mode: bool = False,
    ) -> np.ndarray:
        """Compose the complete HighGUI visual display.
        
        Args:
            frame: Raw BGR image frame (typically 1000x750).
            slots: List of physical slot bounding box definitions.
            vision_state: Current processed parking vision snapshot (occupancy + confidence).
            ev_assignments: Mapping of slot_id -> ev_id (e.g. {'606': 'EV-023'}).
            replay_status: Current replay engine playback telemetry.
            debug_mode: If True, renders raw confidence percentages on all slots.

        Returns:
            Composite BGR numpy array ready for cv2.imshow().
        """
        # Ensure frame is standard dimensions
        h, w = frame.shape[:2]
        if (w, h) != (self.TARGET_FRAME_WIDTH, self.TARGET_HEIGHT):
            frame_resized = cv2.resize(frame, (self.TARGET_FRAME_WIDTH, self.TARGET_HEIGHT))
        else:
            frame_resized = frame.copy()

        # Build lookup maps
        normalized_ev_map: Dict[str, str] = {}
        for slot_k, ev_v in ev_assignments.items():
            norm_k = normalize_slot_id(slot_k)
            normalized_ev_map[norm_k] = ev_v

        occupancy_map: Dict[str, SlotOccupancy] = {}
        if vision_state:
            for s in vision_state.slots:
                occupancy_map[normalize_slot_id(s.slot_id)] = s

        # 1. Render parking slot overlays on camera frame
        annotated_frame = self._draw_slot_overlays(
            frame=frame_resized,
            slots=slots,
            occupancy_map=occupancy_map,
            normalized_ev_map=normalized_ev_map,
            debug_mode=debug_mode,
        )

        # 2. Render right-hand HUD panel
        hud_panel = self._draw_hud_panel(
            vision_state=vision_state,
            replay_status=replay_status,
            ev_assignments=ev_assignments,
            occupancy_map=occupancy_map,
            normalized_ev_map=normalized_ev_map,
            debug_mode=debug_mode,
        )

        # 3. Concatenate side-by-side: [Camera Frame | HUD Panel]
        combined_canvas = np.hstack([annotated_frame, hud_panel])

        # 4. Render top banner header over the canvas
        return combined_canvas

    def _draw_slot_overlays(
        self,
        frame: np.ndarray,
        slots: List[SlotCoordinates],
        occupancy_map: Dict[str, SlotOccupancy],
        normalized_ev_map: Dict[str, str],
        debug_mode: bool,
    ) -> np.ndarray:
        """Draw bounding boxes and status labels for all slots."""
        canvas = frame.copy()
        overlay = frame.copy()

        # Sort slots so assigned slots are drawn LAST (on top)
        sorted_slots = sorted(
            slots,
            key=lambda s: 1 if normalize_slot_id(s.slot_id) in normalized_ev_map else 0
        )

        for slot in sorted_slots:
            norm_id = normalize_slot_id(slot.slot_id)
            occ_info = occupancy_map.get(norm_id)
            is_occupied = occ_info.occupied if occ_info else False
            confidence = occ_info.confidence if occ_info else 0.0

            assigned_ev = normalized_ev_map.get(norm_id)
            is_assigned = assigned_ev is not None

            # Determine visual state category
            if is_assigned and is_occupied:
                state_color = COLOR_ASSIGNED_ACTIVE
                state_label = "ASSIGNED + OCCUPIED"
                border_thickness = 3
            elif is_assigned and not is_occupied:
                state_color = COLOR_ASSIGNED_WAITING
                state_label = "ASSIGNED (WAITING)"
                border_thickness = 3
            elif is_occupied:
                state_color = COLOR_OCCUPIED
                state_label = "OCCUPIED"
                border_thickness = 2
            else:
                state_color = COLOR_FREE
                state_label = "FREE"
                border_thickness = 1

            x1, y1 = slot.x, slot.y
            x2, y2 = slot.x + slot.w, slot.y + slot.h

            # Draw semi-transparent fill for occupied / assigned slots
            if is_assigned or is_occupied:
                fill_alpha = 0.22 if is_assigned else 0.12
                cv2.rectangle(overlay, (x1, y1), (x2, y2), state_color, -1)
                cv2.addWeighted(overlay, fill_alpha, canvas, 1 - fill_alpha, 0, canvas)

            # Draw main bounding box
            cv2.rectangle(canvas, (x1, y1), (x2, y2), state_color, border_thickness)

            # Draw corner brackets for assigned slots
            if is_assigned:
                corner_len = min(15, slot.w // 3, slot.h // 3)
                # Top-left
                cv2.line(canvas, (x1, y1), (x1 + corner_len, y1), state_color, 4)
                cv2.line(canvas, (x1, y1), (x1, y1 + corner_len), state_color, 4)
                # Top-right
                cv2.line(canvas, (x2, y1), (x2 - corner_len, y1), state_color, 4)
                cv2.line(canvas, (x2, y1), (x2, y1 + corner_len), state_color, 4)
                # Bottom-left
                cv2.line(canvas, (x1, y2), (x1 + corner_len, y2), state_color, 4)
                cv2.line(canvas, (x1, y2), (x1, y2 - corner_len), state_color, 4)
                # Bottom-right
                cv2.line(canvas, (x2, y2), (x2 - corner_len, y2), state_color, 4)
                cv2.line(canvas, (x2, y2), (x2, y2 - corner_len), state_color, 4)

            # Slot Label Tag
            if is_assigned:
                # Prominent callout card for assigned slot
                tag_w = max(130, len(assigned_ev) * 12 + 40)
                tag_h = 44
                tag_x = max(5, min(x1, canvas.shape[1] - tag_w - 5))
                tag_y = max(tag_h + 5, y1 - 6)

                # Tag background
                cv2.rectangle(canvas, (tag_x, tag_y - tag_h), (tag_x + tag_w, tag_y), COLOR_PANEL_BG, -1)
                cv2.rectangle(canvas, (tag_x, tag_y - tag_h), (tag_x + tag_w, tag_y), state_color, 2)

                # Line 1: EV-ID -> Slot ID
                txt1 = f"{assigned_ev} -> Slot {slot.slot_id}"
                cv2.putText(canvas, txt1, (tag_x + 6, tag_y - tag_h + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_TEXT_PRIMARY, 1, cv2.LINE_AA)

                # Line 2: OCCUPIED / WAITING status
                if is_occupied:
                    conf_str = f" ({confidence:.0%})" if occ_info else ""
                    txt2 = f"OCCUPIED{conf_str}"
                else:
                    txt2 = "WAITING / EMPTY"
                cv2.putText(canvas, txt2, (tag_x + 6, tag_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, state_color, 1, cv2.LINE_AA)

                # Pointer connector line
                cv2.line(canvas, (tag_x + tag_w // 2, tag_y), (x1 + slot.w // 2, y1), state_color, 2)
            else:
                # Compact label for standard unassigned slots
                lbl_text = f"{slot.slot_id}"
                if debug_mode and occ_info:
                    lbl_text += f":{int(confidence * 100)}%"
                
                font_scale = 0.35
                (txt_w, txt_h), _ = cv2.getTextSize(lbl_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
                
                lbl_x = x1 + 2
                lbl_y = y1 + txt_h + 2
                if lbl_y < canvas.shape[0]:
                    cv2.rectangle(canvas, (lbl_x - 1, y1), (lbl_x + txt_w + 2, y1 + txt_h + 4), (15, 15, 20), -1)
                    cv2.putText(canvas, lbl_text, (lbl_x, lbl_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, state_color, 1, cv2.LINE_AA)

        return canvas

    def _draw_hud_panel(
        self,
        vision_state: Optional[ParkingVisionState],
        replay_status: Optional[ReplayStatus],
        ev_assignments: Dict[str, str],
        occupancy_map: Dict[str, SlotOccupancy],
        normalized_ev_map: Dict[str, str],
        debug_mode: bool,
    ) -> np.ndarray:
        """Render the telemetry HUD side panel."""
        hud = np.zeros((self.TARGET_HEIGHT, self.HUD_WIDTH, 3), dtype=np.uint8)
        hud[:] = COLOR_PANEL_BG

        y = 24

        # 1. Main Header Title
        cv2.putText(hud, "GRIDWISE PARKING VISION", (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, COLOR_TEXT_PRIMARY, 2, cv2.LINE_AA)
        y += 18
        cv2.putText(hud, "Real-Time OpenCV Slot Detection", (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
        y += 14
        cv2.line(hud, (16, y), (self.HUD_WIDTH - 16, y), COLOR_CARD_BORDER, 1)
        y += 16

        # 2. System Telemetry Card
        camera_id = vision_state.camera_id.upper() if vision_state else "CAMERA 4"
        source_mode = "CNR-EXT Historical Replay" if vision_state else "Replay Stream"
        capture_time = vision_state.source_capture_time if vision_state else "N/A"
        frame_id = vision_state.frame_id if vision_state else "0000"

        total_slots = vision_state.summary.total_slots if vision_state else len(occupancy_map)
        occupied_slots = vision_state.summary.occupied_slots if vision_state else sum(1 for s in occupancy_map.values() if s.occupied)
        free_slots = vision_state.summary.free_slots if vision_state else max(0, total_slots - occupied_slots)

        card_h = 108
        self._draw_card_box(hud, 16, y, self.HUD_WIDTH - 32, card_h, "CAMERA & TELEMETRY")
        cy = y + 26
        cv2.putText(hud, f"Camera: {camera_id}", (26, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_TEXT_PRIMARY, 1, cv2.LINE_AA)
        cy += 18
        cv2.putText(hud, f"Source: {source_mode}", (26, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.38, COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
        cy += 18
        cv2.putText(hud, f"Capture: {capture_time}", (26, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.38, COLOR_TEXT_ACCENT, 1, cv2.LINE_AA)
        cy += 18
        slot_metric_str = f"Slots: {total_slots} | Occupied: {occupied_slots} | Free: {free_slots}"
        cv2.putText(hud, slot_metric_str, (26, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLOR_TEXT_PRIMARY, 1, cv2.LINE_AA)
        y += card_h + 14

        # 3. Active QR / Backend EV Assignments Card
        assigned_count = len(normalized_ev_map)
        ev_card_h = max(110, 36 + assigned_count * 26)
        self._draw_card_box(hud, 16, y, self.HUD_WIDTH - 32, ev_card_h, f"ACTIVE EV SESSIONS ({assigned_count})")
        ey = y + 26

        if assigned_count == 0:
            cv2.putText(hud, "No active EV check-ins.", (26, ey + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
            cv2.putText(hud, "Scan QR code to assign bay.", (26, ey + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.38, COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
        else:
            for norm_slot, ev_id in list(normalized_ev_map.items())[:5]:
                occ = occupancy_map.get(norm_slot)
                is_occ = occ.occupied if occ else False
                st_color = COLOR_ASSIGNED_ACTIVE if is_occ else COLOR_ASSIGNED_WAITING
                st_text = "OCCUPIED" if is_occ else "WAITING"
                
                # Render EV -> Slot row
                cv2.putText(hud, f"{ev_id} -> Slot {norm_slot}", (26, ey), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_TEXT_PRIMARY, 1, cv2.LINE_AA)
                cv2.putText(hud, f"[{st_text}]", (self.HUD_WIDTH - 110, ey), cv2.FONT_HERSHEY_SIMPLEX, 0.40, st_color, 1, cv2.LINE_AA)
                ey += 24

        y += ev_card_h + 14

        # 4. Primary Assigned Slot Highlight Card
        primary_assigned_slot = next(iter(normalized_ev_map.keys()), None)
        primary_ev = normalized_ev_map.get(primary_assigned_slot) if primary_assigned_slot else None
        
        focus_h = 135
        self._draw_card_box(hud, 16, y, self.HUD_WIDTH - 32, focus_h, "ASSIGNMENT VERIFICATION")
        fy = y + 26

        if primary_assigned_slot and primary_ev:
            occ = occupancy_map.get(primary_assigned_slot)
            is_occ = occ.occupied if occ else False
            conf = occ.confidence if occ else 0.0

            cv2.putText(hud, f"Vehicle: {primary_ev}", (26, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.46, COLOR_TEXT_PRIMARY, 1, cv2.LINE_AA)
            fy += 20
            cv2.putText(hud, f"Assigned Bay: Slot {primary_assigned_slot}", (26, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.44, COLOR_TEXT_PRIMARY, 1, cv2.LINE_AA)
            fy += 24

            # Big status badge
            badge_color = COLOR_ASSIGNED_ACTIVE if is_occ else COLOR_ASSIGNED_WAITING
            badge_title = "PHYSICALLY OCCUPIED" if is_occ else "AWAITING VEHICLE"
            
            cv2.rectangle(hud, (26, fy - 14), (self.HUD_WIDTH - 26, fy + 16), badge_color, -1)
            text_col = (10, 10, 10) if is_occ else (20, 20, 20)
            cv2.putText(hud, badge_title, (36, fy + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.46, text_col, 2, cv2.LINE_AA)
            fy += 32

            conf_str = f"Detection Confidence: {conf:.1%}" if occ else "Detection Confidence: N/A"
            cv2.putText(hud, conf_str, (26, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.38, COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
        else:
            cv2.putText(hud, "Awaiting driver check-in...", (26, fy + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
            cv2.putText(hud, "Assigned slot will highlight here.", (26, fy + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.38, COLOR_TEXT_MUTED, 1, cv2.LINE_AA)

        y += focus_h + 16

        # 5. Playback & Replay Controls Helper
        is_playing = replay_status.is_running if replay_status else False
        play_mode_str = "PLAYING" if is_playing else "PAUSED"
        
        cv2.putText(hud, f"REPLAY CONTROLS [{play_mode_str}]", (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLOR_TEXT_ACCENT, 1, cv2.LINE_AA)
        y += 16
        cv2.line(hud, (16, y), (self.HUD_WIDTH - 16, y), COLOR_CARD_BORDER, 1)
        y += 18

        controls = [
            ("SPACE", "Pause / Resume Replay"),
            ("N", "Step Next Frame"),
            ("R", "Reset to Start (Frame 0)"),
            ("+ / -", "Adjust Playback Speed"),
            ("D", f"Toggle Debug Info ({'ON' if debug_mode else 'OFF'})"),
            ("Q / ESC", "Quit Demonstration"),
        ]

        for key, desc in controls:
            cv2.putText(hud, f"[{key}]", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.36, COLOR_TEXT_ACCENT, 1, cv2.LINE_AA)
            cv2.putText(hud, desc, (90, y), cv2.FONT_HERSHEY_SIMPLEX, 0.36, COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
            y += 18

        return hud

    def _draw_card_box(self, img: np.ndarray, x: int, y: int, w: int, h: int, title: str) -> None:
        """Draw a styled background container box with title header."""
        cv2.rectangle(img, (x, y), (x + w, y + h), COLOR_CARD_BG, -1)
        cv2.rectangle(img, (x, y), (x + w, y + h), COLOR_CARD_BORDER, 1)
        # Header accent bar
        cv2.rectangle(img, (x, y), (x + w, y + 20), (32, 32, 44), -1)
        cv2.putText(img, title, (x + 8, y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.36, COLOR_TEXT_ACCENT, 1, cv2.LINE_AA)
