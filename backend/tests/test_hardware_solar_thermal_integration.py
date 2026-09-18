"""Integration tests verifying hardware telemetry drives Solar & Thermal services."""

from datetime import datetime, timezone
from app.domain.models.battery import VirtualBattery
from app.domain.models.hardware import HardwareTelemetry
from app.domain.models.parking import ParkingState
from app.domain.models.simulation import ThermalStatus
from app.infrastructure.hardware.telemetry_service import HardwareTelemetryService


def test_hardware_solar_voltage_scaling():
    service = HardwareTelemetryService()
    service.clear()

    # Telemetry with 1.5V (50% of 3.0V max => 5.0 kW on 10.0 kW array)
    telemetry = HardwareTelemetry(
        device_id="ESP32-001",
        timestamp=datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc),
        temperature_c=25.0,
        humidity_percent=50.0,
        rain_detected=False,
        rain_intensity=0.0,
        solar_voltage_v=1.5,
    )
    service.record_telemetry(telemetry)

    battery = VirtualBattery(
        capacity_kwh=50.0,
        current_energy_kwh=25.0,
        soc_percent=50.0,
        min_soc_percent=20.0,
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
    )
    parking = ParkingState(total_slots=0, slots=[])

    state = service.build_hardware_system_state(
        building_demand_kw=5.0,
        battery=battery,
        evs=[],
        parking=parking,
    )

    assert state.energy.solar.solar_voltage_v == 1.5
    assert state.energy.solar.availability_percent == 50.0
    assert state.energy.solar.estimated_generation_kw == 5.0


def test_hardware_extreme_temperature_thermal_derating():
    service = HardwareTelemetryService()
    service.clear()

    # Extreme hot temperature: 45°C (thermal derating starts at 35°C, critical at 50°C)
    # Default grid capacity = 25 kW, min = 10 kW. (45-35)/(50-35) = 10/15 = 2/3 derated
    # derated = 25 - (2/3) * (25 - 10) = 25 - 10 = 15 kW
    telemetry = HardwareTelemetry(
        device_id="ESP32-001",
        timestamp=datetime(2026, 9, 18, 14, 0, 0, tzinfo=timezone.utc),
        temperature_c=45.0,
        humidity_percent=30.0,
        rain_detected=False,
        rain_intensity=0.0,
        solar_voltage_v=2.7,
    )
    service.record_telemetry(telemetry)

    battery = VirtualBattery(
        capacity_kwh=50.0,
        current_energy_kwh=25.0,
        soc_percent=50.0,
        min_soc_percent=20.0,
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
    )
    parking = ParkingState(total_slots=0, slots=[])

    state = service.build_hardware_system_state(
        building_demand_kw=6.0,
        battery=battery,
        evs=[],
        parking=parking,
    )

    assert state.thermal.thermal_status == ThermalStatus.ELEVATED
    assert state.thermal.derating_factor < 1.0
    assert round(state.thermal.effective_capacity_kw, 2) == 15.0
    assert state.energy.grid.effective_capacity_kw == state.thermal.effective_capacity_kw
