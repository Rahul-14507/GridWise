# GridWise: Smart EV Charging Management System

An intelligent Electric Vehicle charging management system designed to optimize energy allocation, respect grid constraints, leverage solar generation proxies, and schedule charging sessions efficiently.

## Milestone 1: Backend Foundation

Milestone 1 implements the backend architectural foundation:
- Pure domain models using **Pydantic v2** (EVs, Grid, Solar, Virtual BESS, Parking, ESP32 Telemetry)
- Decoupled **domain services** for net available power computation
- Typed configuration management with **pydantic-settings**
- Asynchronous **FastAPI** web application with versioned endpoints and health checks
- Comprehensive **pytest** suite with realistic JSON contract fixtures

For full architectural details, data contracts, and quickstart instructions, refer to [backend/README.md](backend/README.md).

## Quick Start

```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run test suite
pytest backend/tests -v

# 3. Start development server
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
