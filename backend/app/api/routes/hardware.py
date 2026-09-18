"""Hardware telemetry API endpoints.

Handles ingestion of real ESP32 edge sensor data, latest telemetry inspection,
and device status/staleness diagnostics.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.models.hardware import HardwareTelemetry
from app.infrastructure.hardware.telemetry_service import (
    HardwareDeviceStatus,
    HardwareStatusSummary,
    HardwareTelemetryService,
    TelemetryReceipt,
    get_hardware_telemetry_service,
)

router = APIRouter(prefix="/hardware", tags=["Hardware Telemetry"])


@router.post(
    "/telemetry",
    response_model=TelemetryReceipt,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest ESP32 hardware telemetry",
    description="Validates and records real sensor readings sent by an ESP32 edge device.",
)
def ingest_telemetry(
    telemetry: HardwareTelemetry,
    service: HardwareTelemetryService = Depends(get_hardware_telemetry_service),
) -> TelemetryReceipt:
    """Ingest, validate, and record incoming ESP32 sensor telemetry."""
    return service.record_telemetry(telemetry)


@router.get(
    "/telemetry/latest",
    response_model=HardwareTelemetry,
    summary="Get latest hardware telemetry reading",
    description="Retrieves the most recent telemetry received globally or for a specific device.",
)
def get_latest_telemetry(
    device_id: Optional[str] = Query(None, description="Optional device ID filter"),
    service: HardwareTelemetryService = Depends(get_hardware_telemetry_service),
) -> HardwareTelemetry:
    """Retrieve the latest valid telemetry snapshot."""
    telemetry = service.get_latest_telemetry(device_id=device_id)
    if telemetry is None:
        detail = (
            f"No hardware telemetry available for device '{device_id}'"
            if device_id
            else "No hardware telemetry has been received yet"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return telemetry


@router.get(
    "/status",
    response_model=HardwareStatusSummary,
    summary="Get hardware connectivity and staleness status",
    description="Returns aggregate health, data source mode, and per-device freshness metrics.",
)
def get_hardware_status(
    service: HardwareTelemetryService = Depends(get_hardware_telemetry_service),
) -> HardwareStatusSummary:
    """Return hardware status summary across all recorded devices."""
    return service.get_status_summary()


@router.get(
    "/devices/{device_id}/status",
    response_model=HardwareDeviceStatus,
    summary="Get individual device status",
    description="Returns connectivity status and freshness diagnostics for a specific device.",
)
def get_device_status(
    device_id: str,
    service: HardwareTelemetryService = Depends(get_hardware_telemetry_service),
) -> HardwareDeviceStatus:
    """Return status diagnostics for a specific hardware device."""
    dev_status = service.get_device_status(device_id)
    if dev_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' has not reported any telemetry",
        )
    return dev_status
