"""Simulation domain models.

Defines external control inputs, thermal status models, and runtime simulation states.
Note: Control inputs represent externally supplied decisions (from tests, human operators,
or future Phase 3 optimizers), preserving strict decoupling between simulation and optimization.
"""

from enum import Enum
from typing import Dict
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ThermalStatus(str, Enum):
    """Transformer/grid operating thermal health status."""

    NORMAL = "normal"
    ELEVATED = "elevated"
    CRITICAL = "critical"


class ThermalState(BaseModel):
    """Grid capacity thermal derating assessment based on ambient temperature."""

    model_config = ConfigDict(frozen=True)

    base_capacity_kw: float = Field(
        ...,
        ge=0.0,
        description="Nominal non-derated grid capacity in kW (>= 0).",
    )
    effective_capacity_kw: float = Field(
        ...,
        ge=0.0,
        description="Thermally derated effective grid capacity in kW (>= 0).",
    )
    derating_factor: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Multiplicative derating factor applied to base capacity (0.0 to 1.0).",
    )
    thermal_status: ThermalStatus = Field(
        ...,
        description="Thermal category evaluation (normal, elevated, or critical).",
    )
    ambient_temperature_c: float = Field(
        ...,
        description="Ambient temperature driving the thermal derating calculation in °C.",
    )


class SimulationControlInput(BaseModel):
    """Externally supplied control commands applied to the simulation engine on a tick.

    In Phase 2, this is populated manually or by test fixtures.
    In Phase 3, this will be produced by the Charging Optimizer.
    """

    model_config = ConfigDict(frozen=True)

    ev_allocations: Dict[str, float] = Field(
        default_factory=dict,
        description="Mapping of EV IDs to requested charging power in kW (e.g. {'EV-001': 7.4}).",
    )
    battery_charge_power_kw: float = Field(
        default=0.0,
        ge=0.0,
        description="Requested charging power for the virtual battery in kW (>= 0).",
    )
    battery_discharge_power_kw: float = Field(
        default=0.0,
        ge=0.0,
        description="Requested discharge power from the virtual battery in kW (>= 0).",
    )

    @field_validator("ev_allocations")
    @classmethod
    def validate_allocations(cls, v: Dict[str, float]) -> Dict[str, float]:
        for ev_id, power in v.items():
            if not ev_id or not ev_id.strip():
                raise ValueError("EV ID in allocations must not be empty")
            if power < 0.0:
                raise ValueError(f"Allocated power for {ev_id} must be non-negative (got {power})")
        return v


class SimulationRunStatus(str, Enum):
    """Operational status of the simulation engine loop."""

    RUNNING = "running"
    STOPPED = "stopped"
