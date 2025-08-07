"""High level orchestration for the skin analysis pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

try:  # pragma: no cover - optional dependency
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

from .face_mesh import FaceMeshResult, extract_face_mesh
from .contour_map import contour_overlay
from .detectors.yolov8 import YOLOv8Detector, Detection
from . import postprocess


class Pipeline:
    """End-to-end processing pipeline.

    Parameters
    ----------
    detector: YOLOv8Detector | None
        Optional detector instance.  When ``None`` a default instance is
        created using the lightweight fallback detector.
    """

    def __init__(self, detector: YOLOv8Detector | None = None):
        self.detector = detector or YOLOv8Detector()

    def process(self, image_path: str, output_dir: Path) -> Dict[str, object]:
        if cv2 is None:  # pragma: no cover
            raise RuntimeError("OpenCV is not installed")
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(image_path)

        face: FaceMeshResult = extract_face_mesh(img)
        overlay_path = contour_overlay(img, output_dir / "contours.png")
        detections: List[Detection] = self.detector.detect(img)

        lesions: List[Dict[str, object]] = []
        for det in detections:
            region = postprocess.assign_region(det.bbox, face.regions, img.shape)
            redness = postprocess.redness_score(img, det.bbox)
            lesions.append(
                {
                    "bbox": {"x": det.bbox[0], "y": det.bbox[1], "w": det.bbox[2], "h": det.bbox[3]},
                    "confidence": det.confidence,
                    "type": det.type,
                    "region": region,
                    "area_px": postprocess.bbox_area(det.bbox),
                    "redness_score": redness,
                }
            )

        return {
            "landmarks": face.landmarks,
            "regions": face.regions,
            "contour_overlay_path": str(overlay_path),
            "lesions": lesions,
        }


__all__ = ["Pipeline"]
