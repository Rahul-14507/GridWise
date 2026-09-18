"""Optimization API endpoints.

Provides endpoints to inspect current decisions, manually trigger optimization runs,
and apply decisions to the simulation engine.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.application.models import OptimizationApplyResponse
from app.application.state_service import AppStateService, get_app_state_service
from app.optimizer.models import OptimizationDecision

router = APIRouter(prefix="/optimization", tags=["Optimization"])


@router.get(
    "/current",
    response_model=OptimizationDecision,
    summary="Get Current Optimization Decision",
    description="Retrieves the most recent OptimizationDecision computed by the optimizer.",
)
def get_current_optimization(
    service: AppStateService = Depends(get_app_state_service),
) -> OptimizationDecision:
    """Return the latest cached optimization decision."""
    decision = service.get_latest_decision()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No optimization decision has been computed yet. Trigger one with POST /api/v1/optimization/run",
        )
    return decision


@router.post(
    "/run",
    response_model=OptimizationDecision,
    summary="Run Optimizer on Current System State",
    description="Executes the ChargingOptimizer on the current state, caches the decision, and returns it.",
)
def run_optimization(
    service: AppStateService = Depends(get_app_state_service),
) -> OptimizationDecision:
    """Trigger an optimization computation cycle."""
    try:
        return service.run_optimization()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Optimization failed: {str(e)}",
        )


@router.post(
    "/apply",
    response_model=OptimizationApplyResponse,
    summary="Apply Optimization Decision to Simulation",
    description="Applies power allocations and battery commands from the latest decision to the simulation.",
)
def apply_optimization_decision(
    service: AppStateService = Depends(get_app_state_service),
) -> OptimizationApplyResponse:
    """Apply the current optimization decision to the simulation engine."""
    try:
        return service.apply_optimization_to_simulation()
    except ValueError as e:
        msg = str(e)
        if "hardware mode" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=msg,
            )
        elif "No optimization decision" in msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
