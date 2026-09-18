"""EV fleet API routes.

Provides endpoints for querying connected Electric Vehicles and charging allocations.
"""

from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter
from app.domain.models.ev import EV, EVStatus

router = APIRouter(prefix="/evs", tags=["EVs"])


@router.get("", response_model=List[EV], summary="Get Connected EVs")
async def get_evs() -> List[EV]:
    """Retrieve connected Electric Vehicles (simulated/placeholder in Milestone 1)."""
    now = datetime.now(timezone.utc)
    return [
        EV(
            id="EV-001",
            slot_id="SLOT-01",
            battery_capacity_kwh=60.0,
            soc_percent=22.0,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=now - timedelta(minutes=45),
            departure_time=now + timedelta(hours=1, minutes=30),
            allocated_power_kw=7.4,
            status=EVStatus.CHARGING,
        ),
        EV(
            id="EV-002",
            slot_id="SLOT-02",
            battery_capacity_kwh=75.0,
            soc_percent=61.0,
            target_soc_percent=90.0,
            max_charging_power_kw=11.0,
            arrival_time=now - timedelta(minutes=20),
            departure_time=now + timedelta(hours=4),
            allocated_power_kw=5.5,
            status=EVStatus.CHARGING,
        ),
        EV(
            id="EV-003",
            slot_id="SLOT-03",
            battery_capacity_kwh=50.0,
            soc_percent=34.0,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=now - timedelta(minutes=10),
            departure_time=now + timedelta(hours=1),
            allocated_power_kw=0.0,
            status=EVStatus.WAITING,
        ),
        EV(
            id="EV-004",
            slot_id="SLOT-04",
            battery_capacity_kwh=100.0,
            soc_percent=82.0,
            target_soc_percent=90.0,
            max_charging_power_kw=22.0,
            arrival_time=now - timedelta(hours=2),
            departure_time=now + timedelta(hours=6),
            allocated_power_kw=3.7,
            status=EVStatus.CHARGING,
        ),
    ]
