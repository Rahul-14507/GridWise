"""Integration test verifying real hardware telemetry state flows through ChargingOptimizer."""

from datetime import datetime, timezone, timedelta
from app.config.settings import Settings
from app.domain.models.battery import VirtualBattery
from app.domain.models.ev import EV, EVStatus
from app.domain.models.hardware import HardwareTelemetry
from app.domain.models.parking import ParkingSlot, ParkingState
from app.infrastructure.hardware.telemetry_service import HardwareTelemetryService
from app.optimizer.optimizer import ChargingOptimizer


def test_hardware_telemetry_through_optimizer():
    settings = Settings()
    service = HardwareTelemetryService(settings=settings)
    service.clear()

    now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    # Real hardware reporting moderate temperature and full solar voltage
    telemetry = HardwareTelemetry(
        device_id="ESP32-001",
        timestamp=now,
        temperature_c=26.0,
        humidity_percent=48.0,
        rain_detected=False,
        rain_intensity=0.0,
        solar_voltage_v=3.0,  # 100% solar => 10 kW solar gen
    )
    service.record_telemetry(telemetry)

    battery = VirtualBattery(
        capacity_kwh=50.0,
        current_energy_kwh=40.0,
        soc_percent=80.0,
        min_soc_percent=20.0,
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
    )

    ev1 = EV(
        id="EV-1",
        slot_id="SLOT-1",
        arrival_time=now - timedelta(hours=1),
        departure_time=now + timedelta(hours=2),
        battery_capacity_kwh=60.0,
        soc_percent=30.0,
        target_soc_percent=80.0,
        max_charging_power_kw=7.4,
        allocated_power_kw=0.0,
        status=EVStatus.WAITING,
    )
    ev2 = EV(
        id="EV-2",
        slot_id="SLOT-2",
        arrival_time=now - timedelta(minutes=30),
        departure_time=now + timedelta(hours=4),
        battery_capacity_kwh=75.0,
        soc_percent=50.0,
        target_soc_percent=80.0,
        max_charging_power_kw=7.4,
        allocated_power_kw=0.0,
        status=EVStatus.WAITING,
    )

    parking = ParkingState(
        total_slots=2,
        slots=[
            ParkingSlot(id="SLOT-1", occupied=True, ev_id="EV-1", charging=False),
            ParkingSlot(id="SLOT-2", occupied=True, ev_id="EV-2", charging=False),
        ],
    )

    # Building demand 5 kW
    # Grid 25 kW + Solar 10 kW - Building 5 kW = 30 kW available
    system_state = service.build_hardware_system_state(
        building_demand_kw=5.0,
        battery=battery,
        evs=[ev1, ev2],
        parking=parking,
        settings=settings,
    )

    assert system_state.energy.available_ev_charging_capacity_kw == 30.0

    # Run Phase 3 optimizer on hardware-derived system state
    optimizer = ChargingOptimizer(settings=settings)
    decision = optimizer.optimize(system_state)

    alloc_map = {a.ev_id: a.allocated_power_kw for a in decision.allocations}
    assert alloc_map["EV-1"] == 7.4
    assert alloc_map["EV-2"] == 7.4
    assert decision.total_allocated_power_kw == 14.8
