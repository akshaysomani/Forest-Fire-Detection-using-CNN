import logging
from typing import Dict, Any, List

logger = logging.getLogger("inference.prediction_metrics")


class PredictionMetrics:
    @staticmethod
    def calculate_precision_recall_f1(tp: int, fp: int, tn: int, fn: int) -> Dict[str, Any]:
        """
        Compute standard model evaluation metrics from a confusion matrix.
        """
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        accuracy = ((tp + tn) / (tp + fp + tn + fn)) if (tp + fp + tn + fn) > 0 else 0.0

        return {
            "confusion_matrix": {"true_positives": tp, "false_positives": fp, "true_negatives": tn, "false_negatives": fn},
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
        }


prediction_metrics = PredictionMetrics()
