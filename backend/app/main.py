"""Main FastAPI application entrypoint for Smart EV Charging Management System."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import get_settings
from app.api.routes.health import router as health_router
from app.api.routes.energy import router as energy_router
from app.api.routes.evs import router as evs_router
from app.api.routes.simulation import router as simulation_router
from app.api.routes.hardware import router as hardware_router
from app.api.routes.system import router as system_router
from app.api.routes.optimization import router as optimization_router
from app.api.routes.parking import router as parking_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Smart EV Charging Management System Backend (Phase 8 - Parking Vision / OpenCV Integration)",
    version="0.8.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health endpoint (GET /health)
app.include_router(health_router)

# Versioned API routes
app.include_router(system_router, prefix=settings.api_v1_prefix)
app.include_router(energy_router, prefix=settings.api_v1_prefix)
app.include_router(evs_router, prefix=settings.api_v1_prefix)
app.include_router(optimization_router, prefix=settings.api_v1_prefix)
app.include_router(simulation_router, prefix=settings.api_v1_prefix)
app.include_router(hardware_router, prefix=settings.api_v1_prefix)
app.include_router(parking_router, prefix=settings.api_v1_prefix)
app.include_router(health_router, prefix=settings.api_v1_prefix)


@app.get("/", summary="Root index")
async def root() -> dict:
    """Root metadata response."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "phase": "Phase 8 - Parking Vision / OpenCV Integration",
        "data_source": settings.telemetry_data_source,
        "docs": "/docs",
        "health": "/health",
        "system_summary": f"{settings.api_v1_prefix}/system/summary",
        "system_state": f"{settings.api_v1_prefix}/system/state",
        "energy": f"{settings.api_v1_prefix}/energy",
        "evs": f"{settings.api_v1_prefix}/evs",
        "optimization": f"{settings.api_v1_prefix}/optimization/current",
        "hardware_status": f"{settings.api_v1_prefix}/hardware/status",
        "simulation": f"{settings.api_v1_prefix}/simulation/state",
        "parking_vision": f"{settings.api_v1_prefix}/parking/state",
    }
