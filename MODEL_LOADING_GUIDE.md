# Model Loading & Caching Guide

This document describes how PyTorch models are loaded, cached, validated, and hot-swapped under production operations.

---

## 1. Dynamic Weight Resolution

The `model_registry_adapter` queries the training database records to select the best checkpoint:
*   When a prediction request arrives, the system attempts to fetch the best checkpoint (`is_best=True`) from the latest completed training run.
*   If no completed training runs are registered, the `ModelManager` gracefully falls back to an un-pretrained, default `CustomCNN` instance (shape: `3x224x224`, output classes: 2).

---

## 2. In-Memory Model Cache Policy

Loaded PyTorch models (which weigh between 40MB and 250MB+) are cached in memory to eliminate checkpoint loading overhead (reducing run latency from ~1.5s to <50ms).

*   **Eviction Policy:** The `ModelCacheManager` limits the memory footprint to `max_cached_models=3`.
*   **LRU Eviction:** If a 4th model is loaded, the manager evicts the oldest unused model from the cache dictionary and triggers `gc.collect()` along with `torch.cuda.empty_cache()` to prevent CPU/GPU memory leaks.
*   **Manual Cache Flush:** Cache sizing and purging can be triggered via:
```python
from app.services.inference.model_cache_manager import model_cache_manager
model_cache_manager.purge_cache()
```

---

## 3. Hot-Swapping Active Models

To update the active inference model version without bringing down the API containers, request the manager to load a new target checkpoint path:
```python
from app.services.inference.model_manager import model_manager

# Update pointer to run ID 'a908be56-02e4-4fb0-85f6-db23c1fd33b8'
await model_manager.load_and_set_active_model(
    model_name="resnet50",
    checkpoint_path="runs/a908be56-02e4-4fb0-85f6-db23c1fd33b8/checkpoints/best_model.pth",
    run_id="a908be56-02e4-4fb0-85f6-db23c1fd33b8"
)
```
Subsequent prediction requests automatically route through the newly swapped ResNet-50 model.
