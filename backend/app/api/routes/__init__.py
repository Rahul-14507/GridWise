"""API routes package."""

from app.api.routes.health import router as health_router
from app.api.routes.energy import router as energy_router
from app.api.routes.evs import router as evs_router
from app.api.routes.simulation import router as simulation_router

__all__ = ["health_router", "energy_router", "evs_router", "simulation_router"]
