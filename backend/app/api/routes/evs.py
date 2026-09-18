from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.application.models import EVDetailResponse
from app.application.state_service import AppStateService, get_app_state_service
from app.domain.models.qr_session import EVRegistrationRequest, QRSession

router = APIRouter(prefix="/evs", tags=["EVs"])


@router.get("", response_model=List[EVDetailResponse], summary="Get Connected EVs")
def get_evs(
    service: AppStateService = Depends(get_app_state_service),
) -> List[EVDetailResponse]:
    """Retrieve all connected Electric Vehicles with charging metrics and optimization status."""
    return service.get_evs_detail()


@router.post("/qr-session", response_model=QRSession, status_code=status.HTTP_201_CREATED, summary="Create QR Session")
def create_qr_session(
    bay_id: Optional[str] = Query(None, description="Optional bay ID (e.g. BAY-04)"),
    service: AppStateService = Depends(get_app_state_service),
) -> QRSession:
    """Generate a unique single-use QR onboarding session for charging station kiosks."""
    return service.create_qr_session(bay_id=bay_id)


@router.get("/qr-session/{session_id}", response_model=QRSession, summary="Get QR Session Status")
def get_qr_session(
    session_id: str,
    service: AppStateService = Depends(get_app_state_service),
) -> QRSession:
    """Retrieve session state by unique token."""
    session = service.get_qr_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"QR Session '{session_id}' not found",
        )
    return session


@router.post("/qr-session/{session_id}/claim", response_model=QRSession, summary="Claim QR Session")
def claim_qr_session(
    session_id: str,
    service: AppStateService = Depends(get_app_state_service),
) -> QRSession:
    """Mark a QR code as scanned/claimed so the kiosk immediately expires the token."""
    try:
        return service.claim_qr_session(session_id)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post("/register", response_model=EVDetailResponse, status_code=status.HTTP_201_CREATED, summary="Register Driver EV")
def register_driver_ev(
    request: EVRegistrationRequest,
    service: AppStateService = Depends(get_app_state_service),
) -> EVDetailResponse:
    """Onboard and register a new vehicle into the charging fleet via mobile QR scan."""
    try:
        return service.register_driver_ev(request)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))


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

