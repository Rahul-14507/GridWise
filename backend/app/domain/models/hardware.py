"""Hardware telemetry domain models.

Represents raw physical measurements received from the ESP32 edge device.
Note: Solar panel voltage is only an input proxy for solar availability.
We do NOT have current/power measurement hardware on the ESP32.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Relative ambient humidity percentage (0.0% to 100.0%).",
    )
    rain_detected: bool = Field(
        default=False,
        description="Boolean flag indicating whether rain/precipitation is detected.",
    )
    rain_intensity: float = Field(
        default=0.0,
        ge=0.0,
        description="Rainfall intensity index/measurement (>= 0.0).",
    )
    solar_voltage_v: float = Field(
        ...,
        ge=0.0,
        description="Measured open-circuit or operating voltage from solar sensor (>= 0.0V). "
        "Proxy for ambient solar irradiance; not a direct power measurement.",
    )
    rain_raw: Optional[float] = Field(
        default=None,
        description="Raw ADC reading from ESP32 rain sensor for diagnostics/calibration.",
    )
    rain_status: Optional[str] = Field(
        default=None,
        description="Human-readable rain status reported by ESP32 edge device ('DRY', 'WET', 'RAIN').",
    )
    solar_status: Optional[str] = Field(
        default=None,
        description="Human-readable solar status reported by ESP32 edge device ('BRIGHT', 'DIM', 'DARK').",
    )

    @model_validator(mode="before")
    @classmethod
    def adapt_esp32_payload(cls, data: dict) -> dict:
        """Pre-process payload to populate missing fields based on ESP32 sensor logic."""
        if not isinstance(data, dict):
            return data

        # Shallow copy to avoid mutating caller's dict
        payload = dict(data)

        # Default humidity if omitted by ESP32
        if "humidity_percent" not in payload or payload["humidity_percent"] is None:
            payload["humidity_percent"] = 50.0

        # Trust rain_status if provided by ESP32
        rain_status = payload.get("rain_status")
        if rain_status is not None and isinstance(rain_status, str):
            is_dry = rain_status.strip().upper() == "DRY"
            if "rain_detected" not in payload or payload["rain_detected"] is None:
                payload["rain_detected"] = not is_dry

        if "rain_detected" not in payload or payload["rain_detected"] is None:
            payload["rain_detected"] = False

        # Compute rain intensity default if omitted
        if "rain_intensity" not in payload or payload["rain_intensity"] is None:
            payload["rain_intensity"] = 1.0 if payload.get("rain_detected") else 0.0

        return payload

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

