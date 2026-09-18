"""Application-layer response models and data contracts for Phase 5 API."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SystemWarning(BaseModel):
    """Structured factual system warning representation."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(..., description="Machine-readable warning code (e.g. EV_DEADLINE_AT_RISK)")
    severity: str = Field(..., description="Warning severity: 'info', 'warning', or 'critical'")
    message: str = Field(..., description="Human-readable warning explanation")


class EnergySummary(BaseModel):
    """Condensed energy metrics for dashboard presentation."""

    model_config = ConfigDict(frozen=True)

    grid_capacity_kw: float = Field(..., ge=0.0, description="Nominal rated grid capacity in kW")
    effective_capacity_kw: float = Field(..., ge=0.0, description="Thermally derated effective grid capacity in kW")
    building_demand_kw: float = Field(..., ge=0.0, description="Facility baseload power demand in kW")
    solar_generation_kw: float = Field(..., ge=0.0, description="Estimated solar PV generation in kW")
    available_ev_power_kw: float = Field(..., ge=0.0, description="Net power capacity available for EV charging in kW")


class BatterySummary(BaseModel):
    """Condensed stationary battery status for dashboard presentation."""

    model_config = ConfigDict(frozen=True)

    soc_percent: float = Field(..., ge=0.0, le=100.0, description="Current battery State of Charge percentage")
    current_energy_kwh: float = Field(..., ge=0.0, description="Stored energy in kWh")
    capacity_kwh: float = Field(..., gt=0.0, description="Total battery capacity in kWh")
    action: str = Field(default="idle", description="Current battery operational mode ('idle', 'charge', 'discharge')")


class EVSummary(BaseModel):
    """Aggregated EV fleet count metrics for dashboard presentation."""

    model_config = ConfigDict(frozen=True)

    total: int = Field(0, ge=0, description="Total number of connected EVs")
    charging: int = Field(0, ge=0, description="Number of EVs currently drawing charge")
    waiting: int = Field(0, ge=0, description="Number of EVs queued and waiting for power allocation")
    paused: int = Field(0, ge=0, description="Number of EVs with temporarily paused charging")
    completed: int = Field(0, ge=0, description="Number of EVs that reached target SoC")
    disconnected: int = Field(0, ge=0, description="Number of disconnected EVs")


class ParkingSummary(BaseModel):
    """Aggregated parking bay occupancy metrics for dashboard presentation."""

    model_config = ConfigDict(frozen=True)

    total_slots: int = Field(0, ge=0, description="Total designated charging bays")
    occupied_slots: int = Field(0, ge=0, description="Number of occupied bays")
    available_slots: int = Field(0, ge=0, description="Number of vacant bays")


class HardwareSummary(BaseModel):
    """Condensed hardware connectivity diagnostics."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(..., description="Overall hardware status ('online', 'stale', 'no_data')")
    devices_online: int = Field(0, ge=0, description="Number of actively reporting edge devices")
    devices_stale: int = Field(0, ge=0, description="Number of devices with stale telemetry")


class SystemSummaryResponse(BaseModel):
    """Dashboard-friendly unified summary response."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(..., description="System snapshot timestamp (timezone-aware)")
    system_status: str = Field(..., description="Overall operational health ('operational', 'warning', 'degraded', 'no_data')")
    data_source: str = Field(..., description="Active telemetry source mode ('simulation' or 'hardware')")
    energy: EnergySummary = Field(..., description="Energy balance summary")
    battery: BatterySummary = Field(..., description="Stationary battery summary")
    evs: EVSummary = Field(..., description="EV fleet status counts")
    parking: ParkingSummary = Field(..., description="Parking slot occupancy summary")
    hardware: HardwareSummary = Field(..., description="Hardware sensor connectivity summary")
    warnings: List[SystemWarning] = Field(default_factory=list, description="Active factual system warnings")


