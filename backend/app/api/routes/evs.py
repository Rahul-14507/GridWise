"""EV fleet API routes.

Provides endpoints for querying connected Electric Vehicles, charging metrics, and individual EV status.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.application.models import EVDetailResponse
from app.application.state_service import AppStateService, get_app_state_service

router = APIRouter(prefix="/evs", tags=["EVs"])


@router.get("", response_model=List[EVDetailResponse], summary="Get Connected EVs")
def get_evs(
    service: AppStateService = Depends(get_app_state_service),
) -> List[EVDetailResponse]:
    """Retrieve all connected Electric Vehicles with charging metrics and optimization status."""
    return service.get_evs_detail()


@router.get("/{ev_id}", response_model=EVDetailResponse, summary="Get Individual EV")
def get_ev_by_id(
    ev_id: str,
    service: AppStateService = Depends(get_app_state_service),
) -> EVDetailResponse:
    """Retrieve detailed state for a specific EV by ID."""
    ev = service.get_ev_detail(ev_id)
    if ev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EV with identifier '{ev_id}' not found",
        )
    return ev
