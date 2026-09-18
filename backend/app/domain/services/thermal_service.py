"""Thermal domain service.

Provides deterministic mathematical modeling for temperature-induced grid and transformer capacity derating.
Note: This is a simulation model and does not claim to directly measure physical transformer internal temperatures.
"""

from app.domain.models.simulation import ThermalState, ThermalStatus


class ThermalService:
    """Service evaluating thermal stress and computing effective grid power derating."""

    @staticmethod
    def calculate_thermal_derating(
        temperature_c: float,
        base_capacity_kw: float,
        derating_start_c: float,
        critical_temp_c: float,
        min_capacity_kw: float,
    ) -> ThermalState:
        """Calculate effective grid capacity and derating factor based on ambient temperature.

        Behavior:
            - temperature <= derating_start_c:
                derating_factor = 1.0
                effective_capacity = base_capacity_kw
                status = NORMAL
            - derating_start_c < temperature < critical_temp_c:
                linear interpolation between base_capacity_kw and min_capacity_kw
                status = ELEVATED
            - temperature >= critical_temp_c:
                effective_capacity = min_capacity_kw
                status = CRITICAL

        Args:
            temperature_c: Current ambient temperature in °C.
            base_capacity_kw: Nominal non-derated grid interconnection rating in kW (>= 0).
            derating_start_c: Temperature threshold where derating begins in °C.
            critical_temp_c: Temperature threshold where maximum derating is reached in °C.
            min_capacity_kw: Floor grid capacity under critical thermal conditions in kW (>= 0).

        Returns:
            ThermalState domain model instance.
        """
        if base_capacity_kw < 0.0:
            raise ValueError(f"base_capacity_kw must be non-negative (got {base_capacity_kw})")
        if min_capacity_kw < 0.0:
            raise ValueError(f"min_capacity_kw must be non-negative (got {min_capacity_kw})")
        if min_capacity_kw > base_capacity_kw:
            raise ValueError(
                f"min_capacity_kw ({min_capacity_kw} kW) cannot exceed base_capacity_kw ({base_capacity_kw} kW)"
            )
        if critical_temp_c <= derating_start_c:
            raise ValueError(
                f"critical_temp_c ({critical_temp_c}°C) must be strictly greater than derating_start_c ({derating_start_c}°C)"
            )

        if temperature_c <= derating_start_c:
            factor = 1.0
            effective_kw = base_capacity_kw
            status = ThermalStatus.NORMAL
        elif temperature_c >= critical_temp_c:
            effective_kw = min_capacity_kw
            factor = min_capacity_kw / base_capacity_kw if base_capacity_kw > 0 else 0.0
            status = ThermalStatus.CRITICAL
        else:
            # Linear derating between start and critical
            span = critical_temp_c - derating_start_c
            ratio = (temperature_c - derating_start_c) / span
            effective_kw = base_capacity_kw - ratio * (base_capacity_kw - min_capacity_kw)
            factor = effective_kw / base_capacity_kw if base_capacity_kw > 0 else 0.0
            status = ThermalStatus.ELEVATED

        return ThermalState(
            base_capacity_kw=round(base_capacity_kw, 4),
            effective_capacity_kw=round(effective_kw, 4),
            derating_factor=round(factor, 4),
            thermal_status=status,
            ambient_temperature_c=round(temperature_c, 2),
        )
