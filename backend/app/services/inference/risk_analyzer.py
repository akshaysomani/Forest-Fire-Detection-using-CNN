import logging

logger = logging.getLogger("inference.risk_analyzer")


class RiskAnalyzer:
    @staticmethod
    def analyze_risk(label: str, confidence: float) -> str:
        """
        Determine the fire hazard risk rating: Low, Medium, or High.
        If no fire is detected, default to Low.
        For positive fire detections:
        - Confidence >= 85%: High Risk
        - Confidence >= 60%: Medium Risk
        - Confidence < 60%: Low Risk
        """
        if label != "fire":
            return "Low"

        if confidence >= 0.85:
            return "High"
        elif confidence >= 0.60:
            return "Medium"
        else:
            return "Low"


risk_analyzer = RiskAnalyzer()
