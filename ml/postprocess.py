"""Post-processing utilities for lesion detections."""
from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import numpy as np

try:  # pragma: no cover
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore


def assign_region(bbox: Tuple[int, int, int, int], regions: Dict[str, List[Tuple[float, float]]], image_shape: Tuple[int, int, int]) -> str | None:
    """Return the facial region that ``bbox`` falls into.

    The function takes the centroid of the bounding box and performs a
    point-in-polygon test against the region polygons.
    """
    if cv2 is None:
        raise RuntimeError("OpenCV is required for region assignment")
    x, y, w, h = bbox
    cx, cy = x + w / 2, y + h / 2
    h_img, w_img = image_shape[:2]
    for name, poly in regions.items():
        pts = np.array([(px * w_img, py * h_img) for px, py in poly], dtype=np.float32)
        if cv2.pointPolygonTest(pts, (cx, cy), False) >= 0:
            return name
    return None


def redness_score(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> float:
    """Compute a simple redness score based on the LAB colour space."""
    if cv2 is None:
        raise RuntimeError("OpenCV is required for redness scoring")
    x, y, w, h = map(int, bbox)
    roi = image[y : y + h, x : x + w]
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    a = lab[:, :, 1]
    return float(a.mean() / 255.0)


def bbox_area(bbox: Tuple[int, int, int, int]) -> int:
    x, y, w, h = bbox
    return int(w * h)


__all__ = ["assign_region", "redness_score", "bbox_area"]
