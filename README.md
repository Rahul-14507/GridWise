# GridWise: Smart EV Charging Management System

An intelligent Electric Vehicle charging management system designed to optimize energy allocation, respect grid constraints, leverage solar generation proxies, manage virtual battery storage, and schedule EV charging sessions efficiently.

## Project Phases

- **Phase 1: Backend Foundation** (Completed)
  - Pure domain models using Pydantic v2 (EVs, Grid, Solar, Virtual BESS, Parking, ESP32 Telemetry)
  - Available capacity calculation service
  - Typed configuration management with pydantic-settings
  - Minimal asynchronous FastAPI application
- **Phase 2: Energy Intelligence & Simulation Engine** (Completed)
  - Deterministic simulation clock and ESP32 telemetry simulator
  - Calibrated solar availability and power estimation service
  - Temperature-induced grid and transformer capacity derating service
  - 24-hour diurnal building demand simulator with interpolation
  - Physical EV charging fleet simulation and battery SoC integration
  - Virtual battery charge/discharge physics
  - 8 predefined operational test scenarios (e.g. `NORMAL_DAY`, `HOT_DAY`, `COMBINED_STRESS`)
  - Interactive CLI simulation runner (`python -m app.simulation`)
- **Phase 3: EV Priority and Charging Optimization Engine** (Completed)
  - Normalized EV urgency metrics (SoC deficit, departure proximity, energy deficit, waiting fairness)
  - Deadline feasibility analyzer (`FEASIBLE`, `AT_RISK`, `EXPIRED`, `COMPLETE`)
  - Weighted composite priority scoring
  - Constrained multi-pass iterative power allocator
  - Stationary battery dispatch strategy (peak shaving & deficit support)
  - Independent hard constraint safety verification
  - Machine-readable explainability reasons for every EV allocation
  - Full closed-loop integration with simulation engine

For full technical documentation, data contracts, and quickstart instructions, refer to [backend/README.md](backend/README.md).

## Quick Start

```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run all tests (139 tests)
pytest backend/tests -v

# 3. Run interactive CLI simulation with live Optimizer
$env:PYTHONPATH="backend"
python -m app.simulation --scenario NORMAL_DAY --ticks 5 --optimize

# 4. Start FastAPI server
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
