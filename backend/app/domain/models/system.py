"""System State domain model.

Unifies environmental telemetry, energy balances, thermal derating, virtual battery storage,
EV fleet states, and parking occupancy into a single coherent snapshot of the charging cluster.
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.models.hardware import HardwareTelemetry
from app.domain.models.energy import EnergyState
from app.domain.models.battery import VirtualBattery
from app.domain.models.ev import EV, EVStatus
from app.domain.models.parking import ParkingState
from app.domain.models.simulation import ThermalState


class SystemState(BaseModel):
    """Unified system state snapshot representing the charging cluster at a point in simulation time."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(
        ...,
        description="Timezone-aware timestamp for this system state snapshot.",
    )
    environment: HardwareTelemetry = Field(
        ...,
        description="Current ambient environmental sensor telemetry (ESP32 data contract).",
    )
    energy: EnergyState = Field(
        ...,
        description="Grid capacity, solar state, and net available charging power.",
    )
    thermal: ThermalState = Field(
        ...,
        description="Thermal derating evaluation for the grid/transformer interconnection.",
    )
    battery: VirtualBattery = Field(
        ...,
        description="Current state of the software-simulated Virtual Battery (BESS).",
    )
    evs: List[EV] = Field(
        default_factory=list,
        description="List of all connected Electric Vehicles in the facility.",
    )
    parking: ParkingState = Field(
        ...,
        description="Physical slot occupancy and charging bay assignments.",
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("timestamp must be timezone-aware (tzinfo cannot be None)")
        return v

    @property
    def available_ev_charging_capacity_kw(self) -> float:
        """Net electrical power budget available for EV charging in kW."""
        return self.energy.available_ev_charging_capacity_kw or 0.0

    @property
    def total_ev_allocated_power_kw(self) -> float:
        """Total power currently allocated across all connected EVs in kW."""
        return round(sum(ev.allocated_power_kw for ev in self.evs), 4)

    @property
    def active_charging_ev_count(self) -> int:
        """Count of EVs currently drawing positive charging power."""
        return sum(
            1 for ev in self.evs if ev.allocated_power_kw > 0.0 and ev.status == EVStatus.CHARGING
        )

    @property
    def available_parking_slots(self) -> int:
        """Count of unoccupied parking slots."""
        return self.parking.available_slots

    @property
    def occupied_parking_slots(self) -> int:
        """Count of occupied parking slots."""
        return self.parking.occupied_slots
