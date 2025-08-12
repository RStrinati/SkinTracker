from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Protocol


class FaceAnalysisProvider(Protocol):
    """Common interface for face analysis backends.

    Implementations should perform face detection/analysis on the provided
    image path and return a dictionary with model specific results.  The
    structure of the dictionary is left flexible to accommodate different
    providers, but should at minimum include ``face_count`` and ``faces``
    entries.
    """

    def analyze(self, image_path: Path) -> Dict[str, Any]:
        """Analyze an image and return structured results."""
        raise NotImplementedError


__all__ = ["FaceAnalysisProvider"]
