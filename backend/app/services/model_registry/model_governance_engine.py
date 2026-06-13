import uuid
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model_registry import ModelVersion
from app.services.model_registry.artifact_storage_service import artifact_storage_service


class ModelGovernanceEngine:
    ACCURACY_THRESHOLD = 0.80  # Default accuracy threshold (80%)
    LOSS_SANITY_LIMIT = 2.0   # Maximum validation loss

    @classmethod
    def evaluate_governance_policies(
        cls,
        version: ModelVersion
    ) -> Tuple[bool, List[str]]:
        """
        Runs automated compliance policy checks on a model version.
        Returns a tuple of (is_compliant, failure_messages).
        """
        failures = []

        metrics = version.metrics or {}
        
        # 1. Validation Accuracy Gate
        accuracy = metrics.get("accuracy") or metrics.get("val_accuracy")
        if accuracy is None:
            failures.append("Missing validation accuracy metric.")
        else:
            # Handle decimals vs percentages
            acc_val = float(accuracy)
            if acc_val > 1.0:
                acc_val = acc_val / 100.0
            
            if acc_val < cls.ACCURACY_THRESHOLD:
                failures.append(
                    f"Validation accuracy ({acc_val * 100:.1f}%) is below the required governance threshold ({cls.ACCURACY_THRESHOLD * 100:.1f}%)."
                )

        # 2. Validation Loss Gate
        val_loss = metrics.get("loss") or metrics.get("val_loss")
        if val_loss is not None:
            loss_val = float(val_loss)
            if loss_val < 0.0 or loss_val > cls.LOSS_SANITY_LIMIT:
                failures.append(
                    f"Validation loss ({loss_val:.4f}) is suspicious/unstable (must be between 0.0 and {cls.LOSS_SANITY_LIMIT})."
                )

        # 3. Artifact Completeness Gate
        artifacts = version.artifacts or []
        has_weights = any(a.artifact_type == "weights" for a in artifacts)
        if not has_weights:
            failures.append("No weights checkpoint file registered in artifacts.")

        for art in artifacts:
            # Verify paths
            if not art.uri:
                failures.append(f"Artifact '{art.name}' has no storage path URI.")

        is_compliant = len(failures) == 0
        return is_compliant, failures


model_governance_engine = ModelGovernanceEngine()
