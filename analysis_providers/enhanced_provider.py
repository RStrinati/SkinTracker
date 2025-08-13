"""Advanced skin analysis provider combining multiple techniques."""
from __future__ import annotations

from pathlib import Path
import logging
from typing import Any, Dict, List, Optional
import os

import cv2
import numpy as np
import torch
from torchvision.models import resnet50, ResNet50_Weights
import onnxruntime as ort
from insightface.app import FaceAnalysis

from .base import FaceAnalysisProvider
from .texture_analysis.skin_features import SkinTextureAnalyzer

logger = logging.getLogger(__name__)

class EnhancedSkinAnalysisProvider(FaceAnalysisProvider):
    """Advanced skin analysis combining multiple models and techniques."""

    def __init__(self) -> None:
        # Initialize face detection
        providers = (
            ["CUDAExecutionProvider"]
            if "CUDAExecutionProvider" in ort.get_available_providers()
            else ["CPUExecutionProvider"]
        )
        ctx_id = 0 if providers[0] != "CPUExecutionProvider" else -1
        
        try:
            # Initialize InsightFace for face detection
            self.face_detector = FaceAnalysis(name="buffalo_l", providers=providers)
            self.face_detector.prepare(ctx_id=ctx_id, det_size=(640, 640))
            
            # Initialize texture analyzer
            self.texture_analyzer = SkinTextureAnalyzer()
            
            # Initialize ResNet model for general feature extraction
            self.feature_extractor = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
            self.feature_extractor.eval()
            
            # Download and load skin condition classifier if available
            model_path = self._ensure_model_files()
            if model_path:
                self.condition_classifier = ort.InferenceSession(
                    model_path,
                    providers=providers
                )
            else:
                self.condition_classifier = None
                
        except Exception as exc:
            logger.error(f"Error initializing EnhancedSkinAnalysisProvider: {exc}")
            raise RuntimeError("Failed to initialize skin analysis provider") from exc

    def _ensure_model_files(self) -> Optional[str]:
        """Download and verify model files."""
        # TODO: Implement model download from a secure source
        # For now, return None to indicate no pre-trained classifier
        return None

    def _preprocess_for_classification(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for the skin condition classifier."""
        # Resize and normalize
        img = cv2.resize(image, (224, 224))
        img = img.astype(np.float32) / 255.0
        img = (img - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        return img.transpose(2, 0, 1)[np.newaxis, ...]

    def analyze(self, image_path: Path) -> Dict[str, Any]:
        """Perform comprehensive skin analysis."""
        try:
            # Read and validate image
            img = cv2.imread(str(image_path))
            if img is None:
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Resize if needed
            h, w = img.shape[:2]
            max_side = max(h, w)
            if max_side > 1280:
                scale = 1280.0 / max_side
                new_w, new_h = int(w * scale), int(h * scale)
                img = cv2.resize(img, (new_w, new_h))

            # Detect faces
            faces = self.face_detector.get(img)
            result_faces = []

            for face in faces:
                # Get basic face detection results
                bbox = face.bbox.astype(float).tolist()
                landmarks = face.kps.astype(float).tolist()
                
                # Extract face region
                x1, y1, x2, y2 = map(int, bbox)
                face_img = img[y1:y2, x1:x2]
                
                if face_img.size == 0:
                    continue

                # Create face mask
                face_mask = np.zeros((y2-y1, x2-x1), dtype=np.uint8)
                cv2.fillConvexPoly(face_mask, cv2.convexHull(np.array(landmarks)), 255)

                # Analyze texture
                texture_results = self.texture_analyzer.analyze_texture(face_img, face_mask)
                
                # Detect skin features
                feature_mask, features = self.texture_analyzer.detect_skin_features(
                    face_img, face_mask
                )

                # Extract deep features
                with torch.no_grad():
                    face_tensor = torch.from_numpy(
                        self._preprocess_for_classification(face_img)
                    ).float()
                    deep_features = self.feature_extractor(face_tensor)
                    deep_features = deep_features.numpy()

                # Run skin condition classifier if available
                condition_scores = {}
                if self.condition_classifier:
                    inputs = {
                        self.condition_classifier.get_inputs()[0].name: 
                        self._preprocess_for_classification(face_img)
                    }
                    condition_scores = dict(
                        zip(["acne", "rosacea", "eczema", "normal"],
                            self.condition_classifier.run(None, inputs)[0][0].tolist())
                    )

                # Combine all results
                face_analysis = {
                    "bbox_xyxy": bbox,
                    "landmarks_5": landmarks,
                    "det_score": float(face.det_score),
                    "texture_analysis": texture_results,
                    "detected_features": features,
                    "condition_scores": condition_scores,
                    "face_attributes": {
                        "gender": face.sex,
                        "age": int(face.age) if face.age is not None else None,
                        "mask": bool(face.mask) if face.mask is not None else None
                    }
                }
                result_faces.append(face_analysis)

            return {
                "provider": "enhanced_skin_analysis",
                "face_count": len(result_faces),
                "faces": result_faces,
            }

        except Exception as e:
            logger.error(f"Error in skin analysis: {e}")
            raise
