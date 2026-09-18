"""API routes package."""

from app.api.routes.health import router as health_router
from app.api.routes.energy import router as energy_router
from app.api.routes.evs import router as evs_router
from app.api.routes.simulation import router as simulation_router
from app.api.routes.hardware import router as hardware_router
from app.api.routes.system import router as system_router
from app.api.routes.optimization import router as optimization_router

__all__ = [
    "health_router",
    "energy_router",
    "evs_router",
    "simulation_router",
    "hardware_router",
    "system_router",
    "optimization_router",
]
