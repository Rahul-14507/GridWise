"""Optimizer domain models.

Defines decision structures, deadline statuses, and explainable allocation results
produced by the ChargingOptimizer.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.models.simulation import SimulationControlInput


class DeadlineStatus(str, Enum):
    """Feasibility assessment of an EV reaching its target State of Charge before scheduled departure."""

    FEASIBLE = "feasible"      # Required average power <= max charger rate; on track
    AT_RISK = "at_risk"        # Required average power > max charger rate; deadline at risk
    EXPIRED = "expired"        # Departure time has passed but target SoC not yet reached
    COMPLETE = "complete"      # Vehicle is at or above target SoC; no further charging required


class BatteryAction(str, Enum):
    """Operational decision for the Virtual Battery Energy Storage System (BESS)."""

    IDLE = "idle"
    DISCHARGE = "discharge"
    CHARGE = "charge"


class EVAllocationDecision(BaseModel):
    """Detailed allocation decision and explainability breakdown for an individual EV."""

    model_config = ConfigDict(frozen=True)

    ev_id: str = Field(..., description="Unique vehicle identifier.")
    allocated_power_kw: float = Field(
        ...,
        ge=0.0,
        description="Power allocated to this EV for the upcoming interval in kW (>= 0).",
    )
    priority_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized composite priority score (0.0 to 1.0).",
    )
    soc_urgency: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized SoC deficit urgency component (0.0 to 1.0).",
    )
    departure_urgency: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized departure proximity urgency component (0.0 to 1.0).",
    )
    energy_deficit_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized energy deficit fraction of total battery capacity (0.0 to 1.0).",
    )
    waiting_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized waiting time fairness component (0.0 to 1.0).",
    )
    required_average_power_kw: float = Field(
        ...,
        ge=0.0,
        description="Minimum average power in kW required to meet target SoC before departure.",
    )
    deadline_status: DeadlineStatus = Field(
        ...,
        description="Evaluation of deadline feasibility.",
    )
    reason: str = Field(
        ...,
        min_length=1,
        description="Explainable machine-readable reason for the allocation decision.",
    )


class OptimizationDecision(BaseModel):
    """Complete, constraint-validated decision payload produced by the ChargingOptimizer."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(
        ...,
        description="Timezone-aware timestamp corresponding to the evaluated SystemState.",
    )
    available_ev_power_kw: float = Field(
        ...,
        ge=0.0,
        description="Net infrastructure capacity available for EV charging in kW.",
    )
    total_allocated_power_kw: float = Field(
        ...,
        ge=0.0,
        description="Total power allocated across all connected EVs in kW (<= available_ev_power_kw).",
    )
    allocations: List[EVAllocationDecision] = Field(
        default_factory=list,
        description="Detailed power allocations and priority breakdowns per EV.",
    )
    battery_action: BatteryAction = Field(
        default=BatteryAction.IDLE,
        description="Determined stationary battery operational dispatch action.",
    )
    battery_power_kw: float = Field(
        default=0.0,
        ge=0.0,
        description="Target battery charge or discharge power in kW.",
    )
    infrastructure_load_kw: float = Field(
        ...,
        ge=0.0,
        description="Estimated net electrical load on grid interconnection in kW.",
    )
    effective_capacity_kw: float = Field(
        ...,
        ge=0.0,
        description="Effective (thermally derated) transformer capacity limit in kW.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Operational alerts, deadline warnings, or infrastructure constraint notifications.",
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("timestamp must be timezone-aware")
        return v

    def get_allocations_dict(self) -> Dict[str, float]:
        """Extract a dictionary mapping EV ID -> allocated_power_kw."""
        return {item.ev_id: item.allocated_power_kw for item in self.allocations}

    def to_control_input(self) -> SimulationControlInput:
        """Convert this optimization decision into a SimulationControlInput payload."""
        charge_power = self.battery_power_kw if self.battery_action == BatteryAction.CHARGE else 0.0
        discharge_power = self.battery_power_kw if self.battery_action == BatteryAction.DISCHARGE else 0.0
        return SimulationControlInput(
            ev_allocations=self.get_allocations_dict(),
            battery_charge_power_kw=charge_power,
            battery_discharge_power_kw=discharge_power,
        )
