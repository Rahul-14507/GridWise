# GridWise — Phase 8: Parking Vision / OpenCV Integration

> **Prototype Disclaimer**: This prototype uses prerecorded parking imagery from the CNR-EXT dataset for demonstration and deterministic replay, and does not represent a live CCTV camera deployment.

---

## 1. System Overview & Architecture Boundary

The GridWise Parking Vision module is a standalone computer vision pipeline designed to determine physical parking-slot occupancy.

### Architectural Boundary Rule

The system cleanly separates vehicle identity from physical occupancy:

- **QR / Mobile Session Layer**: Owns driver session, vehicle identity (`ev_id`), and assigned charging slot (`assigned_slot`).
- **Parking Vision System**: Owns physical slot occupancy (`slot_id`, `occupied`, `confidence`).
- **GridWise Backend**: Merges these two domains into a unified operational view.

**OpenCV is NOT responsible for:**
- Driver authentication or account validation
- Vehicle license-plate recognition or re-identification
- Generating or validating QR sessions
- Charging power allocation or hardware optimization

---

## 2. Dataset & Coordinate Rescaling

### CNR-EXT Camera 4

For hackathon demonstration and deterministic playback, we utilize 20 selected historical frames from CNR-EXT Camera 4:
`CNR-EXT_FULL_IMAGE_1000x750/FULL_IMAGE_1000x750/SUNNY/2016-01-12/camera4/`

### Bounding Box Rescaling Math

Slot bounding boxes are loaded dynamically from `camera4.csv`. The original annotations correspond to a high-resolution camera space of `2592 × 1944`. The replay frames are standardized at `1000 × 750`.

Coordinates are rescaled at runtime using the following formula:

$$\text{x\_new} = \text{round}\left(x \times \frac{1000}{2592}\right)$$
$$\text{y\_new} = \text{round}\left(y \times \frac{750}{1944}\right)$$
$$\text{w\_new} = \text{round}\left(w \times \frac{1000}{2592}\right)$$
$$\text{h\_new} = \text{round}\left(h \times \frac{750}{1944}\right)$$

Original CNR `SlotId`s (e.g. `606`, `607`, `192`, `221`) are preserved.

---

## 3. Vision Pipeline Flow

```
Frame Replay Engine (camera4)
          ↓
  Slot ROI Extractor (camera4.csv)
          ↓
Occupancy Classifier (CV Features / ML)
          ↓
  Temporal State Smoother (2-frame confirmation)
          ↓
  ParkingVisionState & REST API
```

1. **Replay Engine**: Sequences the 20 pre-recorded frames in chronological order (`0749`, `0819`, `0849`, ... `1719`). Supports play, pause, reset, step next, and configurable interval.
2. **ROI Extraction**: Crops the 37 rescaled slot bounding boxes safely from each frame.
3. **Occupancy Classification**: Abstract `OccupancyClassifier` interface. The default feature classifier computes Canny edge density, Laplacian texture variance, and grayscale intensity standard deviation to determine slot occupancy and confidence (0.0 to 1.0).
4. **Temporal Smoothing**: Requires N consecutive frames (default=2) before confirming state changes, preventing single-frame shadow or transient flickers.

---

## 4. How to Run Geometry Validation

To verify that the 37 slot ROIs map accurately onto physical parking spaces:

```bash
cd backend
python -m app.vision.validate_camera4
```

This generates the annotated verification image at:
`outputs/parking_vision/camera4_overlay.jpg`

---

## 5. REST API Integration Contract

### GET `/api/v1/parking/state`
Returns facility-wide physical occupancy state:

```json
{
  "timestamp": "2026-09-19T02:15:00Z",
  "source_capture_time": "2016-01-12_0749",
  "source": "cnrpark_camera4_replay",
  "camera_id": "camera4",
  "frame_id": "2016-01-12_0749",
  "slots": [
    {
      "slot_id": "606",
      "occupied": true,
      "confidence": 0.94
    },
    {
      "slot_id": "607",
      "occupied": false,
      "confidence": 0.91
    }
  ],
  "summary": {
    "total_slots": 37,
    "occupied_slots": 21,
    "free_slots": 16
  }
}
```

### GET `/api/v1/parking/slots/{slot_id}`
Lookup occupancy for a specific slot:

```json
{
  "slot_id": "606",
  "occupied": true,
  "confidence": 0.94
}
```

### POST `/api/v1/parking/replay/control`
Control frame replay execution:

```json
{
  "action": "next",
  "interval_seconds": 1.0
}
```

### POST `/api/v1/parking/combined`
Integrates physical slot occupancy with QR/driver session assignments:

```json
[
  {
    "slot_id": "606",
    "ev_id": "EV-023",
    "slot_occupied": true,
    "confidence": 0.94,
    "status_assessment": "normal_charging"
  }
]
```
