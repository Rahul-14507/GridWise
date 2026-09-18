"""Hardware telemetry service.

Provides in-memory ingestion, multi-device tracking, connectivity freshness
evaluation, and SystemState synthesis from real ESP32 edge sensor telemetry.
"""

from datetime import datetime, timezone
from functools import lru_cache
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.config.settings import Settings, get_settings
from app.domain.models.battery import VirtualBattery
from app.domain.models.ev import EV
from app.domain.models.hardware import HardwareTelemetry
from app.domain.models.parking import ParkingState
from app.domain.models.system import SystemState
from app.domain.services.system_state_service import SystemStateService


class HardwareDeviceStatus(BaseModel):
    """Connectivity and freshness status for an individual hardware device."""

    model_config = ConfigDict(frozen=True)

    device_id: str = Field(..., description="Device identifier")
    is_connected: bool = Field(..., description="True if received telemetry within stale timeout")
    is_stale: bool = Field(..., description="True if telemetry age exceeds stale timeout")
    last_seen: Optional[datetime] = Field(None, description="Timestamp of the most recent telemetry")
    age_seconds: Optional[float] = Field(None, ge=0.0, description="Seconds elapsed since last reading")
    total_readings: int = Field(0, ge=0, description="Total readings received from this device")
    latest_telemetry: Optional[HardwareTelemetry] = Field(None, description="Most recent telemetry snapshot")


class HardwareStatusSummary(BaseModel):
    """Aggregate hardware status across all reporting devices."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(..., description="Overall hardware health ('online', 'stale', 'no_data')")
    data_source: str = Field(..., description="Configured active data source mode")
    timeout_seconds: float = Field(..., description="Configured timeout threshold for staleness")
    total_devices: int = Field(0, ge=0, description="Total unique devices recorded")
    active_devices: int = Field(0, ge=0, description="Number of actively reporting, non-stale devices")
    stale_devices: int = Field(0, ge=0, description="Number of devices with stale telemetry")
    devices: Dict[str, HardwareDeviceStatus] = Field(default_factory=dict, description="Per-device status details")


class TelemetryReceipt(BaseModel):
    """Acknowledgement receipt returned upon successful telemetry ingestion."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(default="accepted", description="Ingestion status")
    device_id: str = Field(..., description="Device identifier from the ingested payload")
    reading_timestamp: datetime = Field(..., description="Timestamp reported by the hardware device")
    recorded_at: datetime = Field(..., description="Server timestamp when telemetry was processed")
    message: str = Field(default="Telemetry ingested successfully", description="Status message")


