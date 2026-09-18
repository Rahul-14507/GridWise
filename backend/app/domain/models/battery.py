"""Virtual Battery domain models.

Represents a software-simulated Battery Energy Storage System (BESS).
This battery does NOT physically exist on the hardware edge device.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VirtualBattery(BaseModel):
    """Software-simulated Battery Energy Storage System (BESS)."""

    model_config = ConfigDict(frozen=True)

    capacity_kwh: float = Field(
        ...,
        gt=0.0,
        description="Total storage capacity in kilowatt-hours (> 0).",
    )
    soc_percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Current State of Charge percentage (0.0% to 100.0%).",
    )
    max_charge_power_kw: float = Field(
        ...,
        ge=0.0,
        description="Maximum rate at which the virtual battery can charge in kW (>= 0).",
    )
    max_discharge_power_kw: float = Field(
        ...,
        ge=0.0,
        description="Maximum rate at which the virtual battery can discharge in kW (>= 0).",
    )
    efficiency_percent: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="Round-trip storage efficiency percentage (0.0% to 100.0%).",
    )
    minimum_soc_percent: float = Field(
        default=20.0,
        ge=0.0,
        le=100.0,
        description="Configured reserve floor / minimum State of Charge percentage (0.0% to 100.0%).",
    )

    @model_validator(mode="after")
    def validate_minimum_soc(self) -> "VirtualBattery":
        if self.minimum_soc_percent > self.soc_percent:
            raise ValueError(
                f"minimum_soc_percent ({self.minimum_soc_percent}%) cannot exceed "
                f"current soc_percent ({self.soc_percent}%)"
            )
        return self
