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
│   │       ├── energy.py           # GET /api/v1/energy
│   │       ├── evs.py              # GET /api/v1/evs
│   │       ├── health.py           # GET /health
│   │       └── simulation.py       # Simulation control, state & optimize-tick APIs
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
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py             # Typed Pydantic-settings configuration
│   │
│   └── infrastructure/
│       ├── __init__.py
│       └── README.md               # Boundary documentation for future DB/MQTT/CV
│
├── tests/                          # 139 automated unit, integration, and safety tests
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

## Running the CLI Simulation with Optimizer

```bash
# Run simulation with live ChargingOptimizer dynamic power allocation
python -m app.simulation --scenario NORMAL_DAY --ticks 5 --optimize

# Run simulation under thermal grid derating
python -m app.simulation --scenario HOT_DAY --ticks 5 --optimize
```

---

## Running Tests

Run the complete test suite (139 tests across Phase 1, Phase 2, and Phase 3):

```bash
cd backend
pytest tests -v
```
