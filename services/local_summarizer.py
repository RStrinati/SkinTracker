"""Local text generation for skin analysis results."""
from __future__ import annotations

from typing import Dict, List, Optional

class LocalAnalysisSummarizer:
    """Generates human-readable summaries of skin analysis results without using OpenAI."""
    
    def __init__(self):
        """Initialize summarizer with thresholds and templates."""
        self.blemish_thresholds = {
            "low": 2.0,      # 0-2% affected area
            "moderate": 5.0,  # 2-5% affected area
            "high": 10.0     # >5% affected area
        }
        
        self.texture_descriptors = {
            "smooth": "The skin appears smooth with good overall texture.",
            "uneven": "The skin shows some uneven areas in texture.",
            "rough": "The skin texture appears somewhat rough."
        }

    def _get_severity_level(self, percent_blemished: float) -> str:
        """Determine severity level based on blemish percentage."""
        if percent_blemished <= self.blemish_thresholds["low"]:
            return "low"
        elif percent_blemished <= self.blemish_thresholds["moderate"]:
            return "moderate"
        else:
            return "high"

    def _get_texture_description(self, texture_metrics: Dict) -> str:
        """Generate texture description based on analysis metrics."""
        smoothness = texture_metrics.get("smoothness", 0.5)
        if smoothness > 0.7:
            return self.texture_descriptors["smooth"]
        elif smoothness > 0.4:
            return self.texture_descriptors["uneven"]
        else:
            return self.texture_descriptors["rough"]

    def _get_condition_insights(self, condition_scores: Dict[str, float]) -> List[str]:
        """Generate insights based on condition scores."""
        insights = []
        for condition, score in condition_scores.items():
            if score > 0.7:
                insights.append(f"High likelihood of {condition}")
            elif score > 0.4:
                insights.append(f"Moderate indicators of {condition}")
        return insights

    def generate_summary(
        self,
        percent_blemished: float,
        texture_metrics: Optional[Dict] = None,
        condition_scores: Optional[Dict[str, float]] = None,
    ) -> str:
        """Generate a human-readable summary of the analysis results."""
        severity = self._get_severity_level(percent_blemished)
        
        summary_parts = []
        
        # Blemish assessment
        if severity == "low":
            summary_parts.append(
                f"Your skin shows minimal blemishes, affecting approximately {percent_blemished:.1f}% "
                "of the analyzed area."
            )
        elif severity == "moderate":
            summary_parts.append(
                f"Moderate presence of blemishes detected, affecting {percent_blemished:.1f}% "
                "of the analyzed area."
            )
        else:
            summary_parts.append(
                f"Significant presence of blemishes detected, affecting {percent_blemished:.1f}% "
                "of the analyzed area."
            )

        # Texture analysis
        if texture_metrics:
            summary_parts.append(self._get_texture_description(texture_metrics))

        # Condition insights
        if condition_scores:
            insights = self._get_condition_insights(condition_scores)
            if insights:
                summary_parts.append("Additional observations:")
                summary_parts.extend([f"- {insight}" for insight in insights])

        # Recommendations based on severity
        if severity == "low":
            summary_parts.append(
                "Recommendation: Continue your current skincare routine while maintaining "
                "good skin hygiene practices."
            )
        elif severity == "moderate":
            summary_parts.append(
                "Recommendation: Consider incorporating gentle exfoliation and targeted "
                "treatments into your skincare routine."
            )
        else:
            summary_parts.append(
                "Recommendation: Consider consulting with a dermatologist for a professional "
                "assessment and treatment plan."
            )

        return "\n".join(summary_parts)
