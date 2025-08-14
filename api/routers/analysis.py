from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from analysis_providers.insightface_provider import InsightFaceProvider
from services.supabase import supabase
from skin_analysis import process_skin_image


router = APIRouter(prefix="/analysis")


class FaceHeavyRequest(BaseModel):
    bucket: str
    object_path: str
    user_id: Optional[str] = None


_provider = None
download_from_bucket = None
upload_json_to_bucket = None

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("analysis")


@router.post("/face/heavy")
async def analyze_face_heavy(req: FaceHeavyRequest):
    """Run heavy face analysis on an image stored in Supabase."""
    # TODO: Consider moving this analysis workflow into a worker queue if latency is high.
    logger.debug(f"Request received: {req}")
    logger.debug("Initializing provider and Supabase functions...")
    try:
        global _provider, download_from_bucket, upload_json_to_bucket
        if download_from_bucket is None or upload_json_to_bucket is None:
            download_from_bucket = supabase.download_from_bucket
            upload_json_to_bucket = supabase.upload_json_to_bucket

        if _provider is None:
            from analysis_providers.insightface_provider import InsightFaceProvider

            _provider = InsightFaceProvider()

        image_path = await asyncio.to_thread(
            supabase.download_from_bucket, req.bucket, req.object_path
        )
        logger.debug(f"Image downloaded to: {image_path}")

        kpi = await asyncio.to_thread(
            process_skin_image,
            str(image_path),
            req.user_id or "anon",
            req.object_path,
            None,
            _provider,
        )
        logger.debug(f"KPI generated: {kpi}")

        result_key = f"{req.object_path}.analysis.json"
        upload_json_to_bucket(req.bucket, result_key, kpi or {"face_detected": False})
        logger.debug(f"Results uploaded to bucket with key: {result_key}")

        return {"ok": True, "result_key": result_key, "face_detected": kpi is not None}

    except Exception as exc:
        logger.error(f"Error processing request: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
