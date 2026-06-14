from typing import Callable, Any, Dict
from app.services.dashboard_cache_service import dashboard_cache_service


class MetricsOptimizer:
    @staticmethod
    async def get_or_aggregate(cache_key: str, aggregator_fn: Callable, ttl_seconds: int = 60, *args, **kwargs) -> Any:
        """
        Bypasses executing database queries if the requested key exists in cache.
        If empty, runs the database aggregator function and stores the result.
        """
        cached_val = await dashboard_cache_service.get(cache_key)
        if cached_val is not None:
            return cached_val

        # Execute raw function on cache miss
        result = await aggregator_fn(*args, **kwargs)
        await dashboard_cache_service.set(cache_key, result, ttl_seconds)
        return result


metrics_optimizer = MetricsOptimizer()
