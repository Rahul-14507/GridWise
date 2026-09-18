"""Unit tests for HardwareTelemetryService."""

from datetime import datetime, timezone, timedelta
import pytest

from app.config.settings import Settings
from app.domain.models.battery import VirtualBattery
from app.domain.models.ev import EV, EVStatus
from app.domain.models.hardware import HardwareTelemetry
from app.domain.models.parking import ParkingSlot, ParkingState
from app.infrastructure.hardware.telemetry_service import (
    HardwareTelemetryService,
)


@pytest.fixture
def sample_telemetry() -> HardwareTelemetry:
    return HardwareTelemetry(
        device_id="ESP32-001",
        timestamp=datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc),
        temperature_c=32.5,
        humidity_percent=55.0,
        rain_detected=False,
        rain_intensity=0.0,
        solar_voltage_v=2.4,
    )


@pytest.fixture
def service() -> HardwareTelemetryService:
    settings = Settings(hardware_telemetry_timeout_seconds=300.0)
    svc = HardwareTelemetryService(settings=settings)
    svc.clear()
    return svc


def test_record_and_get_latest_telemetry(service, sample_telemetry):
    receipt = service.record_telemetry(sample_telemetry)
    assert receipt.status == "accepted"
    assert receipt.device_id == "ESP32-001"

    latest = service.get_latest_telemetry()
    assert latest is not None
    assert latest.device_id == "ESP32-001"
    assert latest.temperature_c == 32.5

    device_latest = service.get_latest_telemetry("ESP32-001")
    assert device_latest == latest

    assert service.get_latest_telemetry("UNKNOWN") is None


def test_multi_device_tracking(service):
    t1 = HardwareTelemetry(
        device_id="ESP32-A",
        timestamp=datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc),
        temperature_c=25.0,
        humidity_percent=50.0,
        rain_detected=False,
        rain_intensity=0.0,
        solar_voltage_v=1.5,
    )
    t2 = HardwareTelemetry(
        device_id="ESP32-B",
        timestamp=datetime(2026, 9, 18, 12, 1, 0, tzinfo=timezone.utc),
        temperature_c=30.0,
        humidity_percent=60.0,
        rain_detected=True,
        rain_intensity=5.0,
        solar_voltage_v=0.5,
    )

    service.record_telemetry(t1)
    service.record_telemetry(t2)

    assert service.get_all_device_ids() == ["ESP32-A", "ESP32-B"]
    assert service.get_latest_telemetry("ESP32-A").temperature_c == 25.0
    assert service.get_latest_telemetry("ESP32-B").temperature_c == 30.0
    # Global latest is the most recently recorded (ESP32-B)
    assert service.get_latest_telemetry().device_id == "ESP32-B"


def test_device_freshness_and_stale_detection(service):
    now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    t = HardwareTelemetry(
        device_id="ESP32-001",
        timestamp=now,
        temperature_c=28.0,
        humidity_percent=45.0,
        rain_detected=False,
        rain_intensity=0.0,
        solar_voltage_v=2.0,
    )

    service.record_telemetry(t, recorded_at=now)

    # 1 minute later: Fresh (< 300s)
    status_fresh = service.get_device_status("ESP32-001", current_time=now + timedelta(seconds=60))
    assert status_fresh is not None
    assert status_fresh.is_connected is True
    assert status_fresh.is_stale is False
    assert status_fresh.age_seconds == 60.0

    # 6 minutes later: Stale (> 300s)
    status_stale = service.get_device_status("ESP32-001", current_time=now + timedelta(seconds=360))
    assert status_stale is not None
    assert status_stale.is_connected is False
    assert status_stale.is_stale is True
    assert status_stale.age_seconds == 360.0


def test_status_summary(service):
    now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    # Empty service
    empty_summary = service.get_status_summary(current_time=now)
    assert empty_summary.status == "no_data"
    assert empty_summary.total_devices == 0

    t1 = HardwareTelemetry(
        device_id="ESP32-ACTIVE",
        timestamp=now,
        temperature_c=25.0,
        humidity_percent=50.0,
        rain_detected=False,
        rain_intensity=0.0,
        solar_voltage_v=1.5,
    )
    t2 = HardwareTelemetry(
        device_id="ESP32-STALE",
        timestamp=now - timedelta(seconds=400),
        temperature_c=26.0,
        humidity_percent=52.0,
        rain_detected=False,
        rain_intensity=0.0,
        solar_voltage_v=1.0,
    )
    service.record_telemetry(t1, recorded_at=now)
    service.record_telemetry(t2, recorded_at=now - timedelta(seconds=400))

    summary = service.get_status_summary(current_time=now)
    assert summary.status == "online"
    assert summary.total_devices == 2
    assert summary.active_devices == 1
    assert summary.stale_devices == 1


def test_build_hardware_system_state(service, sample_telemetry):
    service.record_telemetry(sample_telemetry)

    battery = VirtualBattery(
        capacity_kwh=50.0,
        current_energy_kwh=25.0,
        soc_percent=50.0,
        min_soc_percent=20.0,
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
    )
    now = sample_telemetry.timestamp
    ev = EV(
        id="EV-1",
        slot_id="SLOT-1",
        arrival_time=now,
        departure_time=now + timedelta(hours=3),
        battery_capacity_kwh=60.0,
        soc_percent=40.0,
        target_soc_percent=80.0,
        max_charging_power_kw=7.4,
        allocated_power_kw=0.0,
        status=EVStatus.WAITING,
    )
    parking = ParkingState(
        total_slots=1,
        slots=[ParkingSlot(id="SLOT-1", occupied=True, ev_id="EV-1", charging=False)],
    )

    state = service.build_hardware_system_state(
        building_demand_kw=5.0,
        battery=battery,
        evs=[ev],
        parking=parking,
    )

    assert state.environment.device_id == "ESP32-001"
    assert state.environment.temperature_c == 32.5
    assert state.energy.solar.solar_voltage_v == 2.4
    # Solar generation = (2.4 / 3.0) * 10.0 = 8.0 kW
    assert state.energy.solar.estimated_generation_kw == 8.0
