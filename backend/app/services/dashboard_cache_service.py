import time
import asyncio
from typing import Any, Optional


class DashboardCacheService:
    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value if it exists and has not expired."""
        async with self._lock:
            if key not in self._cache:
                return None

            item = self._cache[key]
            if time.time() > item["expires_at"]:
                # Expired key; clean it up proactively
                del self._cache[key]
                return None

            return item["value"]

    async def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        """Cache a value with a configurable Time-To-Live (TTL) in seconds."""
        async with self._lock:
            self._cache[key] = {"value": value, "expires_at": time.time() + ttl_seconds}

    async def delete(self, key: str) -> None:
        """Explicitly evict a cache key."""
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        """Wipe all keys from the cache."""
        async with self._lock:
            self._cache.clear()


dashboard_cache_service = DashboardCacheService()
