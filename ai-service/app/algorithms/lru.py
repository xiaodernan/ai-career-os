"""The OS-level cache primitive: an LRU with O(1) get and put.

The rest of the system borrows this shape constantly (layers of cache, a
bounded identity map). Writing it down once, with the eviction order pinned
by a test, keeps every caller honest: after ``put`` on a full cache, the
*least recently used* entry is gone, and reading refreshes recency.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Generic, Iterator, MutableMapping, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LruCache(MutableMapping[K, V], Generic[K, V]):
    """A bounded LRU over an OrderedDict.

    Invariants (pinned by tests):

    * ``maxsize`` is a hard bound; inserting into a full cache evicts the
      least recently used entry before the new one lands.
    * A ``get`` refreshes recency; a ``peek`` does not (the caller can inspect
      without perturbing the order).
    * ``clear()`` empties; ``len()`` never exceeds ``maxsize``.
    """

    def __init__(self, maxsize: int = 128) -> None:
        if not isinstance(maxsize, int) or maxsize < 1:
            raise ValueError("maxsize must be a positive integer")
        self.maxsize = maxsize
        self._items: OrderedDict[K, V] = OrderedDict()

    # -- read paths ---------------------------------------------------
    def get(self, key: K, default: V | None = None) -> V | None:  # type: ignore[override]
        try:
            value = self._items.pop(key)
        except KeyError:
            return default
        self._items[key] = value
        return value

    def peek(self, key: K, default: V | None = None) -> V | None:  # type: ignore[override]
        return self._items.get(key, default)

    def __getitem__(self, key: K) -> V:
        try:
            value = self._items.pop(key)
        except KeyError:
            raise KeyError(key) from None
        self._items[key] = value
        return value

    def __setitem__(self, key: K, value: V) -> None:
        if key in self._items:
            self._items.pop(key)
        elif len(self._items) >= self.maxsize:
            self._items.popitem(last=False)  # evict the LRU, and say so in the name
        self._items[key] = value

    def __delitem__(self, key: K) -> None:
        del self._items[key]

    def __iter__(self) -> Iterator[K]:
        # Iterate oldest -> newest; the mapping protocol promises no order,
        # but our callers lean on this for eviction-order checks.
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()


class TtlCache(LruCache[K, V], Generic[K, V]):
    """An LRU whose entries also expire after ``ttl`` seconds (monotonic clock).

    Expiry is lazy: nothing sweeps in the background, and a lookup of an
    expired entry returns the default and evicts the entry. ``purge()`` is
    the eager path for tests and for callers that want the bound enforced
    on demand.
    """

    def __init__(self, maxsize: int = 128, ttl: float = 60.0) -> None:
        if ttl <= 0:
            raise ValueError("ttl must be positive seconds")
        super().__init__(maxsize=maxsize)
        self.ttl = float(ttl)
        import time

        self._now = time.monotonic
        self._birth: dict[K, float] = {}

    def _expired(self, key: K) -> bool:
        born = self._birth.get(key)
        return born is not None and (self._now() - born) > self.ttl

    def get(self, key: K, default: V | None = None) -> V | None:  # type: ignore[override]
        if self._expired(key):
            self._drop(key)
            return default
        return super().get(key, default)

    def peek(self, key: K, default: V | None = None) -> V | None:  # type: ignore[override]
        if self._expired(key):
            self._drop(key)
            return default
        return super().peek(key, default)

    def __getitem__(self, key: K) -> V:
        if self._expired(key):
            self._drop(key)
            raise KeyError(key)
        return super().__getitem__(key)

    def __setitem__(self, key: K, value: V) -> None:
        if key in self._items and not self._expired(key):
            self._items.pop(key)  # refresh recency like the base class, keep birth updated
        super().__setitem__(key, value)
        self._birth[key] = self._now()

    def __delitem__(self, key: K) -> None:
        self._drop(key)

    def __len__(self) -> int:
        # Only live entries count; expired ones are collectible on read or purge.
        self.purge()
        return super().__len__()

    def _drop(self, key: K) -> None:
        self._birth.pop(key, None)
        try:
            super().__delitem__(key)
        except KeyError:
            pass

    def purge(self) -> int:
        """Drop every expired entry; return how many were dropped."""
        dead = [k for k in list(self._items) if self._expired(k)]
        for key in dead:
            self._drop(key)
        return len(dead)
