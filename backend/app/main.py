"""Main FastAPI application entrypoint for Smart EV Charging Management System."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import get_settings
from app.api.routes.health import router as health_router
from app.api.routes.energy import router as energy_router
from app.api.routes.evs import router as evs_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Smart EV Charging Management System Backend (Milestone 1)",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health endpoint (GET /health)
app.include_router(health_router)

# Versioned API routes (GET /api/v1/energy, GET /api/v1/evs, etc.)
app.include_router(energy_router, prefix=settings.api_v1_prefix)
app.include_router(evs_router, prefix=settings.api_v1_prefix)
app.include_router(health_router, prefix=settings.api_v1_prefix)


@app.get("/", summary="Root index")
async def root() -> dict:
    """Root metadata response."""
    return {
        "service": settings.app_name,
        "milestone": "Milestone 1 - Backend Foundation",
        "docs": "/docs",
        "health": "/health",
    }
