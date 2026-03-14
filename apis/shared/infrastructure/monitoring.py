"""Monitoring endpoints — health, readiness, liveness."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/readiness")
async def readiness():
    """Readiness probe — checks dependencies are available."""
    return {"status": "ready"}


@router.get("/liveness")
async def liveness():
    """Liveness probe — confirms the process is alive."""
    return {"status": "alive"}
