"""Configuration management for the Smart EV Charging Management System.

Uses pydantic-settings for robust environment variable parsing, validation,
and default values without scattering magic numbers across modules.
"""

from functools import lru_cache
from pydantic import Field
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

    # Priority Weights Placeholders (Deferred implementation for Milestone 2+)
    # Note: These values are strictly configuration placeholders; no priority calculation is performed in Milestone 1.
    priority_weight_urgency: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Config placeholder for departure urgency weight in future optimizer",
    )
    priority_weight_deficit: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Config placeholder for energy deficit weight in future optimizer",
    )
    priority_weight_stay_duration: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Config placeholder for stay duration weight in future optimizer",
    )


@lru_cache()
def get_settings() -> Settings:
    """Retrieve cached application settings singleton."""
    return Settings()
