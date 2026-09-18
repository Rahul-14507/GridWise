"""System state, summary, and operational status API routes."""

from fastapi import APIRouter, Depends
from app.application.models import (
    NetworkInfoResponse,
    SystemStatusResponse,
    SystemSummaryResponse,
)
from app.application.state_service import AppStateService, get_app_state_service
from app.domain.models.system import SystemState

router = APIRouter(prefix="/system", tags=["System"])


@router.get(
    "/network-info",
    response_model=NetworkInfoResponse,
    summary="Get Server LAN Network Information",
    description="Returns the host machine's active local LAN IP address and dynamic driver deep links.",
)
def get_network_info(
    service: AppStateService = Depends(get_app_state_service),
) -> NetworkInfoResponse:
    """Return host LAN IP coordinates."""
    return service.get_network_info()


@router.get(
    "/state",
    response_model=SystemState,
    summary="Get Complete System State",
    description="Retrieves the full domain snapshot of the charging cluster.",
)
def get_system_state(
    service: AppStateService = Depends(get_app_state_service),
) -> SystemState:
    """Return the authoritative SystemState domain model."""
    return service.get_current_state()


@router.get(
    "/summary",
    response_model=SystemSummaryResponse,
    summary="Get Dashboard Summary",
    description="Returns a presentation-ready dashboard aggregation of energy, battery, fleet, parking, and warnings.",
)
def get_system_summary(
    service: AppStateService = Depends(get_app_state_service),
) -> SystemSummaryResponse:
    """Return dashboard summary response."""
    return service.get_system_summary()


@router.get(
    "/status",
    response_model=SystemStatusResponse,
    summary="Get System Operational Health",
    description="Returns high-level system status, active data source mode, runtime status, and active warnings.",
)
def get_system_status(
    service: AppStateService = Depends(get_app_state_service),
) -> SystemStatusResponse:
    """Return high-level operational status."""
    return service.get_system_status()
