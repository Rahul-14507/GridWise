"""Tests for Electric Vehicle (EV) domain models."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from pydantic import ValidationError

from app.domain.models.ev import EV, EVStatus


def test_ev_model_valid():
    """Verify standard valid EV instance creation."""
    now = datetime.now(timezone.utc)
    ev = EV(
        id="EV-001",
        slot_id="SLOT-01",
        battery_capacity_kwh=60.0,
        soc_percent=30.0,
        target_soc_percent=90.0,
        max_charging_power_kw=7.4,
        arrival_time=now,
        departure_time=now + timedelta(hours=2),
        allocated_power_kw=7.4,
        status=EVStatus.CHARGING,
    )
    assert ev.id == "EV-001"
    assert ev.battery_capacity_kwh == 60.0
    assert ev.soc_percent == 30.0
    assert ev.target_soc_percent == 90.0
    assert ev.max_charging_power_kw == 7.4
    assert ev.allocated_power_kw == 7.4
    assert ev.status == EVStatus.CHARGING


def test_ev_models_from_fixture():
    """Verify loading from tests/fixtures/evs.json contract."""
    fixture_path = Path(__file__).parent / "fixtures" / "evs.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    evs = [EV.model_validate(item) for item in data]
    assert len(evs) == 4
    assert evs[0].id == "EV-001"
    assert evs[0].soc_percent == 22.0
    assert evs[1].id == "EV-002"
    assert evs[1].soc_percent == 61.0
    assert evs[2].id == "EV-003"
    assert evs[2].soc_percent == 34.0
    assert evs[3].id == "EV-004"
    assert evs[3].soc_percent == 82.0


@pytest.mark.parametrize("soc", [-1.0, 100.1, -10.0, 120.0])
def test_ev_invalid_soc(soc):
    """Verify invalid SoC percentages are rejected."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError) as exc_info:
        EV(
            id="EV-001",
            battery_capacity_kwh=60.0,
            soc_percent=soc,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=now,
            departure_time=now + timedelta(hours=2),
        )
    assert "soc_percent" in str(exc_info.value)


@pytest.mark.parametrize("target_soc", [-1.0, 100.1])
def test_ev_invalid_target_soc(target_soc):
    """Verify invalid target SoC percentages are rejected."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError) as exc_info:
        EV(
            id="EV-001",
            battery_capacity_kwh=60.0,
            soc_percent=50.0,
            target_soc_percent=target_soc,
            max_charging_power_kw=7.4,
            arrival_time=now,
            departure_time=now + timedelta(hours=2),
        )
    assert "target_soc_percent" in str(exc_info.value)


@pytest.mark.parametrize("capacity", [0.0, -10.0, -0.01])
def test_ev_negative_battery_capacity(capacity):
    """Verify non-positive battery capacity is rejected."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError) as exc_info:
        EV(
            id="EV-001",
            battery_capacity_kwh=capacity,
            soc_percent=50.0,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=now,
            departure_time=now + timedelta(hours=2),
        )
    assert "battery_capacity_kwh" in str(exc_info.value)


@pytest.mark.parametrize("max_power", [0.0, -7.4])
def test_ev_invalid_max_charging_power(max_power):
    """Verify non-positive maximum charging power is rejected."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError) as exc_info:
        EV(
            id="EV-001",
            battery_capacity_kwh=60.0,
            soc_percent=50.0,
            target_soc_percent=90.0,
            max_charging_power_kw=max_power,
            arrival_time=now,
            departure_time=now + timedelta(hours=2),
        )
    assert "max_charging_power_kw" in str(exc_info.value)


def test_ev_allocated_power_exceeding_max():
    """Verify allocated power cannot exceed maximum charging power."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError) as exc_info:
        EV(
            id="EV-001",
            battery_capacity_kwh=60.0,
            soc_percent=50.0,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            allocated_power_kw=11.0,
            arrival_time=now,
            departure_time=now + timedelta(hours=2),
        )
    assert "cannot exceed" in str(exc_info.value)


def test_ev_invalid_departure_before_arrival():
    """Verify departure time before or equal to arrival time is rejected."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError) as exc_info:
        EV(
            id="EV-001",
            battery_capacity_kwh=60.0,
            soc_percent=50.0,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=now,
            departure_time=now - timedelta(minutes=10),
        )
    assert "departure_time must be strictly after arrival_time" in str(exc_info.value)


def test_ev_naive_timestamp_rejected():
    """Verify naive arrival/departure datetimes are rejected."""
    naive_arrival = datetime(2026, 9, 18, 9, 0, 0)
    naive_departure = datetime(2026, 9, 18, 11, 0, 0)
    with pytest.raises(ValidationError) as exc_info:
        EV(
            id="EV-001",
            battery_capacity_kwh=60.0,
            soc_percent=50.0,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=naive_arrival,
            departure_time=naive_departure,
        )
    assert "timezone-aware" in str(exc_info.value)
