"""Skin image analysis background task.

This module provides a utility function that downloads a skin image,
aligns the face, normalizes lighting, detects blemishes and stores
results in Supabase.  The implementation follows the specification in
the user instructions.  All heavy dependencies (OpenCV and Mediapipe)
are imported lazily so that the module can be imported without the
libraries being installed – useful for running tests that do not rely
on the actual image processing.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np

try:  # Heavy dependencies are imported lazily
    import cv2  # type: ignore
    import mediapipe as mp  # type: ignore
except Exception:  # pragma: no cover - handled gracefully
    cv2 = None  # type: ignore
    mp = None  # type: ignore

from supabase import Client


def _gamma_correction(image: np.ndarray, gamma: float = 1.5) -> np.ndarray:
    inv_gamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** inv_gamma * 255 for i in range(256)]).astype(
        "uint8"
    )
    return cv2.LUT(image, table)


def process_skin_image(
    image_path: str, user_id: str, image_id: str, client: Optional[Client] = None
) -> Optional[Dict[str, object]]:
    """Process a skin image and store KPI results.

    Args:
        image_path: Local path to the downloaded image.
        user_id: ID of the user uploading the image.
        image_id: Unique identifier of the image.
        client: Optional Supabase client used for uploading results.

    Returns:
        KPI dictionary or ``None`` if no face was detected.
    """

    if cv2 is None or mp is None:
        raise RuntimeError("OpenCV and Mediapipe must be installed to use this function")

    img_path = Path(image_path)
    image = cv2.imread(str(img_path))
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    height, width = image.shape[:2]
    face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True)
    results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    if not results.multi_face_landmarks:
        face_mesh.close()
        return None

    landmarks = results.multi_face_landmarks[0]

    # Convert landmarks to pixel coordinates
    points = np.array(
        [(lm.x * width, lm.y * height) for lm in landmarks.landmark], dtype=np.float32
    )

    left_eye = points[33]
    right_eye = points[263]
    dy, dx = right_eye[1] - left_eye[1], right_eye[0] - left_eye[0]
    angle = np.degrees(np.arctan2(dy, dx))

    center = (width / 2, height / 2)
    rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, rot_matrix, (width, height))

    # Rotate landmarks
    ones = np.ones((points.shape[0], 1))
    points_hom = np.hstack([points, ones])
    rotated_points = (rot_matrix @ points_hom.T).T

    # Crop to face bounding box
    x_min, y_min = rotated_points.min(axis=0).astype(int)
    x_max, y_max = rotated_points.max(axis=0).astype(int)
    x_min = max(x_min, 0)
    y_min = max(y_min, 0)
    x_max = min(x_max, rotated.shape[1])
    y_max = min(y_max, rotated.shape[0])

    aligned = rotated[y_min:y_max, x_min:x_max]
    rotated_points -= [x_min, y_min]
    aligned = cv2.resize(aligned, (300, 300))
    scale_x = 300 / (x_max - x_min)
    scale_y = 300 / (y_max - y_min)
    rotated_points *= [scale_x, scale_y]

    # Lighting normalization
    ycrcb = cv2.cvtColor(aligned, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    y = clahe.apply(y)
    ycrcb = cv2.merge([y, cr, cb])
    normalized = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    normalized = _gamma_correction(normalized)

    # Face mask
    face_hull = cv2.convexHull(rotated_points.astype(np.int32))
    face_mask = np.zeros(normalized.shape[:2], dtype=np.uint8)
    cv2.fillConvexPoly(face_mask, face_hull, 255)

    # Blemish detection
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

    # Visualisations
    landmark_img = normalized.copy()
    for pt in rotated_points.astype(np.int32):
        cv2.circle(landmark_img, tuple(pt), 1, (0, 255, 0), -1)

    blemish_img = np.zeros_like(normalized)
    blemish_img[blemish_mask == 255] = (0, 0, 255)

    overlay_img = normalized.copy()
    overlay_img[blemish_mask == 255] = (0, 0, 255)

    # Save images
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
        "timestamp": datetime.utcnow().isoformat(),
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
                bucket.upload(local_path.name, f, {'content-type': 'image/png'})
        client.table("skin_kpis").insert(record).execute()

    face_mesh.close()
    return record


__all__ = ["process_skin_image"]

