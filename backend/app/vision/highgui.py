"""OpenCV HighGUI live visual demonstration runner for GridWise parking vision.

Executes a desktop OpenCV HighGUI window demonstrating real-time parking slot occupancy,
Camera 4 historical frame replay, and dynamic QR session EV -> slot assignments.
"""

import argparse
import os
from pathlib import Path
import sys
import time
from typing import Dict, Optional
import cv2

# Ensure backend root directory is on sys.path regardless of execution directory
_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    import urllib.request
    import json
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

from app.application.state_service import get_app_state_service
from app.vision.renderer import ParkingVisionRenderer, normalize_slot_id
from app.vision.service import ParkingVisionService, get_parking_vision_service


def fetch_ev_assignments_from_api(api_base_url: str) -> Optional[Dict[str, str]]:
    """Fetch active EV slot assignments from running GridWise FastAPI backend."""
    if not HAS_URLLIB:
        return None
    try:
        url = f"{api_base_url.rstrip('/')}/evs"
        req = urllib.request.Request(url, headers={"User-Agent": "GridWise-HighGUI/1.0"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                assignments: Dict[str, str] = {}
                for ev in data:
                    slot_id = ev.get("slot_id")
                    ev_id = ev.get("id")
                    if slot_id and ev_id:
                        assignments[str(slot_id)] = str(ev_id)
                return assignments
    except Exception:
        pass
    return None


def fetch_ev_assignments_in_process() -> Dict[str, str]:
    """Fetch active EV slot assignments directly from in-memory AppStateService."""
    try:
        state_service = get_app_state_service()
        ev_details = state_service.get_evs_detail()
        assignments: Dict[str, str] = {}
        for ev in ev_details:
            if ev.slot_id:
                assignments[str(ev.slot_id)] = ev.id
        return assignments
    except Exception:
        return {}


def run_highgui_demo(
    api_url: Optional[str] = "http://localhost:8000/api/v1",
    initial_interval: float = 1.0,
    window_name: str = "GridWise Parking Vision — Camera 4",
    auto_play: bool = True,
    debug: bool = False,
) -> None:
    """Run interactive OpenCV HighGUI event loop."""
    vision_service = get_parking_vision_service()
    slot_manager = vision_service.slot_manager
    renderer = ParkingVisionRenderer()

    # Banner announcement
    print("=" * 60)
    print("GridWise Parking Vision Demonstration")
    print("Camera: Camera 4 (CNR-EXT)")
    print("Mode: Historical Replay Stream")
    print(f"Total Slots Tracked: {len(slot_manager.slots)}")
    print(f"Backend Sync Mode: {'HTTP Bridge (' + api_url + ')' if api_url else 'In-Memory Service'}")
    print("=" * 60)
    print("Keyboard Controls:")
    print("  [SPACE]   Pause / Resume Replay Playback")
    print("  [N]       Advance Next Frame Manually")
    print("  [R]       Reset Playback to Frame 0")
    print("  [+]       Increase Playback Speed")
    print("  [-]       Decrease Playback Speed")
    print("  [D]       Toggle Confidence Debug Overlay")
    print("  [Q / ESC] Cleanly Close Visualizer")
    print("=" * 60)

    # Initial frame processing
    vision_state = vision_service.get_current_state()
    
    # Configure replay engine
    is_playing = auto_play
    interval_seconds = max(0.1, initial_interval)
    vision_service.control_replay("play" if is_playing else "pause", interval_seconds=interval_seconds)

    # Create highgui window with GUI support verification
    try:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1380, 750)
    except cv2.error as e:
        print("\n" + "!" * 60)
        print("ERROR: OpenCV HighGUI is not available in the current Python environment.")
        print("Reason: You are running with a headless OpenCV package (e.g. opencv-python-headless).")
        print("\nSolution:")
        print("  Run using the project virtual environment where full GUI OpenCV is installed:")
        print("  Windows:  .\\.venv\\Scripts\\python.exe -m app.vision.highgui")
        print("  or activate the virtualenv first:  .\\.venv\\Scripts\\Activate.ps1")
        print("!" * 60 + "\n")
        return

    last_advance_time = time.time()
    last_assignment_poll = 0.0
    cached_assignments: Dict[str, str] = {}
    debug_mode = debug

    try:
        while True:
            now = time.time()

            # 1. Periodically poll EV assignments (every 0.5s)
            if now - last_assignment_poll >= 0.5:
                last_assignment_poll = now
                api_assignments = None
                if api_url:
                    api_assignments = fetch_ev_assignments_from_api(api_url)
                
                if api_assignments is not None:
                    cached_assignments = api_assignments
                else:
                    cached_assignments = fetch_ev_assignments_in_process()

            # 2. Advance frame if playing
            if is_playing and (now - last_advance_time >= interval_seconds):
                vision_state = vision_service.next_frame()
                last_advance_time = now

            # 3. Retrieve current visual frame and replay status
            frame, frame_id, capture_time = vision_service.replay_engine.get_current_frame()
            replay_status = vision_service.replay_engine.get_status()

            # 4. Render composite visualization
            canvas = renderer.render(
                frame=frame,
                slots=slot_manager.slots,
                vision_state=vision_state,
                ev_assignments=cached_assignments,
                replay_status=replay_status,
                debug_mode=debug_mode,
            )

            # 5. Display frame
            cv2.imshow(window_name, canvas)

            # 6. Non-blocking key event processing
            key = cv2.waitKey(30) & 0xFF
            if key in (ord('q'), ord('Q'), 27):  # 27 = ESC
                print("\n[HighGUI] Closing window and exiting demonstration cleanly.")
                break
            elif key == 32:  # SPACE
                is_playing = not is_playing
                vision_service.control_replay("play" if is_playing else "pause")
                print(f"[HighGUI] Replay {'Resumed (Playing)' if is_playing else 'Paused'}")
            elif key in (ord('n'), ord('N')):
                vision_state = vision_service.next_frame()
                last_advance_time = time.time()
                print(f"[HighGUI] Stepped to next frame: {vision_state.frame_id} ({vision_state.source_capture_time})")
            elif key in (ord('r'), ord('R')):
                vision_service.control_replay("reset")
                vision_state = vision_service.process_current_frame()
                last_advance_time = time.time()
                print("[HighGUI] Reset replay to frame 0")
            elif key in (ord('+'), ord('=')):
                interval_seconds = max(0.1, round(interval_seconds - 0.2, 1))
                vision_service.control_replay("play" if is_playing else "pause", interval_seconds=interval_seconds)
                print(f"[HighGUI] Speed increased (Interval: {interval_seconds}s)")
            elif key in (ord('-'), ord('_')):
                interval_seconds = min(5.0, round(interval_seconds + 0.2, 1))
                vision_service.control_replay("play" if is_playing else "pause", interval_seconds=interval_seconds)
                print(f"[HighGUI] Speed decreased (Interval: {interval_seconds}s)")
            elif key in (ord('d'), ord('D')):
                debug_mode = not debug_mode
                print(f"[HighGUI] Debug Overlay {'Enabled' if debug_mode else 'Disabled'}")

    except KeyboardInterrupt:
        print("\n[HighGUI] Keyboard interrupt received. Exiting.")
    finally:
        cv2.destroyAllWindows()


def main() -> None:
    """CLI Entrypoint for HighGUI parking vision demonstration."""
    parser = argparse.ArgumentParser(description="GridWise Parking Vision HighGUI Live Demonstration")
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000/api/v1",
        help="GridWise FastAPI backend base URL for live driver QR session sync (default: http://localhost:8000/api/v1). Pass '' to force in-process mode.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Replay playback interval between frames in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable confidence debug text overlay on all parking slots",
    )
    parser.add_argument(
        "--paused",
        action="store_true",
        help="Start with replay in paused state",
    )
    parser.add_argument(
        "--window-name",
        type=str,
        default="GridWise Parking Vision — Camera 4",
        help="Title of OpenCV window",
    )

    args = parser.parse_args()

    api_url_arg = args.api_url if args.api_url and args.api_url.strip() else None

    run_highgui_demo(
        api_url=api_url_arg,
        initial_interval=args.interval,
        window_name=args.window_name,
        auto_play=not args.paused,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
