# Hardware Integration & ESP32 Telemetry Subsystem

## Overview
The `app/infrastructure/hardware/` subsystem provides the ingestion boundary for real physical sensor telemetry streamed over HTTP from ESP32 edge microcontroller devices.

## Sensor Scope & Physical Boundaries
The real ESP32 device measures and reports physical environmental parameters only:
- **Temperature (`temperature_c`)**: Ambient temperature in °C.
- **Humidity (`humidity_percent`)**: Relative humidity % (0-100%).
- **Rain Detection (`rain_detected`)**: Boolean rain indicator.
- **Rain Intensity (`rain_intensity`)**: Precipitation intensity index.
- **Solar Sensor Voltage (`solar_voltage_v`)**: Voltage proxy (0-3.3V) indicating ambient solar irradiance.

### Explicit Non-Measurements
The ESP32 hardware **does not** contain electrical current, active power (kW), or energy metering hardware. Power-domain properties (solar generation in kW, building load demand, transformer loading, and EV charge rates) are calculated and managed in software by the domain services (`SolarService`, `ThermalService`, `EnergyService`, and `ChargingOptimizer`).

## Data Contract
Incoming telemetry payloads must adhere to the `HardwareTelemetry` schema:
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

## Freshness & Staleness Detection
Hardware connectivity is tracked per device. If the time elapsed since the most recent reading exceeds `hardware_telemetry_timeout_seconds` (default: 300s), the device status transitions to `stale` (`is_connected: false`).
