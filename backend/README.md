# GridWise: Smart EV Charging Management System (Backend)

GridWise is an intelligent Electric Vehicle charging management system designed to optimize energy allocation, respect grid capacity constraints, leverage solar irradiance proxies, manage virtual battery storage, and schedule EV charging sessions.

---

## Architecture: Optimization & Simulation Pipeline

```
ESP32 / Fake Telemetry
        ↓
Telemetry Processing
        ↓
Solar Service (Irradiance Calibration)
        ↓
Thermal Service (Grid Capacity Derating)
        ↓
Grid Simulator (24h Diurnal Demand)
        ↓
Virtual Battery Simulator (BESS Physics)
        ↓
Parking Simulator (Slot Occupancy Sync)
        ↓
   SystemState
        ↓
[ Phase 3 Optimizer ] ──────► OptimizationDecision (with explainability)
        │                                  │
        └─────── Control Allocations ◄─────┘
                        ↓
                  EV Simulator
                        ↓
            Updated SystemState Snapshot
```

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application setup & route registration
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── system.py           # GET /api/v1/system/state, /summary, /status
│   │       ├── energy.py           # GET /api/v1/energy
│   │       ├── evs.py              # GET /api/v1/evs, GET /api/v1/evs/{ev_id}
│   │       ├── optimization.py     # GET /api/v1/optimization/current, POST /run, POST /apply
│   │       ├── health.py           # GET /health
│   │       ├── hardware.py         # POST /api/v1/hardware/telemetry, GET /latest, GET /status
│   │       └── simulation.py       # Simulation control, state & optimize-tick APIs
│   │
│   ├── application/
│   │   ├── __init__.py
│   │   ├── models.py               # API response models (SystemSummary, EnergyDetail, EVDetail, etc.)
│   │   ├── state_service.py        # Central in-memory AppStateService coordinator
│   │   └── warnings.py             # Factual SystemWarning evaluator
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── ev.py               # EV, EVStatus, and physical helper calculations
│   │   │   ├── energy.py           # GridState, SolarState, EnergyState models
│   │   │   ├── battery.py          # VirtualBattery (BESS) domain model
│   │   │   ├── parking.py          # ParkingSlot & ParkingState domain models
│   │   │   ├── hardware.py         # HardwareTelemetry ESP32 data contract
│   │   │   ├── simulation.py       # ThermalState, SimulationControlInput models
│   │   │   └── system.py           # SystemState top-level unified snapshot
│   │   │
│   │   └── services/
│   │       ├── energy_service.py   # Available charging capacity calculation
│   │       ├── solar_service.py    # Solar availability & generation estimation
│   │       ├── thermal_service.py  # Temperature-based grid capacity derating
│   │       ├── battery_service.py  # Battery charge/discharge energy physics
│   │       └── system_state_service.py # SystemState assembler
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   └── hardware/
│   │       ├── __init__.py
│   │       ├── telemetry_service.py # In-memory ESP32 ingestion, multi-device tracking, staleness
│   │       └── README.md            # Hardware physical sensor boundaries documentation
│   │
│   ├── optimizer/
│   │   ├── __init__.py
│   │   ├── models.py               # OptimizationDecision, EVAllocationDecision, DeadlineStatus
│   │   ├── urgency.py              # SoC, departure, deficit, and waiting score metrics
│   │   ├── deadline.py             # Feasibility & deadline risk classification
│   │   ├── priority.py             # Weighted priority score calculation
│   │   ├── constraints.py          # Hard physical & infrastructure safety validator
│   │   ├── battery_strategy.py     # Stationary battery discharge decision logic
│   │   ├── allocator.py            # Constrained iterative priority-ranked power allocator
│   │   └── optimizer.py            # ChargingOptimizer central engine & explainability
│   │
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── clock.py                # Synthetic timezone-aware simulation clock
│   │   ├── sensor_simulator.py     # Diurnal ESP32 telemetry generator
│   │   ├── grid_simulator.py       # 24-hour building load curve interpolation
│   │   ├── ev_simulator.py         # EV fleet charging & SoC integration
│   │   ├── battery_simulator.py    # Virtual battery state wrapper
│   │   ├── parking_simulator.py    # Parking occupancy & bay management
│   │   ├── scenarios.py            # Predefined deterministic scenarios
│   │   ├── engine.py               # Central Simulation Engine coordinator
│   │   ├── cli.py                  # Terminal interactive simulation runner
│   │   └── __main__.py             # python -m app.simulation entrypoint
│   │
│   └── config/
│       ├── __init__.py
│       └── settings.py             # Typed Pydantic-settings configuration
│
├── tests/                          # 167 automated unit, integration, and safety tests
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Phase 3: EV Priority and Charging Optimization Engine

