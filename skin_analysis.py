"""Skin image analysis utilities with pluggable face providers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import numpy as np

try:  # Heavy dependency imported lazily
    import cv2  # type: ignore
except Exception:  # pragma: no cover - handled gracefully
    cv2 = None  # type: ignore

from supabase import Client

from analysis_providers.base import FaceAnalysisProvider
from services.local_storage import LocalStorageService


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
    """Detect blemishes and compute statistics using advanced preprocessing."""
    # Convert to LAB color space for better skin analysis
    lab = cv2.cvtColor(normalized, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l_channel = clahe.apply(l_channel)
    
    # Reconstruct the image
    lab = cv2.merge([l_channel, a_channel, b_channel])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    # Convert to grayscale
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    masked_gray = cv2.bitwise_and(gray, face_mask)
    
    # Apply local contrast enhancement
    blurred = cv2.GaussianBlur(masked_gray, (7, 7), 0)
    detail = cv2.addWeighted(masked_gray, 1.5, blurred, -0.5, 0)
    
    # Use adaptive thresholding instead of global
    thresh = cv2.adaptiveThreshold(
        detail,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11,  # Block size
        2    # C constant for threshold
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

    if cv2 is None:
        raise RuntimeError("OpenCV must be installed to use this function")

    if provider is None:
        from analysis_providers.insightface_provider import InsightFaceProvider
        provider = InsightFaceProvider()

    img_path = Path(image_path)
    image = cv2.imread(str(img_path))
    
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")
        
    # Validate image dimensions and content
    if image.size == 0:
        raise ValueError("Image is empty")
        
    if len(image.shape) != 3:
        raise ValueError("Image must be a color image")
        
    height, width = image.shape[:2]
    if width < 100 or height < 100:
        raise ValueError(f"Image too small: {width}x{height}. Minimum size is 100x100 pixels")

    analysis = provider.analyze(img_path)
    if analysis.get("face_count", 0) == 0:
        return None
    face = analysis["faces"][0]
    bbox = np.array(face["bbox_xyxy"], dtype=np.float32)
    landmarks = np.array(face["landmarks_5"], dtype=np.float32)

    normalized, points, face_mask = align_face(image, bbox, landmarks)
    blemish_mask, blemish_area, face_area, percent_blemished = detect_blemishes(
        normalized, face_mask
    )

    landmark_img = normalized.copy()
    for pt in points.astype(np.int32):
        cv2.circle(landmark_img, tuple(pt), 1, (0, 255, 0), -1)

    blemish_img = np.zeros_like(normalized)
    blemish_img[blemish_mask == 255] = (0, 0, 255)

    overlay_img = normalized.copy()
    overlay_img[blemish_mask == 255] = (0, 0, 255)

    base = f"{user_id}_{image_id}"
    face_image_path = img_path.parent / f"{base}_face.png"
    blemish_image_path = img_path.parent / f"{base}_blemishes.png"
    overlay_image_path = img_path.parent / f"{base}_overlay.png"

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

    # Always store locally first
    local_storage = LocalStorageService()
    local_storage.store_analysis(record, analysis)

    # Upload to Supabase if client is available
    if client:
        try:
            bucket = client.storage.from_("skin-photos")
            for local_path in [face_image_path, blemish_image_path, overlay_image_path]:
                with open(local_path, "rb") as f:
                    bucket.upload(local_path.name, f, {"content-type": "image/png"})
            client.table("skin_kpis").insert(record).execute()
            # Mark as synced after successful upload
            local_storage.mark_synced(record["user_id"], record["image_id"])
        except Exception as e:
            # Log error but continue - data is safe in local storage
            print(f"Failed to sync to cloud: {e}")

    return record


__all__ = ["process_skin_image", "align_face", "detect_blemishes"]

