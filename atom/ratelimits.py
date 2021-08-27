from typing import Any, Dict, Optional
import time

from .request import Request

__all__ = (
    'Ratelimited',
    'Bucket',
    'RatelimiteHandler'
)

class Ratelimited(Exception):
    def __init__(self, retry_after: float, key: 'Key') -> None:
        self.retry_after = retry_after
        self.key = key
        self.bucket = key.bucket

        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")

class Key:
    def __init__(self, bucket: 'Bucket') -> None:
        self.bucket = bucket

        self._last = 0.0
        self._window = 0.0
        self._remaining = self.rate

    def update(self, current: Optional[float]=None):
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
        return self.bucket.rate

    @property
    def per(self) -> float:
        return self.bucket.per

    def get_remaining(self, current: float) -> int:
        remaining = self._remaining

        if current > self._window + self.per:
            remaining = self.rate

        return remaining

class Bucket:
    def __init__(self, rate: int, per: float, path: Optional[str]) -> None:
        self.rate = rate
        self.per = per
        self.path = path

        self._keys: Dict[Any, Key] = {}

    @property
    def keys(self):
        return self._keys

    def add_key(self, value: Any) -> Key:
        key = Key(self)
        self._keys[value] = key

        return key

    def get_key(self, value: Any) -> Optional[Key]:
        return self._keys.get(value)

    def update_ratelimit(self, request: Request, value: Any) -> None:
        key = self.get_key(value)
        if not key:
            return

        after = key.update(current=request.created_at.timestamp())
        if after:
            raise Ratelimited(after, key)

class RatelimiteHandler:
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
        bucket = Bucket(rate, per, path)
        self._buckets[path] = bucket

        return bucket

    def get_bucket(self, path: str) -> Optional[Bucket]:
        return self._buckets.get(path)

    def get_global_bucket(self) -> Optional[Bucket]:
        return self._global_bucket
