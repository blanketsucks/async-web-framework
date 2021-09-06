from typing import Any, Dict, Optional, List
import time

from .request import Request

__all__ = (
    'RatelimitExceeded',
    'Bucket',
    'RatelimiteHandler'
)

class RatelimitExceeded(Exception):
    def __init__(self, retry_after: float, key: 'Key') -> None:
        self.retry_after = retry_after
        self.key = key
        self.bucket = key.bucket

        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")

class Key:
    """
    Attributes:
        bucket: The ratelimit [Bucket](ratelimits.md).
    """
    def __init__(self, bucket: 'Bucket') -> None:
        self.bucket = bucket

        self._last = 0.0
        self._window = 0.0
        self._remaining = self.rate

    def update(self, current: Optional[float]=None):
        """
        Updates the ratelimit.

        Args:
            current: The current time.
        """
        current = current or time.time()
        self._last = current

        self._remaining = self.get_remaining(current)

        if self._remaining == self.rate:
            self._window = current

        if self._remaining == 0:
            return self.per - (current - self._window)

        self._remaining -= 1

    @property
    def rate(self) -> int:
        """
        Returns:
            The rate-limit.
        """
        return self.bucket.rate

    @property
    def per(self) -> float:
        """
        Returns:
            The period.
        """
        return self.bucket.per

    def get_remaining(self, current: float) -> int:
        """
        Gets the remaining time.

        Args:
            current: The current time.

        Returns:
            The remaining time.
        """
        remaining = self._remaining

        if current > self._window + self.per:
            remaining = self.rate

        return remaining

class Bucket:
    """
    A rate limit bucket.

    Attributes:
        rate: The rate limit per second.
        per: The time window in seconds.
        path: The path to the bucket.
    """
    def __init__(self, rate: int, per: float, path: Optional[str]) -> None:
        self.rate = rate
        self.per = per
        self.path = path

        self._keys: Dict[Any, Key] = {}

    @property
    def keys(self) -> List[Key]:
        """
        Returns:
            A list of [Key](./ratelimits.md)s.
        """
        return list(self._keys.values())

    def add_key(self, value: Any) -> Key:
        """
        Adds a [Key](ratelimits.md) to the bucket.

        Args:
            value: The value of that key to add.

        Returns:
            The [Key](ratelimits.md) added.
        """
        key = Key(self)
        self._keys[value] = key

        return key

    def get_key(self, value: Any) -> Optional[Key]:
        """
        Returns:
            The [Key](ratelimits.md) for that value.
        """
        return self._keys.get(value)

    def update_ratelimit(self, request: Request, value: Any) -> None:
        """
        Updates the ratelimit for a [Key](ratelimits.md).

        Args:
            request: The [Request](./request.md) object.
            value: The value of that key.

        Raises:
            RatelimitExceeded: If the ratelimit is exceeded.
        """
        key = self.get_key(value)
        if not key:
            key = self.add_key(value)

        after = key.update(current=request.created_at.timestamp())
        if after:
            raise RatelimitExceeded(after, key)

class RatelimiteHandler:
    """
    The main ratelimit handler.
    """
    def __init__(self, global_rate: Optional[int]=None, global_per: Optional[float]=None) -> None:
        self._buckets: Dict[str, Bucket] = {}

        if not global_rate:
            if global_per:
                raise ValueError("Global rate must be specified if global per is specified.")

            self._global_bucket = None

        else:
            if not global_per:
                raise ValueError("Global per must be specified if global rate is specified.")

            self._global_bucket = Bucket(global_rate, global_per, None)

    def add_bucket(self, path: str, *, rate: int, per: float) -> Bucket:
        """
        Adds a [Bucket](./ratelimits.md) to the handler.

        Args:
            path: The path to the bucket.
            rate: The rate limit per second.
            per: The time window in seconds.
        """
        bucket = Bucket(rate, per, path)
        self._buckets[path] = bucket

        return bucket

    def get_bucket(self, path: str) -> Optional[Bucket]:
        """
        Gets a [Bucket](ratelimits.md) from the handler.

        Args:
            path: The path to the bucket.
        """
        return self._buckets.get(path)

    def get_global_bucket(self) -> Optional[Bucket]:
        """
        Gets the global [Bucket](ratelimits.md).
        """
        return self._global_bucket
