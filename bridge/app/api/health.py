"""Health check endpoint."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
