import logging
from typing import List, Dict, Any

logger = logging.getLogger("inference.prediction_mapper")


class PredictionMapper:
    @staticmethod
    def format_prediction_output(
        model_name: str,
        model_version: str,
        filename: str,
        label: str,
        confidence: float,
        probabilities: List[float],
        risk_level: str,
        processing_duration: float,
    ) -> Dict[str, Any]:
        """
        Structure inference calculations and system parameters into a dictionary representation
        corresponding to standard API payload response schemas.
        """
        return {
            "model_name": model_name,
            "model_version": model_version,
            "filename": filename,
            "prediction_label": label,
            "confidence": confidence,
            "probabilities": {
                "non-fire": probabilities[0] if len(probabilities) > 0 else 0.0,
                "fire": probabilities[1] if len(probabilities) > 1 else 0.0,
            },
            "risk_level": risk_level,
            "processing_duration_seconds": processing_duration,
        }


prediction_mapper = PredictionMapper()
