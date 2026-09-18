"""Solar domain service.

Provides mathematical conversion of physical sensor voltage measurements
into normalized solar availability and estimated solar generation in kW.
Note: We do NOT have current/power sensors on the ESP32; solar generation
is estimated based on calibrated voltage bounds and installed capacity.
"""

from app.domain.models.energy import SolarState


class SolarService:
    """Service providing solar irradiance availability and generation estimation."""

    @staticmethod
    def calculate_solar_state(
        solar_voltage_v: float,
        min_voltage_v: float,
        max_voltage_v: float,
        solar_capacity_kw: float,
    ) -> SolarState:
        """Calculate solar availability and estimated generation from raw sensor voltage.

        Formulas:
            availability = clamp((solar_voltage_v - min_voltage_v) / (max_voltage_v - min_voltage_v), 0.0, 1.0)
            availability_percent = availability * 100.0
            estimated_generation_kw = availability * solar_capacity_kw

        Edge Cases:
            - voltage <= min_voltage_v: availability = 0.0, generation = 0.0 kW
            - voltage >= max_voltage_v: availability = 1.0, generation = solar_capacity_kw
            - max_voltage_v <= min_voltage_v: raises ValueError (invalid calibration)

        Args:
            solar_voltage_v: Measured sensor voltage in Volts (>= 0.0).
            min_voltage_v: Calibrated zero-irradiance voltage floor in Volts.
            max_voltage_v: Calibrated peak-irradiance voltage ceiling in Volts.
            solar_capacity_kw: Installed solar array rated capacity in kW (> 0.0).

        Returns:
            SolarState instance with physical voltage, availability percent, and estimated generation kW.
        """
        if solar_voltage_v < 0.0:
            raise ValueError(f"solar_voltage_v must be non-negative (got {solar_voltage_v})")
        if max_voltage_v <= min_voltage_v:
            raise ValueError(
                f"max_voltage_v ({max_voltage_v}V) must be strictly greater than min_voltage_v ({min_voltage_v}V)"
            )
        if solar_capacity_kw < 0.0:
            raise ValueError(f"solar_capacity_kw must be non-negative (got {solar_capacity_kw})")

        voltage_span = max_voltage_v - min_voltage_v
        raw_availability = (solar_voltage_v - min_voltage_v) / voltage_span
        availability = max(0.0, min(1.0, raw_availability))

        estimated_kw = round(availability * solar_capacity_kw, 4)
        availability_pct = round(availability * 100.0, 2)

        return SolarState(
            solar_voltage_v=solar_voltage_v,
            availability_percent=availability_pct,
            estimated_generation_kw=estimated_kw,
        )
