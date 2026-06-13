import logging
import gc
import torch
from typing import Dict, Any, List
from app.services.inference.model_manager import model_manager

logger = logging.getLogger("inference.model_cache_manager")


class ModelCacheManager:
    def __init__(self, max_cached_models: int = 3):
        self.max_cached_models = max_cached_models

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Compile cache sizing and target hardware allocations."""
        active_details = model_manager.get_active_model_details()
        return {
            "cached_keys": list(model_manager._cached_models.keys()),
            "cached_count": len(model_manager._cached_models),
            "max_cache_limit": self.max_cached_models,
            "device": str(model_manager.device),
            "active_model": active_details.get("model_name"),
            "active_checkpoint": active_details.get("checkpoint_path")
        }

    def enforce_retention_limit(self) -> None:
        """
        Enforce in-memory model limits. If cache size exceeds threshold,
        evicts the oldest loaded checkpoint (excluding the currently active model).
        """
        cached = model_manager._cached_models
        if len(cached) <= self.max_cached_models:
            return

        active_path = model_manager._active_checkpoint_path
        evict_candidates = [k for k in cached.keys() if k != active_path]

        if evict_candidates:
            # Evict first candidate
            oldest_key = evict_candidates[0]
            del cached[oldest_key]
            logger.info(f"Evicted model checkpoint '{oldest_key}' from memory to respect size limits.")
            
            # Clean up memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

    def purge_cache(self) -> None:
        """Clears memory allocations entirely."""
        model_manager.clear_cache()


model_cache_manager = ModelCacheManager()
