"""Energy status API routes.

Provides endpoints for querying facility grid, solar, and power capacity state.
"""

from fastapi import APIRouter, Depends
from app.application.models import EnergyDetailResponse
from app.application.state_service import AppStateService, get_app_state_service

router = APIRouter(prefix="/energy", tags=["Energy"])


@router.get("", response_model=EnergyDetailResponse, summary="Get Current Energy State")
def get_energy_state(
    service: AppStateService = Depends(get_app_state_service),
) -> EnergyDetailResponse:
    """Retrieve the current facility energy state and electrical power balance."""
    return service.get_energy_detail()
