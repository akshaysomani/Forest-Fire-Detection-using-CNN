import logging

logger = logging.getLogger("alert.severity_classifier")


class SeverityClassifier:
    @staticmethod
    def classify(label: str, confidence: float) -> str:
        """
        Classifies the severity level of a detection based on prediction label and confidence.
        Severity Levels: Critical, High, Medium, Low, Informational
        """
        if label.lower() != "fire":
            return "Informational"

        if confidence >= 0.90:
            return "Critical"
        elif confidence >= 0.75:
            return "High"
        elif confidence >= 0.60:
            return "Medium"
        elif confidence >= 0.50:
            return "Low"
        else:
            return "Informational"


severity_classifier = SeverityClassifier()
