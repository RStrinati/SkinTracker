"""Pydantic models for the public API."""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class ProcessImageRequest(BaseModel):
    image_id: UUID | None = None
    bucket_path: str | None = None
    force: bool = False


class LesionOut(BaseModel):
    lesion_id: UUID | None = None
    bbox: Dict[str, int]
    confidence: float
    type: str
    region: str | None = None
    area_px: int | None = None
    redness_score: float | None = None


class ProcessImageResponse(BaseModel):
    image_id: UUID
    contour_overlay_url: str | None = None
    lesions: List[LesionOut] = []
