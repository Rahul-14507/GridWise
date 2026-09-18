"""Hardware telemetry domain models.

Represents raw physical measurements received from the ESP32 edge device.
Note: Solar panel voltage is only an input proxy for solar availability.
We do NOT have current/power measurement hardware on the ESP32.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HardwareTelemetry(BaseModel):
    """Raw telemetry payload reported by the ESP32 hardware device."""

    model_config = ConfigDict(frozen=True)

    device_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier of the reporting hardware device.",
    )
    timestamp: datetime = Field(
        ...,
        description="Timezone-aware timestamp when the telemetry reading was captured.",
    )
    temperature_c: float = Field(
        ...,
        ge=-50.0,
        le=80.0,
        description="Ambient temperature in Celsius (-50.0°C to 80.0°C).",
    )
    humidity_percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Relative ambient humidity percentage (0.0% to 100.0%).",
    )
    rain_detected: bool = Field(
        ...,
        description="Boolean flag indicating whether rain/precipitation is detected.",
    )
    rain_intensity: float = Field(
        ...,
        ge=0.0,
        description="Rainfall intensity index/measurement (>= 0.0).",
    )
    solar_voltage_v: float = Field(
        ...,
        ge=0.0,
        description="Measured open-circuit or operating voltage from solar sensor (>= 0.0V). "
        "Proxy for ambient solar irradiance; not a direct power measurement.",
    )

    @field_validator("device_id")
    @classmethod
    def validate_device_id_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("device_id must not be empty or whitespace-only")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("timestamp must be timezone-aware (tzinfo cannot be None)")
        return v
