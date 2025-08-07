"""User summary and export endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/{user_id}/summary")
async def summary(user_id: UUID, window: str = "30d") -> dict:
    """Return basic metrics for ``user_id``.

    This is a stub implementation that returns empty aggregates.  The
    real implementation would query the database and generate trend
    charts.  The endpoint is nevertheless useful for end-to-end testing
    of the API surface.
    """

    return {"user_id": str(user_id), "window": window, "lesion_counts": {}}
