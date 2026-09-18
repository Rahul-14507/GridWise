"""Simulation control and state API routes.

Provides endpoints for running, stepping, resetting, querying, and optimizing the charging cluster simulation.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.domain.models.simulation import SimulationControlInput
from app.domain.models.system import SystemState
from app.optimizer.models import OptimizationDecision
from app.optimizer.optimizer import ChargingOptimizer
from app.simulation.engine import get_simulation_engine
from app.simulation.scenarios import ScenarioManager

router = APIRouter(prefix="/simulation", tags=["Simulation"])


class ScenarioInfo(BaseModel):
    """Metadata description of a simulation scenario."""

    name: str = Field(..., description="Uppercase scenario identifier.")
    description: str = Field(..., description="Summary of scenario conditions.")


class OptimizeTickResponse(BaseModel):
    """Combined response payload for an optimized simulation tick."""

    state: SystemState = Field(..., description="Updated SystemState after applying optimal allocation.")
    decision: OptimizationDecision = Field(..., description="The optimization decision computed by ChargingOptimizer.")


@router.get("/state", response_model=SystemState, summary="Get Current System State")
async def get_simulation_state() -> SystemState:
    """Retrieve the complete current SystemState snapshot of the charging cluster."""
    engine = get_simulation_engine()
    return engine.get_state()


@router.post("/tick", response_model=SystemState, summary="Advance Simulation Tick")
async def advance_simulation_tick(
    control_input: Optional[SimulationControlInput] = None,
    interval_seconds: Optional[float] = Query(
        default=None,
        gt=0.0,
        description="Optional tick step duration override in seconds",
    ),
) -> SystemState:
    """Advance the simulation clock by one tick, apply control inputs, and return new SystemState."""
    engine = get_simulation_engine()
    try:
        return engine.tick(
            control_input=control_input,
            interval_seconds=interval_seconds,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/optimize-tick",
    response_model=OptimizeTickResponse,
    summary="Compute Optimization & Advance Tick",
)
async def optimize_and_advance_tick(
    interval_seconds: Optional[float] = Query(
        default=None,
        gt=0.0,
        description="Optional tick step duration override in seconds",
    ),
) -> OptimizeTickResponse:
    """Run ChargingOptimizer on current state, apply resulting allocations to simulator, and advance one tick."""
    engine = get_simulation_engine()
    current_state = engine.get_state()
    optimizer = ChargingOptimizer()

    try:
        decision = optimizer.optimize(
            system_state=current_state,
            simulation_interval_seconds=interval_seconds,
        )
        updated_state = engine.tick(
            control_input=decision.to_control_input(),
            interval_seconds=interval_seconds,
        )
        return OptimizeTickResponse(state=updated_state, decision=decision)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/start", summary="Start Simulation Progression")
async def start_simulation() -> Dict[str, str]:
    """Start the simulation runtime loop."""
    engine = get_simulation_engine()
    engine.start()
    return {"status": "running"}


@router.post("/stop", summary="Stop Simulation Progression")
async def stop_simulation() -> Dict[str, str]:
    """Pause/stop the simulation runtime loop."""
    engine = get_simulation_engine()
    engine.stop()
    return {"status": "stopped"}


@router.post("/reset", response_model=SystemState, summary="Reset Simulation State")
async def reset_simulation() -> SystemState:
    """Reset the current scenario to its starting conditions."""
    engine = get_simulation_engine()
    return engine.reset()


@router.get("/scenarios", response_model=List[ScenarioInfo], summary="List Available Scenarios")
async def list_scenarios() -> List[ScenarioInfo]:
    """Return all available predefined simulation scenarios."""
    scenarios = ScenarioManager.get_all_scenarios()
    return [
        ScenarioInfo(name=s.name, description=s.description)
        for s in scenarios.values()
    ]


@router.post(
    "/scenarios/{scenario_name}",
    response_model=SystemState,
    summary="Load and Activate Scenario",
)
async def load_scenario(scenario_name: str) -> SystemState:
    """Load a specific scenario by name and reinitialize simulation state."""
    engine = get_simulation_engine()
    try:
        return engine.load_scenario(scenario_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