class SystemStatusResponse(BaseModel):
    """High-level operational health and system status response."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(..., description="Operational status ('operational', 'warning', 'degraded', 'no_data')")
    data_source: str = Field(..., description="Configured active data source ('simulation' or 'hardware')")
    simulation_running: bool = Field(..., description="True if simulation runtime clock is advancing")
    hardware_devices_online: int = Field(..., ge=0, description="Count of connected, non-stale hardware devices")
    last_state_update: Optional[datetime] = Field(None, description="Timestamp of the most recent state calculation")
    warnings: List[SystemWarning] = Field(default_factory=list, description="Active factual system warnings")


class EnergyDetailResponse(BaseModel):
    """Detailed facility energy breakdown and power balance."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(..., description="Snapshot timestamp")
    base_grid_capacity_kw: float = Field(..., ge=0.0, description="Rated non-derated grid capacity in kW")
    effective_grid_capacity_kw: float = Field(..., ge=0.0, description="Effective thermally-derated grid capacity in kW")
    building_demand_kw: float = Field(..., ge=0.0, description="Current facility baseload power demand in kW")
    solar_voltage_v: float = Field(..., ge=0.0, description="Solar sensor voltage proxy in V")
    solar_availability_percent: float = Field(..., ge=0.0, le=100.0, description="Derived solar irradiance availability percentage")
    estimated_solar_generation_kw: float = Field(..., ge=0.0, description="Estimated solar generation in kW")
    battery_discharge_kw: float = Field(0.0, ge=0.0, description="Stationary battery active discharge contribution in kW")
    battery_charge_kw: float = Field(0.0, ge=0.0, description="Stationary battery active charging draw in kW")
    available_ev_charging_power_kw: float = Field(..., ge=0.0, description="Net power capacity available for EV fleet in kW")
    total_ev_allocated_power_kw: float = Field(0.0, ge=0.0, description="Total power currently allocated across all EVs in kW")
    infrastructure_load_kw: float = Field(..., ge=0.0, description="Net electrical load on utility interconnection in kW")


class EVDetailResponse(BaseModel):
    """Detailed status and domain calculation breakdown for an Electric Vehicle."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique EV identifier")
    slot_id: Optional[str] = Field(None, description="Assigned parking/charging bay ID")
    status: str = Field(..., description="Lifecycle status ('waiting', 'charging', 'paused', 'completed', 'disconnected')")
    battery_capacity_kwh: float = Field(..., gt=0.0, description="Total battery capacity in kWh")
    soc_percent: float = Field(..., ge=0.0, le=100.0, description="Current State of Charge percentage")
    target_soc_percent: float = Field(..., ge=0.0, le=100.0, description="Target State of Charge percentage")
    max_charging_power_kw: float = Field(..., gt=0.0, description="Maximum AC/DC charging rate in kW")
    allocated_power_kw: float = Field(0.0, ge=0.0, description="Currently allocated charging power in kW")
    arrival_time: datetime = Field(..., description="Vehicle arrival timestamp")
    departure_time: datetime = Field(..., description="Scheduled departure timestamp")
    energy_required_kwh: float = Field(..., ge=0.0, description="Remaining energy needed to reach target SoC in kWh")
    remaining_time_minutes: float = Field(..., description="Minutes remaining until scheduled departure")
    required_average_power_kw: float = Field(..., ge=0.0, description="Minimum average power required to meet deadline in kW")
    priority_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Composite priority score from latest optimization run")
    deadline_status: Optional[str] = Field(None, description="Deadline feasibility classification ('feasible', 'at_risk', 'expired', 'complete')")
    reason: Optional[str] = Field(None, description="Machine-readable allocation rationale from optimizer")


class OptimizationApplyResponse(BaseModel):
    """Confirmation receipt when an optimization decision is applied to simulation."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(default="applied", description="Application status")
    decision_timestamp: datetime = Field(..., description="Timestamp of the applied decision")
    total_allocated_kw: float = Field(..., ge=0.0, description="Total power allocated across EVs in kW")
    ev_allocations_count: int = Field(..., ge=0, description="Number of EV allocations applied")
    battery_action: str = Field(..., description="Stationary battery dispatch command applied")
    battery_power_kw: float = Field(0.0, ge=0.0, description="Target battery power in kW")
    message: str = Field(default="Optimization decision successfully applied to simulation", description="Informational message")


class NetworkInfoResponse(BaseModel):
    """Network connection coordinates for cross-device QR scanning."""

    model_config = ConfigDict(frozen=True)

    host_ip: str = Field(..., description="Active LAN IPv4 address of the GridWise server")
    frontend_port: int = Field(default=3000, description="Port number of the frontend kiosk/dashboard")
    backend_port: int = Field(default=8000, description="Port number of the backend API")
    driver_base_url: str = Field(..., description="Full base URL for driver mobile scanner landing")

