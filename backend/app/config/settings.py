"""Configuration management for the Smart EV Charging Management System.

Uses pydantic-settings for robust environment variable parsing, validation,
and default values without scattering magic numbers across modules.
"""

from functools import lru_cache
from typing import List
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application and domain configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Information
    app_name: str = Field(
        default="Smart EV Charging Management System",
        description="Application service name",
    )
    environment: str = Field(
        default="development",
        description="Deployment environment (development, staging, production)",
    )
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="Prefix for API version 1 endpoints",
    )
    cors_origins: List[str] = Field(
        default=["*"],
        description="CORS allowed origins for frontend communication",
    )

    # Telemetry & Hardware Integration Settings
    telemetry_data_source: str = Field(
        default="simulation",
        description="Active telemetry data source ('simulation' or 'hardware')",
    )
    hardware_telemetry_timeout_seconds: float = Field(
        default=300.0,
        gt=0.0,
        description="Timeout in seconds after which hardware telemetry is considered stale",
    )

    # Grid & Electrical Defaults
    default_grid_capacity_kw: float = Field(
        default=25.0,
        gt=0.0,
        description="Default grid maximum power rating in kW",
    )
    max_ev_charging_power_kw: float = Field(
        default=7.4,
        gt=0.0,
        description="Maximum charging power per EV charger slot in kW (e.g. 7.4 kW Level 2 AC)",
    )

    # Solar Calibration Parameters
    solar_min_voltage_v: float = Field(
        default=0.0,
        ge=0.0,
        description="Minimum sensor voltage corresponding to zero solar availability (V)",
    )
    solar_max_voltage_v: float = Field(
        default=3.0,
        gt=0.0,
        description="Maximum sensor voltage corresponding to 100% solar availability (V)",
    )
    solar_capacity_kw: float = Field(
        default=10.0,
        gt=0.0,
        description="Installed / nominal solar generation capacity at peak availability (kW)",
    )

    # Thermal Model & Capacity Derating Parameters
    thermal_normal_temperature_c: float = Field(
        default=25.0,
        description="Baseline ambient temperature under normal operating conditions (°C)",
    )
    thermal_derating_start_c: float = Field(
        default=35.0,
        description="Ambient temperature threshold where grid capacity derating begins (°C)",
    )
    thermal_critical_temperature_c: float = Field(
        default=50.0,
        description="Ambient temperature threshold where maximum derating is reached (°C)",
    )
    minimum_grid_capacity_kw: float = Field(
        default=10.0,
        ge=0.0,
        description="Floor grid capacity during severe thermal derating in kW",
    )

    # Building Demand Simulation Defaults
    building_base_demand_kw: float = Field(
        default=8.0,
        ge=0.0,
        description="Nominal baseline building electricity demand in kW",
    )
    building_demand_noise_percent: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="Relative random perturbation noise applied to building demand (0.05 = ±5%)",
    )

    # Virtual Battery (BESS) Simulation Defaults
    virtual_battery_capacity_kwh: float = Field(
        default=50.0,
        gt=0.0,
        description="Total storage capacity of the simulated virtual battery in kWh",
    )
    virtual_battery_min_soc_percent: float = Field(
        default=20.0,
        ge=0.0,
        le=100.0,
        description="Minimum reserve State of Charge floor percentage for virtual battery",
    )
    virtual_battery_max_charge_power_kw: float = Field(
        default=10.0,
        ge=0.0,
        description="Maximum charge power for virtual battery in kW",
    )
    virtual_battery_max_discharge_power_kw: float = Field(
        default=10.0,
        ge=0.0,
        description="Maximum discharge power for virtual battery in kW",
    )

    # Simulation Defaults
    simulation_interval_seconds: int = Field(
        default=60,
        gt=0,
        description="Interval duration between simulated telemetry and optimization cycles in seconds",
    )
    simulation_time_scale: float = Field(
        default=1.0,
        gt=0.0,
        description="Speed multiplier for simulation execution relative to real-time",
    )
    random_seed: int = Field(
        default=42,
        description="Seed for deterministic pseudo-random number generation in simulation components",
    )

    # Phase 3 Optimizer Parameters & Priority Weights
    priority_weight_soc: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Weight for current State of Charge urgency in priority scoring (0.35)",
    )
    priority_weight_departure: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Weight for departure urgency in priority scoring (0.40)",
    )
    priority_weight_deficit: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for energy deficit fraction in priority scoring (0.15)",
    )
    priority_weight_waiting: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Weight for waiting time fairness in priority scoring (0.10)",
    )

    # Legacy alias compatibility for Phase 1 placeholders if needed
    priority_weight_urgency: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Legacy alias for departure urgency weight",
    )
    priority_weight_stay_duration: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Legacy alias for stay duration / waiting weight",
    )

    departure_urgency_horizon_hours: float = Field(
        default=4.0,
        gt=0.0,
        description="Time horizon in hours where departure urgency begins ramping up",
    )
    departure_critical_horizon_hours: float = Field(
        default=1.0,
        gt=0.0,
        description="Time horizon in hours where departure is considered near-critical",
    )
    waiting_reference_minutes: float = Field(
        default=60.0,
        gt=0.0,
        description="Reference waiting duration in minutes for normalizing waiting time score to 1.0",
    )
    enable_battery_support_in_optimizer: bool = Field(
        default=True,
        description="Whether optimizer may dispatch virtual battery discharge to support EV charging deficit",
    )

    @model_validator(mode="after")
    def validate_priority_weights(self) -> "Settings":
        total_weight = (
            self.priority_weight_soc
            + self.priority_weight_departure
            + self.priority_weight_deficit
            + self.priority_weight_waiting
        )
        if not (0.999 <= total_weight <= 1.001):
            raise ValueError(
                f"Priority weights must sum to 1.0 (got sum={total_weight:.4f}: "
                f"soc={self.priority_weight_soc}, dep={self.priority_weight_departure}, "
                f"def={self.priority_weight_deficit}, wait={self.priority_weight_waiting})"
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    """Retrieve cached application settings singleton."""
    return Settings()
