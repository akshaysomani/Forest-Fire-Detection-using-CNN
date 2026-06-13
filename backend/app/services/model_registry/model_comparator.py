from typing import Dict, Any
from app.models.model_registry import ModelVersion


class ModelComparator:
    @staticmethod
    def compare_versions(version_a: ModelVersion, version_b: ModelVersion) -> Dict[str, Any]:
        """
        Compares two model versions.
        Returns a dict containing:
        - metrics_diff: dictionary of differences in float metrics (version_b - version_a)
        - hyperparameters_diff: dictionary indicating if values changed, added, or removed.
        """
        metrics_a = version_a.metrics or {}
        metrics_b = version_b.metrics or {}
        
        # 1. Metrics Difference
        metrics_diff = {}
        # Merge all numeric metric keys
        all_metric_keys = set(metrics_a.keys()).union(set(metrics_b.keys()))
        for key in all_metric_keys:
            val_a = metrics_a.get(key)
            val_b = metrics_b.get(key)
            # Evaluate only if values are numeric
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                metrics_diff[key] = {
                    "value_a": val_a,
                    "value_b": val_b,
                    "difference": val_b - val_a
                }
            elif val_a is not None or val_b is not None:
                metrics_diff[key] = {
                    "value_a": val_a,
                    "value_b": val_b,
                    "difference": "non-numeric-comparison"
                }

        # 2. Hyperparameters Difference
        hp_a = version_a.hyperparameters or {}
        hp_b = version_b.hyperparameters or {}
        hp_diff = {}
        all_hp_keys = set(hp_a.keys()).union(set(hp_b.keys()))
        
        for key in all_hp_keys:
            val_a = hp_a.get(key)
            val_b = hp_b.get(key)
            if val_a != val_b:
                hp_diff[key] = {
                    "value_a": val_a,
                    "value_b": val_b,
                    "changed": True
                }
            else:
                hp_diff[key] = {
                    "value_a": val_a,
                    "value_b": val_b,
                    "changed": False
                }

        return {
            "metrics_diff": metrics_diff,
            "hyperparameters_diff": hp_diff
        }


model_comparator = ModelComparator()
