"""Image upload and processing endpoints."""
from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from .. import schemas
from ml.pipeline import Pipeline

router = APIRouter(prefix="/api/v1/images", tags=["images"])
_pipeline = Pipeline()


@router.post("/")
async def upload_image(file: UploadFile = File(...)) -> dict:
    """Accept an image upload and store it temporarily.

    This endpoint is intentionally simple for the prototype: the file is
    written to ``/tmp`` and the local path is returned.  A production
    implementation would instead upload to Supabase storage and record a
    row in the ``images`` table.
    """

    image_id = uuid4()
    tmp_path = Path("/tmp") / f"{image_id}.jpg"
    with open(tmp_path, "wb") as f:
        f.write(await file.read())
    return {"image_id": image_id, "path": str(tmp_path)}


@router.post("/{image_id}/process", response_model=schemas.ProcessImageResponse)
async def process_image(image_id: UUID, req: schemas.ProcessImageRequest) -> schemas.ProcessImageResponse:
    if not req.bucket_path:
        raise HTTPException(status_code=400, detail="bucket_path required")
    path = Path(req.bucket_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    result = _pipeline.process(str(path), path.parent)
    lesions = [schemas.LesionOut(bbox=d["bbox"], confidence=d["confidence"], type=d["type"], region=d["region"], area_px=d["area_px"], redness_score=d["redness_score"]) for d in result["lesions"]]
    return schemas.ProcessImageResponse(image_id=image_id, contour_overlay_url=result["contour_overlay_path"], lesions=lesions)
