# GridWise Frontend — Admin Real-Time Dashboard

A modern, responsive, real-time monitoring and control dashboard for the GridWise Smart EV Charging Management System. Built with React 18, TypeScript, and Vite.

## Architecture & Features

- **Pure Consumer Model**: Strictly consumes Phase 5 REST APIs (`/api/v1/*`); contains zero domain/business logic.
- **Resilient Polling & Stale Detection**: Configurable polling interval (default 3s) with 10s timeout badge detection and graceful disconnection handling.
- **Rolling Telemetry History**: Maintains an in-memory rolling window of recent data points for SVG line charts (Demand vs. Capacity, Solar Generation, EV Power, Battery SoC).
- **Comprehensive Cluster Visibility**:
  - **Header Bar**: Live status, mode badge (`SIMULATION` / `HARDWARE`), manual refresh, simulation step (+60s), run optimizer, and apply allocations.
  - **Infrastructure Overview**: Total facility load, effective capacity, available EV power, and capacity utilization bar with safety coloring.
  - **Connected EV Fleet Table**: Real-time slot allocation, charging rate vs. max rate, SoC progress with target marker, deadline feasibility status (`FEASIBLE`, `AT_RISK`, `EXPIRED`, `COMPLETE`), and algorithmic priority scores.
  - **Solar & Environmental Subsystem**: Solar availability %, generation in kW, sensor proxy voltage, and precipitation indicators.
  - **Transformer & Safety Subsystem**: Ambient temperature and thermal derating tracking.
  - **Energy Flow Balance**: Real-time visual balance of Generation Sources vs. Demand Sinks.
  - **Stationary Virtual Battery (BESS)**: SoC, usable kWh, charge/discharge contribution power, and dispatch mode.
  - **Charging Bay Occupancy**: Total, occupied, and available slot metrics.
  - **System Alerts & Notifications**: Formatted active warning and constraint notifications.
  - **Optimization Decision Panel**: Allocated power, BESS strategy, and cycle timestamp.

## Development & Build

```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm.cmd install

# Start development server (http://localhost:3000)
npm.cmd run dev

# Run Vitest test suites (23 tests)
npm.cmd test

# Build production bundle
npm.cmd run build
```
