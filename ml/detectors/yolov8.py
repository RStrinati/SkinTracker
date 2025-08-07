"""Minimal YOLOv8 wrapper used for lesion detection.

The real project intends to use the `ultralytics` package.  To keep the
repository lightweight and the unit tests fast, this module falls back
to a very small OpenCV based blob detector when the heavy dependency is
not installed.  The wrapper exposes a single :class:`YOLOv8Detector`
with a ``detect`` method returning bounding boxes in ``(x, y, w, h)``
format.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

try:  # pragma: no cover - optional dependency
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover
    YOLO = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]
    confidence: float
    type: str = "pimple"


class YOLOv8Detector:
    """Wrapper around the ultralytics YOLOv8 model.

    Parameters
    ----------
    weights: str, optional
        Path to the model weights.  When ``None`` and the ultralytics
        package is missing, a trivial fallback detector is used instead.
    """

    def __init__(self, weights: str | None = None):
        self.weights = weights
        if YOLO is not None and weights is not None:
            self.model = YOLO(weights)
        else:  # pragma: no cover - executed in test environment without YOLO
            self.model = None

    def _fallback(self, image: np.ndarray) -> List[Detection]:  # pragma: no cover - simple heuristic
        if cv2 is None:
            raise RuntimeError("OpenCV is required for the fallback detector")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections: List[Detection] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 50 <= area <= 2000:
                x, y, w, h = cv2.boundingRect(cnt)
                detections.append(Detection(bbox=(x, y, w, h), confidence=1.0))
        return detections

    def detect(self, image: np.ndarray) -> List[Detection]:
        if self.model is None:
            return self._fallback(image)
        results = self.model(image)[0]
        detections: List[Detection] = []
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(
                Detection(
                    bbox=(int(x1), int(y1), int(x2 - x1), int(y2 - y1)),
                    confidence=float(box.conf[0]),
                )
            )
        return detections


__all__ = ["YOLOv8Detector", "Detection"]
