"""System State service.

Orchestrates domain models and calculations to assemble a coherent SystemState snapshot.
"""

from datetime import datetime
from typing import List

from app.domain.models.hardware import HardwareTelemetry
from app.domain.models.energy import GridState, SolarState, EnergyState
from app.domain.models.battery import VirtualBattery
from app.domain.models.ev import EV
from app.domain.models.parking import ParkingState
from app.domain.models.simulation import ThermalState
from app.domain.models.system import SystemState
from app.domain.services.solar_service import SolarService
from app.domain.services.thermal_service import ThermalService
from app.domain.services.energy_service import EnergyService


class SystemStateService:
    """Service assembling and verifying complete SystemState domain snapshots."""

    @staticmethod
    def build_system_state(
        timestamp: datetime,
        environment: HardwareTelemetry,
        base_grid_capacity_kw: float,
        solar_min_voltage_v: float,
        solar_max_voltage_v: float,
        solar_capacity_kw: float,
        thermal_derating_start_c: float,
        thermal_critical_temp_c: float,
        thermal_min_capacity_kw: float,
        building_demand_kw: float,
        battery: VirtualBattery,
        evs: List[EV],
        parking: ParkingState,
        battery_discharge_kw: float = 0.0,
    ) -> SystemState:
        """Construct a validated SystemState snapshot from individual component inputs.

        Args:
            timestamp: Snapshot timestamp (timezone-aware).
            environment: Sensor telemetry payload (ESP32 data contract).
            base_grid_capacity_kw: Non-derated nominal grid capacity in kW.
            solar_min_voltage_v: Minimum solar calibration voltage in V.
            solar_max_voltage_v: Peak solar calibration voltage in V.
            solar_capacity_kw: Rated solar generation capacity in kW.
            thermal_derating_start_c: Threshold where thermal derating begins in °C.
            thermal_critical_temp_c: Threshold where critical thermal limit is reached in °C.
            thermal_min_capacity_kw: Minimum grid capacity under severe thermal stress in kW.
            building_demand_kw: Baseload facility power demand in kW.
            battery: Current VirtualBattery state.
            evs: Connected EV fleet list.
            parking: Parking slots and occupancy state.
            battery_discharge_kw: Active battery power contribution in kW.

        Returns:
            Fully instantiated and consistent SystemState domain object.
        """
        # 1. Calculate Solar State
        solar_state: SolarState = SolarService.calculate_solar_state(
            solar_voltage_v=environment.solar_voltage_v,
            min_voltage_v=solar_min_voltage_v,
            max_voltage_v=solar_max_voltage_v,
            solar_capacity_kw=solar_capacity_kw,
        )

        # 2. Calculate Thermal & Effective Grid Capacity
        thermal_state: ThermalState = ThermalService.calculate_thermal_derating(
            temperature_c=environment.temperature_c,
            base_capacity_kw=base_grid_capacity_kw,
            derating_start_c=thermal_derating_start_c,
            critical_temp_c=thermal_critical_temp_c,
            min_capacity_kw=thermal_min_capacity_kw,
        )

        # 3. Calculate Available EV Charging Capacity
        effective_capacity_kw = thermal_state.effective_capacity_kw
        available_ev_power = EnergyService.calculate_available_ev_power(
            grid_capacity_kw=effective_capacity_kw,
            building_demand_kw=building_demand_kw,
            solar_generation_kw=solar_state.estimated_generation_kw,
            battery_discharge_kw=battery_discharge_kw,
        )

        # 4. Construct Grid and Energy States
        grid_state = GridState(
            max_capacity_kw=base_grid_capacity_kw,
            building_demand_kw=building_demand_kw,
            effective_capacity_kw=effective_capacity_kw,
        )

        energy_state = EnergyState(
            grid=grid_state,
            solar=solar_state,
            available_ev_charging_capacity_kw=available_ev_power,
        )

        return SystemState(
            timestamp=timestamp,
            environment=environment,
            energy=energy_state,
            thermal=thermal_state,
            battery=battery,
            evs=evs,
            parking=parking,
        )
