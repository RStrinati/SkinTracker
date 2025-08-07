"""Generate pseudo contour maps for facial images."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

try:  # pragma: no cover - optional dependency
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore


def contour_overlay(image: np.ndarray, output_path: Path) -> Path:
    """Create a contour line overlay from ``image`` and save it.

    The method is deliberately lightweight: it converts the image to
    grayscale, applies a Laplacian filter to accentuate edges and then
    draws the resulting contours onto a transparent PNG.
    """
    if cv2 is None:  # pragma: no cover
        raise RuntimeError("OpenCV is not installed")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    lap = cv2.Laplacian(blurred, cv2.CV_64F)
    lap_norm = cv2.normalize(lap, None, 0, 255, cv2.NORM_MINMAX).astype("uint8")
    contours, _ = cv2.findContours(lap_norm, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    overlay = np.zeros((*gray.shape, 4), dtype=np.uint8)
    cv2.drawContours(overlay, contours, -1, (0, 255, 0, 255), 1)
    cv2.imwrite(str(output_path), overlay)
    return output_path


__all__ = ["contour_overlay"]
