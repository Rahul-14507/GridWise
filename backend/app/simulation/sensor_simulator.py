"""Sensor telemetry simulator.

Generates realistic, deterministic physical sensor readings adhering to the ESP32 Hardware JSON contract.
Note: Solar panel voltage is simulated as raw sensor voltage (0.0 to 3.0V), NOT electrical power.
"""

import math
from datetime import datetime
from typing import Optional
from app.domain.models.hardware import HardwareTelemetry


class SensorSimulator:
    """Simulates physical sensor telemetry from the ESP32 edge device."""

    def __init__(
        self,
        device_id: str = "ESP32-SIM-001",
        base_temperature_c: float = 28.0,
        base_humidity_percent: float = 55.0,
        max_solar_voltage_v: float = 2.85,
    ) -> None:
        """Initialize sensor simulator.

        Args:
            device_id: Unique hardware identifier for simulated device.
            base_temperature_c: Baseline midday temperature in °C.
            base_humidity_percent: Baseline ambient humidity in %.
            max_solar_voltage_v: Maximum achievable solar panel voltage in V.
        """
        self.device_id = device_id
        self.base_temperature_c = base_temperature_c
        self.base_humidity_percent = base_humidity_percent
        self.max_solar_voltage_v = max_solar_voltage_v

        # Scenario overrides (when active)
        self.override_temperature_c: Optional[float] = None
        self.override_humidity_percent: Optional[float] = None
        self.override_rain_detected: Optional[bool] = None
        self.override_rain_intensity: Optional[float] = None
        self.override_solar_voltage_v: Optional[float] = None

    def set_overrides(
        self,
        temperature_c: Optional[float] = None,
        humidity_percent: Optional[float] = None,
        rain_detected: Optional[bool] = None,
        rain_intensity: Optional[float] = None,
        solar_voltage_v: Optional[float] = None,
    ) -> None:
        """Set explicit environmental overrides (used by Scenarios)."""
        self.override_temperature_c = temperature_c
        self.override_humidity_percent = humidity_percent
        self.override_rain_detected = rain_detected
        self.override_rain_intensity = rain_intensity
        self.override_solar_voltage_v = solar_voltage_v

    def clear_overrides(self) -> None:
        """Clear all active scenario overrides."""
        self.override_temperature_c = None
        self.override_humidity_percent = None
        self.override_rain_detected = None
        self.override_rain_intensity = None
        self.override_solar_voltage_v = None

    def generate_telemetry(self, timestamp: datetime) -> HardwareTelemetry:
        """Generate a HardwareTelemetry payload for the given timestamp.

        Args:
            timestamp: Current simulation timestamp (timezone-aware).

        Returns:
            Validated HardwareTelemetry instance.
        """
        # Calculate time of day in fractional hours (0.0 to 24.0)
        hour = timestamp.hour + timestamp.minute / 60.0 + timestamp.second / 3600.0

        # 1. Solar voltage curve: peaks at 13:00 (1:00 PM), zero before 06:00 and after 18:00
        if self.override_solar_voltage_v is not None:
            solar_voltage = self.override_solar_voltage_v
        else:
            if 6.0 <= hour <= 18.0:
                # Half-sine curve between sunrise (6am) and sunset (6pm)
                progress = (hour - 6.0) / 12.0
                solar_voltage = self.max_solar_voltage_v * math.sin(progress * math.pi)
            else:
                solar_voltage = 0.0

        # 2. Temperature curve: diurnal cycle lagging solar peak (peaks ~15:00)
        if self.override_temperature_c is not None:
            temperature = self.override_temperature_c
        else:
            diurnal_variation = 6.0 * math.sin(((hour - 9.0) / 24.0) * 2.0 * math.pi)
            temperature = self.base_temperature_c + diurnal_variation

        # 3. Humidity curve: inversely proportional to temperature
        if self.override_humidity_percent is not None:
            humidity = self.override_humidity_percent
        else:
            humidity = self.base_humidity_percent - (temperature - self.base_temperature_c) * 1.5
            humidity = max(10.0, min(95.0, humidity))

        # 4. Rain status
        rain_detected = self.override_rain_detected if self.override_rain_detected is not None else False
        rain_intensity = self.override_rain_intensity if self.override_rain_intensity is not None else 0.0

        return HardwareTelemetry(
            device_id=self.device_id,
            timestamp=timestamp,
            temperature_c=round(temperature, 2),
            humidity_percent=round(humidity, 2),
            rain_detected=rain_detected,
            rain_intensity=round(rain_intensity, 2),
            solar_voltage_v=round(max(0.0, solar_voltage), 3),
        )
