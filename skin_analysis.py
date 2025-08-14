from __future__ import annotations

"""Skin image analysis utilities with pluggable face providers."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:  # Heavy dependency imported lazily
    import cv2  # type: ignore
except Exception:  # pragma: no cover - handled gracefully
    cv2 = None  # type: ignore

from supabase import Client

from analysis_providers.base import FaceAnalysisProvider


def align_face(image: np.ndarray, bbox: np.ndarray, landmarks: np.ndarray):
    """Rotate and crop the face based on eye landmarks."""
    x1, y1, x2, y2 = bbox.astype(int)
    left_eye, right_eye = landmarks[0], landmarks[1]
    dx, dy = right_eye[0] - left_eye[0], right_eye[1] - left_eye[1]
    angle = np.degrees(np.arctan2(dy, dx))
    center = ((x1 + x2) / 2, (y1 + y2) / 2)
    rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, rot_matrix, (image.shape[1], image.shape[0]))

    ones = np.ones((landmarks.shape[0], 1))
    landmarks_hom = np.hstack([landmarks, ones])
    rotated_points = (rot_matrix @ landmarks_hom.T).T

    crop = rotated[y1:y2, x1:x2]
    rotated_points -= [x1, y1]
    aligned = cv2.resize(crop, (300, 300))
    scale_x = 300 / (x2 - x1)
    scale_y = 300 / (y2 - y1)
    aligned_points = rotated_points * [scale_x, scale_y]

    mask = np.full((300, 300), 255, dtype=np.uint8)
    return aligned, aligned_points, mask


def detect_blemishes(normalized: np.ndarray, face_mask: np.ndarray):
    """Detect blemishes and compute statistics."""
    gray = cv2.cvtColor(normalized, cv2.COLOR_BGR2GRAY)
    masked_gray = cv2.bitwise_and(gray, face_mask)
    blurred = cv2.GaussianBlur(masked_gray, (7, 7), 0)
    _, thresh = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    thresh = cv2.bitwise_and(thresh, face_mask)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blemish_mask = np.zeros_like(face_mask)
    blemish_area = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 50 <= area <= 2000:
            blemish_area += area
            cv2.drawContours(blemish_mask, [cnt], -1, 255, -1)

    face_area = int(cv2.countNonZero(face_mask))
    percent_blemished = (
        float(blemish_area) / face_area * 100 if face_area > 0 else 0.0
    )

    return blemish_mask, blemish_area, face_area, percent_blemished


def process_skin_image(
    image_path: str,
    user_id: str,
    image_id: str,
    client: Optional[Client] = None,
    provider: Optional[FaceAnalysisProvider] = None,
) -> Optional[Dict[str, object]]:
    """Process a skin image and store KPI results."""

    try:
        if cv2 is None:
            logger.error("OpenCV is not installed.")
            raise RuntimeError("OpenCV must be installed to use this function")

        if provider is None:
            from analysis_providers.insightface_provider import InsightFaceProvider
            provider = InsightFaceProvider()

        img_path = Path(image_path)
        image = cv2.imread(str(img_path))
        if image is None:
            logger.error(f"Image not found: {image_path}")
            raise FileNotFoundError(f"Image not found: {image_path}")

        analysis = provider.analyze(img_path)
        if analysis.get("face_count", 0) == 0:
            logger.warning(f"No face detected in image: {image_path}")
            return None
        face = analysis["faces"][0]
        bbox = np.array(face["bbox_xyxy"], dtype=np.float32)
        landmarks = np.array(face["landmarks_5"], dtype=np.float32)
    except Exception as e:
        logger.exception(f"Error in process_skin_image for image {image_path}")
        raise

    normalized, points, face_mask = align_face(image, bbox, landmarks)
    blemish_mask, blemish_area, face_area, percent_blemished = detect_blemishes(
        normalized, face_mask
    )

    landmark_img = normalized.copy()
    for pt in points.astype(np.int32):
        cv2.circle(landmark_img, tuple(pt), 1, (0, 255, 0), -1)

    mask_2d = blemish_mask[..., 0] if blemish_mask.ndim == 3 else blemish_mask
    blemish_img = np.zeros_like(normalized)
    if np.any(mask_2d == 255):
        blemish_img[mask_2d == 255] = (0, 0, 255)

    overlay_img = normalized.copy()
    if np.any(mask_2d == 255):
        overlay_img[mask_2d == 255] = (0, 0, 255)

    base = f"{user_id}_{image_id}"
    face_image_path = img_path.parent / f"{base}_face.png"
    blemish_image_path = img_path.parent / f"{base}_blemishes.png"
    overlay_image_path = img_path.parent / f"{base}_overlay.png"

    if hasattr(cv2, "imwrite"):
        cv2.imwrite(str(face_image_path), landmark_img)
        cv2.imwrite(str(blemish_image_path), blemish_img)
        cv2.imwrite(str(overlay_image_path), overlay_img)

    record: Dict[str, object] = {
        "user_id": user_id,
        "image_id": image_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "face_area_px": face_area,
        "blemish_area_px": int(blemish_area),
        "percent_blemished": percent_blemished,
        "face_image_path": str(face_image_path),
        "blemish_image_path": str(blemish_image_path),
        "overlay_image_path": str(overlay_image_path),
    }

    if client:
        bucket = client.storage.from_("skin-photos")
        for local_path in [face_image_path, blemish_image_path, overlay_image_path]:
            with open(local_path, "rb") as f:
                bucket.upload(local_path.name, f, {"content-type": "image/png"})
        client.table("skin_kpis").insert(record).execute()

    return record


__all__ = ["process_skin_image", "align_face", "detect_blemishes"]

