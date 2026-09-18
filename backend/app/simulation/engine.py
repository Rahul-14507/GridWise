"""Central Simulation Engine.

Coordinates all simulation components (Clock, Sensors, Grid, Solar, Thermal, Battery, EVs, Parking)
to evolve system state across discrete simulation ticks and construct unified SystemState snapshots.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.config.settings import Settings, get_settings
from app.domain.models.simulation import SimulationControlInput, SimulationRunStatus
from app.domain.models.system import SystemState
from app.domain.services.system_state_service import SystemStateService
from app.simulation.clock import SimulationClock
from app.simulation.sensor_simulator import SensorSimulator
from app.simulation.grid_simulator import GridSimulator
from app.simulation.ev_simulator import EVSimulator
from app.simulation.battery_simulator import BatterySimulator
from app.simulation.parking_simulator import ParkingSimulator
from app.simulation.scenarios import Scenario, ScenarioManager

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Core simulation engine orchestrating the physical state evolution of the EV charging cluster."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        scenario_name: str = "NORMAL_DAY",
    ) -> None:
        """Initialize Simulation Engine.

        Args:
            settings: Application configuration settings. Defaults to cached get_settings().
            scenario_name: Initial scenario to load. Defaults to 'NORMAL_DAY'.
        """
        self.settings = settings or get_settings()
        self.current_scenario_name = scenario_name
        self.status = SimulationRunStatus.STOPPED

        # Subcomponent initialization
        self.clock = SimulationClock()
        self.sensor_sim = SensorSimulator(
            device_id="ESP32-SIM-001",
            max_solar_voltage_v=self.settings.solar_max_voltage_v,
        )
        self.grid_sim = GridSimulator(
            base_grid_capacity_kw=self.settings.default_grid_capacity_kw,
            noise_percent=self.settings.building_demand_noise_percent,
            random_seed=self.settings.random_seed,
        )
        self.ev_sim = EVSimulator()
        self.battery_sim = BatterySimulator()
        self.parking_sim = ParkingSimulator()

        # Load initial scenario
        self.load_scenario(self.current_scenario_name)

    def load_scenario(self, scenario_name: str) -> SystemState:
        """Load a predefined scenario and reset simulation components to its initial state.

        Args:
            scenario_name: Name of the scenario (e.g. 'NORMAL_DAY', 'HOT_DAY').

        Returns:
            Initial SystemState snapshot of the newly loaded scenario.
        """
        scenario: Scenario = ScenarioManager.get_scenario(scenario_name)
        self.current_scenario_name = scenario.name

        # Reset clock
        self.clock.reset(scenario.initial_time)

        # Apply environmental overrides
        self.sensor_sim.set_overrides(
            temperature_c=scenario.temperature_c,
            humidity_percent=scenario.humidity_percent,
            rain_detected=scenario.rain_detected,
            rain_intensity=scenario.rain_intensity,
            solar_voltage_v=scenario.solar_voltage_v,
        )

        # Apply building demand overrides
        self.grid_sim.set_demand_override(scenario.building_demand_kw)
        self.grid_sim.reset_seed(self.settings.random_seed)

        # Set initial components
        self.battery_sim.set_battery(scenario.battery)
        self.ev_sim.set_evs(scenario.evs)
        self.parking_sim.set_state(scenario.parking)
        self.parking_sim.sync_with_evs(scenario.evs)

        # Generate initial state
        return self._build_current_state(battery_discharge_kw=0.0)

    def reset(self) -> SystemState:
        """Reset the current scenario to its starting conditions."""
        return self.load_scenario(self.current_scenario_name)

    def start(self) -> None:
        """Mark simulation status as running."""
        self.status = SimulationRunStatus.RUNNING
        logger.info("[SIM] Simulation started.")

    def stop(self) -> None:
        """Mark simulation status as stopped."""
        self.status = SimulationRunStatus.STOPPED
        logger.info("[SIM] Simulation stopped.")

    def get_state(self) -> SystemState:
        """Retrieve the current SystemState without advancing time."""
        return self._build_current_state(
            battery_discharge_kw=self.battery_sim.last_discharge_power_kw
        )

    def tick(
        self,
        control_input: Optional[SimulationControlInput] = None,
        interval_seconds: Optional[float] = None,
    ) -> SystemState:
        """Advance the simulation by one discrete time step and return the resulting SystemState.

        Execution Order:
            1. Advance simulation clock.
            2. Generate ambient environmental telemetry.
            3. Apply external virtual battery commands.
            4. Apply external EV charging allocations.
            5. Synchronize parking bay occupancy with EV fleet.
            6. Sample building electricity demand.
            7. Synthesize complete SystemState domain model.

        Args:
            control_input: Externally provided EV allocations and battery commands.
            interval_seconds: Optional step duration in seconds (defaults to settings configuration).

        Returns:
            Updated SystemState domain model.
        """
        dt_seconds = (
            interval_seconds
            if interval_seconds is not None
            else self.settings.simulation_interval_seconds * self.settings.simulation_time_scale
        )
        if dt_seconds <= 0.0:
            raise ValueError(f"Step interval must be strictly positive (got {dt_seconds}s)")

        # 1. Advance Clock
        current_time = self.clock.advance(dt_seconds)

        # 2. Extract Controls
        ev_allocations = control_input.ev_allocations if control_input else {}
        battery_charge_kw = control_input.battery_charge_power_kw if control_input else 0.0
        battery_discharge_kw = control_input.battery_discharge_power_kw if control_input else 0.0

        # 3. Step Battery
        _, active_battery_power, _ = self.battery_sim.step(
            duration_seconds=dt_seconds,
            charge_power_kw=battery_charge_kw,
            discharge_power_kw=battery_discharge_kw,
        )

        # 4. Step EVs
        updated_evs = self.ev_sim.step(
            current_time=current_time,
            duration_seconds=dt_seconds,
            allocations=ev_allocations,
        )

        # 5. Sync Parking
        self.parking_sim.sync_with_evs(updated_evs)

        # 6. Build and return SystemState
        state = self._build_current_state(
            battery_discharge_kw=self.battery_sim.last_discharge_power_kw
        )

        # High-level simulation log
        logger.info(
            f"[SIM] {current_time.strftime('%H:%M:%S')} | "
            f"Temp: {state.environment.temperature_c}°C | "
            f"Solar: {state.energy.solar.estimated_generation_kw:.2f}kW | "
            f"Demand: {state.energy.grid.building_demand_kw:.2f}kW | "
            f"Avail EV Power: {state.available_ev_charging_capacity_kw:.2f}kW | "
            f"EVs Charging: {state.active_charging_ev_count}"
        )

        return state

    def _build_current_state(self, battery_discharge_kw: float) -> SystemState:
        """Assemble current SystemState from internal simulators."""
        current_time = self.clock.current_time
        telemetry = self.sensor_sim.generate_telemetry(current_time)
        building_demand = self.grid_sim.get_building_demand_kw(current_time)

        return SystemStateService.build_system_state(
            timestamp=current_time,
            environment=telemetry,
            base_grid_capacity_kw=self.settings.default_grid_capacity_kw,
            solar_min_voltage_v=self.settings.solar_min_voltage_v,
            solar_max_voltage_v=self.settings.solar_max_voltage_v,
            solar_capacity_kw=self.settings.solar_capacity_kw,
            thermal_derating_start_c=self.settings.thermal_derating_start_c,
            thermal_critical_temp_c=self.settings.thermal_critical_temperature_c,
            thermal_min_capacity_kw=self.settings.minimum_grid_capacity_kw,
            building_demand_kw=building_demand,
            battery=self.battery_sim.battery,
            evs=self.ev_sim.evs,
            parking=self.parking_sim.state,
            battery_discharge_kw=battery_discharge_kw,
        )


# Global singleton engine instance for API and runtime sharing
_simulation_engine_instance: Optional[SimulationEngine] = None


def get_simulation_engine() -> SimulationEngine:
    """Retrieve or create the global SimulationEngine singleton."""
    global _simulation_engine_instance
    if _simulation_engine_instance is None:
        _simulation_engine_instance = SimulationEngine()
    return _simulation_engine_instance
