from typing import Dict, Any, List
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix


class MetricsCalculator:
    @staticmethod
    def compute_all_metrics(y_true: List[int], y_pred: List[int], y_prob: List[float]) -> Dict[str, Any]:
        """
        Compute Accuracy, Precision, Recall, F1 Score, ROC AUC, and Confusion Matrix.
        y_true: list of actual class integers (0 or 1)
        y_pred: list of predicted class integers (0 or 1)
        y_prob: list of predicted class probability floats for class 1
        """
        if not y_true:
            return {
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "roc_auc": 0.0,
                "confusion_matrix": {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
            }

        y_true_arr = np.array(y_true)
        y_pred_arr = np.array(y_pred)
        y_prob_arr = np.array(y_prob)

        # Basic metrics with zero_division protection
        accuracy = accuracy_score(y_true_arr, y_pred_arr)
        precision = precision_score(y_true_arr, y_pred_arr, zero_division=0)
        recall = recall_score(y_true_arr, y_pred_arr, zero_division=0)
        f1 = f1_score(y_true_arr, y_pred_arr, zero_division=0)

        # ROC AUC
        try:
            if len(np.unique(y_true_arr)) > 1:
                roc_auc = roc_auc_score(y_true_arr, y_prob_arr)
            else:
                roc_auc = 1.0  # Trivial single-class case
        except Exception:
            roc_auc = 0.5

        # Confusion Matrix
        cm = confusion_matrix(y_true_arr, y_pred_arr)
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
        else:
            tn, fp, fn, tp = 0, 0, 0, 0
            if len(np.unique(y_true_arr)) == 1:
                if y_true_arr[0] == 0:
                    tn = int(np.sum(y_pred_arr == 0))
                    fp = int(np.sum(y_pred_arr == 1))
                else:
                    fn = int(np.sum(y_pred_arr == 0))
                    tp = int(np.sum(y_pred_arr == 1))

        return {
            "accuracy": round(float(accuracy), 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4),
            "roc_auc": round(float(roc_auc), 4),
            "confusion_matrix": {
                "tn": int(tn),
                "fp": int(fp),
                "fn": int(fn),
                "tp": int(tp)
            }
        }


metrics_calculator = MetricsCalculator()
