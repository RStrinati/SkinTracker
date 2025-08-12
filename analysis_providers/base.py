from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Protocol


class AnalysisProvider(Protocol):
    """Protocol for analysis providers."""

    def analyze(self, image_path: Path) -> Dict[str, Any]:
        """Analyze an image and return structured results."""
        raise NotImplementedError
