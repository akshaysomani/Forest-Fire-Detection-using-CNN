import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from typing import Dict, Any, List
from app.services.training.metrics_calculator import metrics_calculator


class EvaluationService:
    @staticmethod
    def evaluate_model(
        model: nn.Module,
        dataloader: DataLoader,
        device: torch.device
    ) -> Dict[str, Any]:
        """
        Evaluate model against validation/testing loader.
        Returns calculated metrics: accuracy, precision, recall, f1_score, roc_auc, confusion_matrix.
        """
        model.eval()
        y_true: List[int] = []
        y_pred: List[int] = []
        y_prob: List[float] = []

        # Apply Softmax to map outputs to probabilities
        softmax = nn.Softmax(dim=1)

        with torch.no_grad():
            for inputs, targets in dataloader:
                inputs = inputs.to(device)
                outputs = model(inputs)

                probs = softmax(outputs)
                # Extract probabilities of the positive class (class index 1, representing Fire)
                # If the model has 2 classes, probs[:, 1] is positive class probability
                if probs.shape[1] > 1:
                    p1 = probs[:, 1].cpu().numpy().tolist()
                else:
                    p1 = probs[:, 0].cpu().numpy().tolist()

                _, predicted = outputs.max(1)

                y_true.extend(targets.numpy().tolist())
                y_pred.extend(predicted.cpu().numpy().tolist())
                y_prob.extend(p1)

        return metrics_calculator.compute_all_metrics(y_true, y_pred, y_prob)


evaluation_service = EvaluationService()