### 1. Priority Scoring Formulation

The priority of each eligible vehicle is computed using a normalized, weighted linear combination:

$$\text{Priority} = w_{\text{soc}} \cdot U_{\text{soc}} + w_{\text{dep}} \cdot U_{\text{dep}} + w_{\text{def}} \cdot S_{\text{def}} + w_{\text{wait}} \cdot S_{\text{wait}}$$

Default configured weights:
* $w_{\text{soc}} = 0.35$ — State of Charge Urgency: $1 - (\text{SoC} / \text{Target SoC})$
* $w_{\text{dep}} = 0.40$ — Departure Proximity Urgency (monotonic piecewise curve ramping from $0.1$ at 4h to $1.0$ at departure)
* $w_{\text{def}} = 0.15$ — Energy Deficit Fraction: $\text{Energy Required} / \text{Battery Capacity}$
* $w_{\text{wait}} = 0.10$ — Waiting Time Fairness Score: $\min(\text{Minutes Waiting} / 60\text{ min}, 1.0)$

Weights are strictly verified to be non-negative and sum to $1.0$, producing a priority score bounded in $[0.0, 1.0]$.

### 2. Deadline Feasibility Analysis

For each vehicle, the required average charging power is evaluated:
$$P_{\text{req,avg}} = \frac{E_{\text{required}}}{\Delta t_{\text{remaining}}}$$

* **`COMPLETE`**: Vehicle is at or above target SoC ($E_{\text{required}} \le 0$).
* **`EXPIRED`**: Departure time has passed with positive deficit ($\Delta t_{\text{remaining}} \le 0$).
* **`AT_RISK`**: $P_{\text{req,avg}} > P_{\text{max\_charging}}$, indicating the vehicle mathematically cannot reach its target under its current maximum charging rate limit.
* **`FEASIBLE`**: $P_{\text{req,avg}} \le P_{\text{max\_charging}}$.

Vehicles evaluated as `AT_RISK` are prioritized during power allocation to minimize departure deficit.

### 3. Hard Safety Constraints

