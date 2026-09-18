"""Electric Vehicle (EV) domain models.

Defines the state and constraints of an Electric Vehicle connected to the system.
Calculations such as priority scoring or dynamic optimization are deferred to later milestones.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EVStatus(str, Enum):
    """Lifecycle statuses for an EV within the charging facility."""

    WAITING = "waiting"
    CHARGING = "charging"
    PAUSED = "paused"
    COMPLETED = "completed"
    DISCONNECTED = "disconnected"


class EV(BaseModel):
    """Electric Vehicle domain entity representing current battery, charging state, and parking allocation."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ...,
        min_length=1,
        description="Unique vehicle identifier (e.g. EV-001).",
    )
    slot_id: Optional[str] = Field(
        default=None,
        description="Assigned parking/charging slot ID if parked, else None.",
    )
    battery_capacity_kwh: float = Field(
        ...,
        gt=0.0,
        description="Total battery capacity in kilowatt-hours (> 0).",
    )
    soc_percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Current State of Charge (SoC) percentage (0.0% to 100.0%).",
    )
    target_soc_percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Desired target State of Charge percentage (0.0% to 100.0%).",
    )
    max_charging_power_kw: float = Field(
        ...,
        gt=0.0,
        description="Maximum supported onboard charging power in kilowatts (> 0).",
    )
    arrival_time: datetime = Field(
        ...,
        description="Timezone-aware timestamp of vehicle arrival/connection.",
    )
    departure_time: datetime = Field(
        ...,
        description="Timezone-aware timestamp of expected or scheduled departure.",
    )
    allocated_power_kw: float = Field(
        default=0.0,
        ge=0.0,
        description="Currently allocated charging power in kilowatts (>= 0 and <= max_charging_power_kw).",
    )
    status: EVStatus = Field(
        default=EVStatus.WAITING,
        description="Current operational status of the vehicle.",
    )

    @field_validator("id")
    @classmethod
    def validate_id_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("id must not be empty or whitespace-only")
        return v

    @field_validator("arrival_time", "departure_time")
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("Time must be timezone-aware (tzinfo cannot be None)")
        return v

    @model_validator(mode="after")
    def validate_ev_constraints(self) -> "EV":
        if self.departure_time <= self.arrival_time:
            raise ValueError("departure_time must be strictly after arrival_time")
        if self.allocated_power_kw > self.max_charging_power_kw:
            raise ValueError(
                f"allocated_power_kw ({self.allocated_power_kw}) cannot exceed "
                f"max_charging_power_kw ({self.max_charging_power_kw})"
            )
        return self
