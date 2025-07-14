try:
    from cachetools import TTLCache
    CACHE_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency missing
    CACHE_AVAILABLE = False

    class TTLCache(dict):  # type: ignore
        def __init__(self, maxsize: int = 100, ttl: int = 300):
            super().__init__()

class QueryCache:
    """Simple TTL cache wrapper."""

    def __init__(self, maxsize: int = 100, ttl: int = 300):
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str):
        return self.cache.get(key)

    def set(self, key: str, value):
        self.cache[key] = value