class HardwareTelemetryService:
    """In-memory service managing ESP32 telemetry ingestion and hardware state."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._devices_telemetry: Dict[str, HardwareTelemetry] = {}
        self._devices_counts: Dict[str, int] = {}
        self._devices_last_recorded_at: Dict[str, datetime] = {}
        self._latest_global_telemetry: Optional[HardwareTelemetry] = None

    def record_telemetry(
        self,
        telemetry: HardwareTelemetry,
        recorded_at: Optional[datetime] = None,
    ) -> TelemetryReceipt:
        """Ingest, validate, and record incoming ESP32 telemetry.

        Args:
            telemetry: Validated HardwareTelemetry payload.
            recorded_at: Optional server recording timestamp. Defaults to UTC now.

        Returns:
            TelemetryReceipt confirming ingestion.
        """
        now = recorded_at or datetime.now(timezone.utc)

        device_id = telemetry.device_id
        self._devices_telemetry[device_id] = telemetry
        self._devices_counts[device_id] = self._devices_counts.get(device_id, 0) + 1
        self._devices_last_recorded_at[device_id] = now
        self._latest_global_telemetry = telemetry

        return TelemetryReceipt(
            status="accepted",
            device_id=device_id,
            reading_timestamp=telemetry.timestamp,
            recorded_at=now,
            message=f"Telemetry from '{device_id}' recorded successfully",
        )

    def get_latest_telemetry(self, device_id: Optional[str] = None) -> Optional[HardwareTelemetry]:
        """Retrieve the latest telemetry for a specific device, or global latest if omitted."""
        if device_id is not None:
            return self._devices_telemetry.get(device_id)
        return self._latest_global_telemetry

    def get_all_device_ids(self) -> List[str]:
        """Return list of all known device IDs."""
        return sorted(list(self._devices_telemetry.keys()))

    def get_device_status(
        self,
        device_id: str,
        current_time: Optional[datetime] = None,
    ) -> Optional[HardwareDeviceStatus]:
        """Compute freshness and connection status for a specific device.

        Args:
            device_id: Unique hardware identifier.
            current_time: Reference time for age calculation. Defaults to UTC now.

        Returns:
            HardwareDeviceStatus, or None if device has never been seen.
        """
        telemetry = self._devices_telemetry.get(device_id)
        if telemetry is None:
            return None

        now = current_time or datetime.now(timezone.utc)
        ref_timestamp = self._devices_last_recorded_at.get(device_id, telemetry.timestamp)

        if ref_timestamp.tzinfo is None:
            ref_timestamp = ref_timestamp.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        age_seconds = max(0.0, (now - ref_timestamp).total_seconds())
        timeout = self._settings.hardware_telemetry_timeout_seconds
        is_stale = age_seconds > timeout
        is_connected = not is_stale

        return HardwareDeviceStatus(
            device_id=device_id,
            is_connected=is_connected,
            is_stale=is_stale,
            last_seen=ref_timestamp,
            age_seconds=age_seconds,
            total_readings=self._devices_counts.get(device_id, 0),
            latest_telemetry=telemetry,
        )

    def get_status_summary(
        self,
        current_time: Optional[datetime] = None,
    ) -> HardwareStatusSummary:
        """Compute overall hardware connectivity and per-device status summary."""
        now = current_time or datetime.now(timezone.utc)
        device_statuses: Dict[str, HardwareDeviceStatus] = {}

        active_count = 0
        stale_count = 0

        for dev_id in self.get_all_device_ids():
            status = self.get_device_status(dev_id, current_time=now)
            if status is not None:
                device_statuses[dev_id] = status
                if status.is_connected:
                    active_count += 1
                else:
                    stale_count += 1

        total_devices = len(device_statuses)
        if total_devices == 0:
            overall_status = "no_data"
        elif active_count > 0:
            overall_status = "online"
        else:
            overall_status = "stale"

        return HardwareStatusSummary(
            status=overall_status,
            data_source=self._settings.telemetry_data_source,
            timeout_seconds=self._settings.hardware_telemetry_timeout_seconds,
            total_devices=total_devices,
            active_devices=active_count,
            stale_devices=stale_count,
            devices=device_statuses,
        )

    def build_hardware_system_state(
        self,
        building_demand_kw: float,
        battery: VirtualBattery,
        evs: List[EV],
        parking: ParkingState,
        device_id: Optional[str] = None,
        battery_discharge_kw: float = 0.0,
        settings: Optional[Settings] = None,
    ) -> SystemState:
        """Construct a SystemState domain model using latest real hardware telemetry.

        Raises:
            ValueError: If no hardware telemetry has been received for the specified device.
        """
        telemetry = self.get_latest_telemetry(device_id=device_id)
        if telemetry is None:
            dev_msg = f" for device '{device_id}'" if device_id else ""
            raise ValueError(f"No hardware telemetry available{dev_msg} to build SystemState")

        cfg = settings or self._settings

        return SystemStateService.build_system_state(
            timestamp=telemetry.timestamp,
            environment=telemetry,
            base_grid_capacity_kw=cfg.default_grid_capacity_kw,
            solar_min_voltage_v=cfg.solar_min_voltage_v,
            solar_max_voltage_v=cfg.solar_max_voltage_v,
            solar_capacity_kw=cfg.solar_capacity_kw,
            thermal_derating_start_c=cfg.thermal_derating_start_c,
            thermal_critical_temp_c=cfg.thermal_critical_temperature_c,
            thermal_min_capacity_kw=cfg.minimum_grid_capacity_kw,
            building_demand_kw=building_demand_kw,
            battery=battery,
            evs=evs,
            parking=parking,
            battery_discharge_kw=battery_discharge_kw,
        )

    def clear(self) -> None:
        """Reset all in-memory telemetry and device registries (useful for testing)."""
        self._devices_telemetry.clear()
        self._devices_counts.clear()
        self._devices_last_recorded_at.clear()
        self._latest_global_telemetry = None


@lru_cache()
def get_hardware_telemetry_service() -> HardwareTelemetryService:
    """Retrieve singleton HardwareTelemetryService instance."""
    return HardwareTelemetryService()
