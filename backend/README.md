# GridWise: Smart EV Charging Management System (Backend)

Milestone 1 establishes the backend foundation for GridWise, featuring clean domain boundaries, strict typing with Pydantic v2, data validation contracts, configuration management, and unit/integration testing.

---

## Architecture & Project Structure

The project follows a modular, layered domain-driven design:

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI entry point & route registration
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── energy.py           # Energy status API routes
│   │       ├── evs.py              # EV fleet status API routes
│   │       └── health.py           # Health check routes (/health)
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── ev.py               # EV & EVStatus domain models
│   │   │   ├── energy.py           # GridState, SolarState, EnergyState models
│   │   │   ├── battery.py          # VirtualBattery (BESS) domain model
│   │   │   ├── parking.py          # ParkingSlot & ParkingState domain models
│   │   │   └── hardware.py         # HardwareTelemetry ESP32 data contract
│   │   │
│   │   └── services/
│   │       ├── __init__.py
│   │       └── energy_service.py   # Available charging capacity calculation
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py             # Pydantic-settings configuration
│   │
│   └── infrastructure/
│       ├── __init__.py
│       └── README.md               # Boundary documentation for future DB/MQTT/CV
│
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── hardware.json           # Sample ESP32 telemetry JSON
│   │   └── evs.json                # Sample EV fleet test fixtures
│   ├── test_hardware_models.py     # Hardware telemetry validation tests
│   ├── test_ev_models.py           # EV state & constraints tests
│   ├── test_energy_models.py       # Energy, BESS & EnergyService tests
│   ├── test_parking_models.py      # Parking slot allocation tests
│   └── test_health.py              # FastAPI endpoint tests
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Architectural Principles

1. **High Cohesion**: Each module has one explicit responsibility (e.g., `hardware.py` defines only ESP32 telemetry models; `settings.py` manages configuration).
2. **Low Coupling**: The domain layer (`app/domain/`) is pure Python + Pydantic v2 and **does not depend on FastAPI**, HTTP frameworks, databases, OpenCV, or hardware-specific drivers.
3. **API Layer Separation**: API routes depend on domain models and services, not vice versa.
4. **Separation of Concerns**: State is represented in domain models; business logic belongs in domain services. Optimization algorithms are isolated for subsequent milestones.

---

## Real Hardware Input vs. Simulated Data

### Real Hardware Inputs (from ESP32 Edge Telemetry)
* `temperature_c`: Ambient temperature (°C)
* `humidity_percent`: Relative ambient humidity (0–100%)
* `rain_detected`: Precipitation boolean indicator
* `rain_intensity`: Rain intensity index
* `solar_voltage_v`: Raw sensor voltage proxy for solar availability (Note: We do NOT have current/power measurement hardware on the ESP32)

### Simulated / Modeled Data (Milestone 1)
* Grid capacity limits
* Facility building power demand
* Estimated solar power generation (kW)
* Virtual Battery Energy Storage System (BESS)
* EV fleet connection, SoC, and parking occupancy

---

## ESP32 Hardware JSON Contract

The ESP32 reports telemetry using the following JSON schema:

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

Validation requirements:
- `device_id`: non-empty string.
- `timestamp`: ISO-8601 string parsed as timezone-aware `datetime`.
- `temperature_c`: float in range `[-50.0, 80.0]`.
- `humidity_percent`: float in range `[0.0, 100.0]`.
- `rain_intensity`: float `>= 0.0`.
- `solar_voltage_v`: float `>= 0.0` (proxy for irradiance, not power).

---

## Core Domain Rules

1. **Grid safety is a hard constraint**: Total EV charging load must never exceed available facility capacity.
2. **Maximum charging rate**: An EV cannot receive more power than its `max_charging_power_kw`.
3. **Target SoC ceiling**: An EV at or above its `target_soc_percent` should not receive charging power.
4. **Non-negative power**: Charging and available power values can never be negative.
5. **Virtual Battery limits**: Virtual battery SoC cannot exceed 100% or drop below `minimum_soc_percent`.
6. **Physical vs Derived**: Solar panel voltage is a physical measurement; solar generation is an estimated/modeled value.
7. **Simulation isolation**: Grid capacity, building demand, battery state, and EV charging power are simulated.

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- Virtual environment (`venv`)

### 1. Set Up Virtual Environment
```bash
# From the project root
python -m venv .venv

# Activate on Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Activate on Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

---

## Running the Application

Start the FastAPI application using Uvicorn:

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Available Endpoints
- **Health Check**: `GET http://localhost:8000/health`
- **Interactive Swagger Docs**: `GET http://localhost:8000/docs`
- **ReDoc Documentation**: `GET http://localhost:8000/redoc`
- **Energy State (Placeholder)**: `GET http://localhost:8000/api/v1/energy`
- **EV Fleet (Placeholder)**: `GET http://localhost:8000/api/v1/evs`

---

## Running Tests

Execute the comprehensive test suite with `pytest`:

```bash
cd backend
pytest tests -v
```
