"""Health check API routes."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health Check")
async def get_health() -> dict:
    """Return basic service health status."""
    return {"status": "ok"}