Every allocation decision is validated by an independent [`ConstraintValidator`](file:///e:/Projects/GridWise/backend/app/optimizer/constraints.py) that verifies:
1. **Infrastructure Capacity Limit**:
   $$\sum P_{\text{EV}} \le P_{\text{available\_ev\_power}}$$
2. **Net Interconnection Load Limit**:
   $$P_{\text{building}} + \sum P_{\text{EV}} - P_{\text{solar}} - P_{\text{battery\_discharge}} + P_{\text{battery\_charge}} \le P_{\text{effective\_grid}}$$
3. **Charger Hardware Limit**:
   $$0.0 \le P_{\text{EV}} \le \text{EV.max\_charging\_power\_kw}$$
4. **Energy Ceiling**:
   $$P_{\text{EV}} \cdot \Delta t \le E_{\text{required\_to\_target}}$$
5. **Ineligibility**: Disconnected or completed EVs receive $0.0\text{ kW}$.
6. **Battery Bounds**: Discharge power $\le P_{\text{max\_discharge}}$ and current $\text{SoC} > \text{Minimum SoC Floor}$.

### 4. Explainability & Machine-Readable Reasons

Every vehicle in an [`OptimizationDecision`](file:///e:/Projects/GridWise/backend/app/optimizer/models.py) includes a machine-readable `reason` explaining the allocation:
* `"Completed: Target SoC of 90% reached"`
* `"Disconnected: Vehicle is not connected"`
* `"At Risk: Allocated maximum charging rate (7.4 kW) to minimize departure deficit"`
* `"High Priority: Full maximum charging rate (11.0 kW) allocated"`
* `"Partial Allocation: Granted 8.53 kW constrained by available capacity"`
* `"Paused/Waiting: Lower priority rank under constrained infrastructure headroom"`

---

## Important Assumptions & Technical Limitations

1. **Modelled Transformer Loading**:
   The prototype edge hardware does not have physical current sensors measuring transformer internal windings. Grid loading is estimated from modeled building demand, EV charging allocations, estimated solar generation, and battery contributions.
2. **Thermal Derating Simulation**:
   Thermal derating is a configurable simulation model based on ambient temperature ($35^\circ\text{C}$ to $50^\circ\text{C}$), not a replacement for a physical utility protective relay.
3. **Pure Decision Engine**:
   The optimizer only calculates decisions and does not directly send actuation signals to hardware, databases, or third-party networks.

---

## Predefined Simulation Scenarios

| Scenario | Description | Key Conditions |
| :--- | :--- | :--- |
| `NORMAL_DAY` | Standard daytime operations | $T=28^\circ\text{C}$, Solar=2.20V (7.3 kW), Demand=8.0 kW |
| `SOLAR_SURPLUS` | Peak solar irradiance with low building demand | $T=31^\circ\text{C}$, Solar=2.85V (9.5 kW), Demand=5.0 kW |
| `CLOUD_EVENT` | Sudden midday cloud cover | $T=26^\circ\text{C}$, Solar=0.60V (2.0 kW), Demand=8.5 kW |
| `RAIN_EVENT` | Active precipitation and overcast skies | $T=23.5^\circ\text{C}$, Rain=12.5 mm/h, Solar=0.45V |
| `EVENING_PEAK` | Facility evening power surge | $T=27^\circ\text{C}$, Solar=0.10V, Demand=15.5 kW |
| `HIGH_EV_DEMAND` | Full fleet connected with deep energy deficits | 6 connected EVs, 6 parking bays |
| `HOT_DAY` | Extreme ambient heat triggering thermal derating | $T=43.5^\circ\text{C}$, Grid derated to 16.5 kW |
| `COMBINED_STRESS` | High heat + high demand + low solar + full EV fleet | $T=45.0^\circ\text{C}$, Demand=14.0 kW, Solar=0.50V |

---

## Phase 4: Real Hardware Telemetry Integration

### 1. Hardware Contract & Physical Boundaries
Real ESP32 edge microcontroller devices push environmental sensor readings to `POST /api/v1/hardware/telemetry`:
```json
{
  "device_id": "ESP32-001",
  "timestamp": "2026-09-18T10:30:00Z",
  "temperature_c": 31.4,
  "humidity_percent": 62.1,
  "rain_detected": false,
  "rain_intensity": 0.0,
  "solar_voltage_v": 2.14
}
```

* **Physical Measurements**: Ambient temperature, humidity, rain detection/intensity, and solar panel voltage proxy.
* **Software Calculations**: Power metrics (solar generation in kW, building electrical load, transformer loading, and EV power allocations) are computed dynamically in software by domain services and the Phase 3 `ChargingOptimizer`.

### 2. Multi-Device Tracking & Freshness Diagnostics
* **Multi-Device Support**: Devices are tracked independently in-memory via `HardwareTelemetryService`.
* **Staleness Detection**: Configurable `hardware_telemetry_timeout_seconds` (default: 300s). Telemetry older than the threshold transitions the device to `stale` (`is_connected: false`).
* **Endpoints**:
  - `POST /api/v1/hardware/telemetry` — Ingests & validates payload, returning `TelemetryReceipt`.
  - `GET /api/v1/hardware/telemetry/latest?device_id=...` — Returns latest telemetry (global or per-device).
  - `GET /api/v1/hardware/status` — Returns aggregate health, active/stale device counts, and per-device freshness.
  - `GET /api/v1/hardware/devices/{device_id}/status` — Returns individual device connection diagnostics.

---

## Phase 5: Production API + Real-Time State Layer

### 1. Application Layer Architecture
GridWise decouples raw domain models and simulation engines from presentation via [`AppStateService`](file:///e:/Projects/GridWise/backend/app/application/state_service.py).
- **Presentation Aggregation**: Assembles dashboard metrics without duplicating business rules.
- **Factual Warning Engine**: [`WarningService`](file:///e:/Projects/GridWise/backend/app/application/warnings.py) derives structured, machine-readable alerts (`EV_DEADLINE_AT_RISK`, `THERMAL_DERATING_ACTIVE`, `BATTERY_LOW_RESERVE`, etc.).
- **Hardware Protection**: Prevents simulated optimization decisions from controlling real physical hardware (`409 Conflict` on `/optimization/apply` in hardware mode).

### 2. Complete REST API Endpoints Table

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/system/state` | Complete authoritative `SystemState` domain snapshot |
| `GET` | `/api/v1/system/summary` | Dashboard-friendly aggregation (energy, battery, EV counts, parking, warnings) |
| `GET` | `/api/v1/system/status` | High-level operational health, active data source, and warning alerts |
| `GET` | `/api/v1/energy` | Facility energy balance, grid limits, solar generation, and load |
| `GET` | `/api/v1/evs` | Connected EV fleet list with battery metrics and optimization status |
| `GET` | `/api/v1/evs/{id}` | Detailed status for a single EV (404 if not found) |
| `GET` | `/api/v1/optimization/current` | Most recent computed `OptimizationDecision` (404 if none computed) |
| `POST` | `/api/v1/optimization/run` | Execute optimizer on current state, cache decision, and return |
| `POST` | `/api/v1/optimization/apply` | Apply latest decision to simulation engine (409 in hardware mode) |
| `POST` | `/api/v1/simulation/start` | Start simulation clock progression |
| `POST` | `/api/v1/simulation/stop` | Stop/pause simulation clock |
| `POST` | `/api/v1/simulation/reset` | Reset simulation state to initial scenario conditions |
| `POST` | `/api/v1/simulation/tick` | Advance simulation by one step and evolve EV SoCs |
| `POST` | `/api/v1/simulation/optimize-tick` | Compute optimal allocations and advance one tick in single step |
| `GET` | `/api/v1/simulation/scenarios` | List all predefined test scenarios |
| `POST` | `/api/v1/simulation/scenarios/{name}` | Load and activate a scenario |
| `POST` | `/api/v1/hardware/telemetry` | Ingest real ESP32 sensor telemetry payload |
| `GET` | `/api/v1/hardware/telemetry/latest` | Retrieve latest recorded sensor telemetry |
| `GET` | `/api/v1/hardware/status` | Hardware health and device freshness status |
| `GET` | `/api/v1/hardware/devices/{id}/status` | Connection diagnostics for individual device |
| `GET` | `/health` | Application health check endpoint |

---

## Running the CLI Simulation with Optimizer

```bash
# Run simulation with live ChargingOptimizer dynamic power allocation
python -m app.simulation --scenario NORMAL_DAY --ticks 5 --optimize

# Run simulation under thermal grid derating
python -m app.simulation --scenario HOT_DAY --ticks 5 --optimize
```

---

## Running Tests

Run the complete test suite (167 tests across Phase 1, Phase 2, Phase 3, Phase 4, and Phase 5):

```bash
cd backend
pytest tests -v
```
