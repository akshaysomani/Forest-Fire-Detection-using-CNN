import logging
from typing import List, Tuple, Optional

logger = logging.getLogger("inference.classification_service")


class ClassificationService:
    def __init__(self, default_threshold: float = 0.5):
        self.default_threshold = default_threshold
        # Index 0 is non-fire, Index 1 is fire
        self.classes = ["non-fire", "fire"]

    def resolve_classification(self, probabilities: List[float], threshold: Optional[float] = None) -> Tuple[str, float]:
        """
        Map model probabilities list [P(non-fire), P(fire)] to class string and confidence score.
        If P(fire) exceeds threshold, classifies as 'fire'.
        Returns a tuple of (label, confidence).
        """
        if len(probabilities) < 2:
            raise ValueError(f"Model output probabilities must contain at least 2 classes. Got: {probabilities}")

        target_threshold = threshold if threshold is not None else self.default_threshold

        p_non_fire = probabilities[0]
        p_fire = probabilities[1]

        # Determine class label and confidence score
        if p_fire >= target_threshold:
            label = "fire"
            confidence = p_fire
        else:
            label = "non-fire"
            confidence = p_non_fire

        return label, confidence


# Initialize default instance
classification_service = ClassificationService()
