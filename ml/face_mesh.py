"""Utilities for extracting facial landmarks and canonical regions.

This module wraps MediaPipe Face Mesh and exposes a simple helper
returning 468 normalized landmark coordinates together with a set of
pre-defined facial regions.  The regions use normalized coordinates
(0-1) in image space so they can easily be scaled to any resolution.

The implementation is intentionally lightweight; it lazily imports
``mediapipe`` so that unit tests that do not require the heavy
dependency can still run.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

try:  # pragma: no cover - optional dependency
    import mediapipe as mp  # type: ignore
except Exception:  # pragma: no cover - handled gracefully
    mp = None  # type: ignore


@dataclass
class FaceMeshResult:
    """Returned by :func:`extract_face_mesh`.

    Attributes
    ----------
    landmarks:
        List of dictionaries with ``i``, ``x`` and ``y`` entries where
        ``x`` and ``y`` are normalized coordinates.
    regions:
        Mapping of region name to a list of ``(x, y)`` tuples forming a
        polygon in normalized coordinates.
    """

    landmarks: List[Dict[str, float]]
    regions: Dict[str, List[Tuple[float, float]]]


# These indices roughly outline key facial regions.  The exact selection
# is not mission critical for the initial prototype and can be refined
# later without breaking the API.
REGION_INDICES: Dict[str, List[int]] = {
    "forehead": [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379],
    "left_cheek": [205, 50, 187, 147, 123, 116, 111, 117, 118, 119],
    "right_cheek": [425, 352, 345, 347, 346, 330, 329, 296, 281, 363],
    "nose": [6, 195, 5, 4, 1, 19, 94, 2],
    "chin": [152, 377, 400, 378, 365, 401, 435],
}


def _build_regions(landmarks: List[Dict[str, float]]) -> Dict[str, List[Tuple[float, float]]]:
    regions: Dict[str, List[Tuple[float, float]]] = {}
    for name, indices in REGION_INDICES.items():
        regions[name] = [(landmarks[i]["x"], landmarks[i]["y"]) for i in indices]
    return regions


def extract_face_mesh(image: np.ndarray) -> FaceMeshResult:
    """Extract facial landmarks and regions from ``image``.

    Parameters
    ----------
    image:
        ``numpy`` array in BGR color space.
    Returns
    -------
    FaceMeshResult
        Data class containing landmarks and region polygons.
    """

    if mp is None:  # pragma: no cover - dependency not available
        raise RuntimeError("mediapipe is not installed")

    h, w = image.shape[:2]
    mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True)
    try:
        results = mesh.process(image[:, :, ::-1])  # MediaPipe expects RGB
        if not results.multi_face_landmarks:
            raise ValueError("No face detected")
        landmarks = [
            {"i": i, "x": lm.x, "y": lm.y} for i, lm in enumerate(results.multi_face_landmarks[0].landmark)
        ]
        regions = _build_regions(landmarks)
        return FaceMeshResult(landmarks=landmarks, regions=regions)
    finally:
        mesh.close()


__all__ = ["FaceMeshResult", "extract_face_mesh"]
