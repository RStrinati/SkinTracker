from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:  # pragma: no cover - heavy deps may be missing
    import cv2  # type: ignore
    import numpy as np
    import onnxruntime as ort  # type: ignore
    from insightface.app import FaceAnalysis
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore
    np = None  # type: ignore
    ort = None  # type: ignore
    FaceAnalysis = None  # type: ignore

from .base import AnalysisProvider


class InsightFaceProvider(AnalysisProvider):
    """InsightFace implementation using the ``buffalo_l`` model."""

    def __init__(self) -> None:
        if cv2 is None or np is None or ort is None or FaceAnalysis is None:
            raise RuntimeError("InsightFace dependencies are not installed")

        providers = (
            ["CUDAExecutionProvider"]
            if "CUDAExecutionProvider" in ort.get_available_providers()
            else ["CPUExecutionProvider"]
        )
        ctx_id = 0 if providers[0] != "CPUExecutionProvider" else -1
        try:
            self.app = FaceAnalysis(name="buffalo_l", providers=providers)
            # Prepare with reasonable detection size
            self.app.prepare(ctx_id=ctx_id, det_size=(640, 640))
        except Exception as exc:  # pragma: no cover - initialization failures
            raise RuntimeError("InsightFace initialization failed") from exc

    def _resize_image(self, img: np.ndarray) -> np.ndarray:
        """Resize image so that the longest side is at most 1280 px."""
        h, w = img.shape[:2]
        max_side = max(h, w)
        if max_side <= 1280:
            return img
        scale = 1280.0 / max_side
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(img, (new_w, new_h))

    def analyze(self, image_path: Path) -> Dict[str, Any]:  # noqa: D401
        """Analyze the image and return face detection results."""
        img = cv2.imread(str(image_path))
        if img is None:
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = self._resize_image(img)
        faces = self.app.get(img)
        result_faces: List[Dict[str, Any]] = []
        for face in faces:
            attrs: Dict[str, Any] = {}
            if face.sex is not None:
                attrs["gender"] = face.sex
            if face.age is not None:
                attrs["age"] = int(face.age)
            if face.pose is not None:
                attrs["pose"] = [float(p) for p in face.pose]
            if face.mask is not None:
                attrs["mask"] = bool(face.mask)

            result_faces.append(
                {
                    "bbox_xyxy": face.bbox.astype(float).tolist(),
                    "landmarks_5": face.kps.astype(float).tolist(),
                    "det_score": float(face.det_score),
                    "embedding_512": face.embedding.astype(float).tolist(),
                    "attributes": attrs,
                }
            )

        return {
            "provider": "insightface_buffalo_l",
            "face_count": len(result_faces),
            "faces": result_faces,
        }
