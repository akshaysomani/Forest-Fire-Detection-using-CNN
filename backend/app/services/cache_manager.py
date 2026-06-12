import time
from typing import Any, Dict, Optional, Tuple


class CacheManager:
    """Simple in-memory Key-Value Cache manager with TTL support."""
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            val, expiry = self._cache[key]
            if expiry > time.time():
                return val
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        expiry = time.time() + ttl_seconds
        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        self._cache.clear()


cache_manager = CacheManager()
