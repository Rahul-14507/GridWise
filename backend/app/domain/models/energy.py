"""Energy domain models.

Represents grid capacity, solar state, and overall facility energy balance.
Note:
- solar_voltage_v is the actual physical sensor measurement.
- availability_percent and estimated_generation_kw are derived/modelled values.
- Grid capacity and building demand are simulated values in Milestone 1.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class GridState(BaseModel):
    """Grid supply limits and building demand state."""

    model_config = ConfigDict(frozen=True)

    max_capacity_kw: float = Field(
        ...,
        ge=0.0,
        description="Maximum rated grid interconnection capacity in kW (>= 0).",
    )
    building_demand_kw: float = Field(
        ...,
        ge=0.0,
        description="Current baseload/facility power demand in kW (>= 0).",
    )
    effective_capacity_kw: float = Field(
        ...,
        ge=0.0,
        description="Effective grid capacity available for EV infrastructure in kW (>= 0).",
    )


class SolarState(BaseModel):
    """Solar photovoltaic generation telemetry and modelled generation."""

    model_config = ConfigDict(frozen=True)

    solar_voltage_v: float = Field(
        ...,
        ge=0.0,
        description="Physical sensor voltage measurement from the solar panel/proxy (>= 0.0V).",
    )
    availability_percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Modelled/derived solar irradiance availability index (0.0% to 100.0%).",
    )
    estimated_generation_kw: float = Field(
        ...,
        ge=0.0,
        description="Derived/estimated solar generation power in kW based on solar model (>= 0.0).",
    )


class EnergyState(BaseModel):
    """Aggregated facility energy snapshot."""

    model_config = ConfigDict(frozen=True)

    grid: GridState = Field(
        ...,
        description="Current grid status and facility demand.",
    )
    solar: SolarState = Field(
        ...,
        description="Current solar measurement and generation estimate.",
    )
    available_ev_charging_capacity_kw: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Derived capacity in kW currently available for EV charging (optional state snapshot).",
    )
