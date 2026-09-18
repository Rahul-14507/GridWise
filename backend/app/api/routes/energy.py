"""Energy status API routes.

Provides endpoints for querying facility grid, solar, and power capacity state.
"""

from fastapi import APIRouter
from app.domain.models.energy import EnergyState, GridState, SolarState
from app.domain.services.energy_service import EnergyService

router = APIRouter(prefix="/energy", tags=["Energy"])


@router.get("", response_model=EnergyState, summary="Get Current Energy State")
async def get_energy_state() -> EnergyState:
    """Retrieve the current facility energy state (simulated/placeholder in Milestone 1)."""
    grid = GridState(
        max_capacity_kw=25.0,
        building_demand_kw=8.0,
        effective_capacity_kw=17.0,
    )
    solar = SolarState(
        solar_voltage_v=2.14,
        availability_percent=42.8,
        estimated_generation_kw=5.0,
    )
    available_power = EnergyService.calculate_available_ev_power(
        grid_capacity_kw=grid.max_capacity_kw,
        building_demand_kw=grid.building_demand_kw,
        solar_generation_kw=solar.estimated_generation_kw,
        battery_discharge_kw=2.0,
    )

    return EnergyState(
        grid=grid,
        solar=solar,
        available_ev_charging_capacity_kw=available_power,
    )
