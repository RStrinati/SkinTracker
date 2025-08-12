from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from analysis_providers.insightface_provider import InsightFaceProvider
from utils.db import upsert_face_embeddings
from utils.supabase_io import download_from_bucket, upload_json_to_bucket

router = APIRouter(prefix="/analysis")


class FaceHeavyRequest(BaseModel):
    bucket: str
    object_path: str
    user_id: Optional[str] = None


_provider = InsightFaceProvider()


@router.post("/face/heavy")
async def analyze_face_heavy(req: FaceHeavyRequest):
    """Run heavy face analysis on an image stored in Supabase."""
    try:
        image_path = download_from_bucket(req.bucket, req.object_path)
        result = _provider.analyze(image_path)
        result_key = f"{req.object_path}.insightface.json"
        upload_json_to_bucket(req.bucket, result_key, result)
        if req.user_id:
            await asyncio.to_thread(
                upsert_face_embeddings, req.user_id, req.object_path, result["faces"]
            )
        return {"ok": True, "result_key": result_key, "faces": result["face_count"]}
    except Exception as exc:  # pragma: no cover - network/IO errors
        raise HTTPException(status_code=500, detail=str(exc)) from exc
