# GridWise: Smart EV Charging Management System

An intelligent Electric Vehicle (EV) charging management system designed to optimize energy allocation, respect physical grid constraints, leverage solar generation proxies, manage stationary virtual battery storage (BESS), and schedule EV charging sessions efficiently.

---

## Key Features

- **Dynamic Grid & Thermal Derating**: Calculates available facility capacity based on transformer thermal limits and real-time temperature telemetry.
- **Solar Irradiance Integration**: Calibrates solar sensor voltage to estimate real-time PV generation.
- **Virtual Battery Storage (BESS)**: Simulates stationary battery physics to support peak shaving and deficit buffering.
- **Prioritized EV Power Allocation**: Weighted multi-factor priority algorithm (SoC deficit, departure deadline proximity, waiting time fairness, energy requirement).
- **Hard Safety Constraint Enforcement**: Guarantees total power allocations never exceed maximum safe grid capacity.
- **Real-Time ESP32 Telemetry Ingestion**: Ingests sensor data from physical/simulated hardware with staleness detection.
- **Production REST API**: FastAPI backend providing rich telemetry, system state, simulation control, and optimization endpoints.
- **Admin Real-Time Dashboard**: React 18 + Vite + TypeScript dashboard with live charts, occupancy maps, and control controls.

---

## Project Architecture

```text
GridWise/
├── backend/                   # Python FastAPI Backend
│   ├── app/
│   │   ├── api/routes/        # REST API Endpoints (/api/v1/*)
│   │   ├── application/       # Application state coordinator & warnings
│   │   ├── config/            # pydantic-settings configuration
│   │   ├── domain/            # Domain models (EVs, Energy, Battery, Hardware, System)
│   │   ├── infrastructure/    # ESP32 hardware telemetry ingestion & staleness
│   │   ├── optimizer/         # Priority scoring, deadline feasibility & power allocator
│   │   └── simulation/        # Closed-loop simulation engine & scenario presets
│   ├── tests/                 # 167 Pytest unit & integration test suites
│   ├── pyproject.toml
│   └── requirements.txt
│
└── frontend/                  # React + Vite + TypeScript Frontend
    ├── src/
    │   ├── components/        # Reusable UI components (Header, FleetTable, Solar, Battery, etc.)
    │   ├── hooks/             # Custom state & polling hooks (useSystemState)
    │   ├── pages/             # Admin Dashboard page
    │   ├── services/          # Centralized API fetch client
    │   └── types/             # TypeScript API contract definitions
    ├── tests/                 # 23 Vitest + React Testing Library test suites
    ├── .env.development       # Development environment config (VITE_API_BASE_URL)
    └── package.json
```

---

## Prerequisites

Before starting, ensure you have the following installed:

- **Python**: Version `3.10` or higher
- **Node.js**: Version `18.0` or higher
- **npm**: Version `9.0` or higher (comes with Node.js)
- **Git**: For version control

---

## Setup & Installation Guide

### Step 1: Clone the Repository

```powershell
git clone <repository-url>
cd GridWise
```

### Step 2: Backend Setup (Python Virtual Environment)

1. **Create a virtual environment**:
   ```powershell
   python -m venv .venv
   ```

2. **Activate the virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD)**:
     ```cmd
     .\.venv\Scripts\activate.bat
     ```
   - **Linux / macOS**:
     ```bash
     source .venv/bin/activate
     ```

3. **Install backend dependencies**:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

### Step 3: Frontend Setup (Node.js & npm)

1. Navigate to the frontend directory:
   ```powershell
   cd frontend
   ```

2. Install Node.js packages:
   ```powershell
   npm install
   ```

3. Verify environment configuration (`frontend/.env.development`):
   Ensure `VITE_API_BASE_URL` points to the backend versioned API prefix:
   ```env
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   ```

4. Return to root directory:
   ```powershell
   cd ..
   ```

---

## Running the Application Locally

To run the complete system, start the backend API server and the frontend dev server in separate terminal windows.

### Terminal 1: Start Backend API Server

```powershell
# Ensure virtual environment is active
.\.venv\Scripts\Activate.ps1

cd backend
python -m uvicorn app.main:app --reload --port 8000
```

- **Backend Base URL**: `http://localhost:8000`
- **API Version 1 Base**: `http://localhost:8000/api/v1`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

### Terminal 2: Start Frontend Development Server

```powershell
cd frontend
npm run dev
```

- **Admin Dashboard**: `http://localhost:3000` (or the local port displayed in terminal)

---

## Additional Operational Modes

### Running CLI Simulation Mode (Headless)

You can run the simulation engine directly in the terminal without starting the web servers:

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Set PYTHONPATH to include backend folder
$env:PYTHONPATH="backend"

# Run 10-step simulation with live optimizer under the HOT_DAY scenario
python -m app.simulation --scenario HOT_DAY --ticks 10 --optimize
```

**Available Scenarios**: `NORMAL_DAY`, `HOT_DAY`, `SOLAR_SURPLUS`, `HIGH_EV_DEMAND`, `BESS_STRESS`, `SENSOR_FAILURE`, `OVERNIGHT_CHARGING`, `COMBINED_STRESS`.

---

## Running Test Suites

### Backend Tests (167 tests via Pytest)

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run all backend unit & integration tests
pytest backend/tests -v
```

### Frontend Tests (23 tests via Vitest)

```powershell
cd frontend

# Run frontend unit & component tests
npm test
```

---

## License

Internal project repository — All rights reserved.
