from cachetools import TTLCache


class QueryCache:
    """
    Implements an in-memory, time-to-live (TTL) cache for query results.
    """

    def __init__(self, maxsize: int = 100, ttl: int = 300):
        """
        Initializes the QueryCache.

        Args:
            maxsize: The maximum number of items the cache can store.
            ttl: The time-to-live (in seconds) for cached items.
        """
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str):
        """
        Retrieves a value from the cache.

        Args:
            key: The key associated with the cached value.

        Returns:
            The cached value if found and not expired, otherwise None.
        """
        return self.cache.get(key)

    def set(self, key: str, value):
        """
        Stores a value in the cache.

        Args:
            key: The key to associate with the value.
            value: The value to store.
        """
        self.cache[key] = value
