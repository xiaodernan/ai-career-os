"""Top-K and bottom-K selection over an iterable, in O(n log k).

`heapq.nlargest`/`nsmallest` do this; these two wrap them so the call site
says what it wants, takes a key, and takes a stable tie-break: when two
items score the same, the earlier one in the input wins, deterministically.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")


def top_k(iterable: Iterable[T], k: int, key: Callable[[T], float] | None = None) -> list[T]:
    """The k largest items, best first, in O(n log k) time and O(k) extra space.

    Tie-break is stable: at equal score the earlier item in the input wins.
    """
    if k < 0:
        raise ValueError("k must be >= 0")
    score = key or (lambda item: item)
    best: list[tuple[float, int, T]] = []  # min-heap keyed on (score, index)
    for index, item in enumerate(iterable):
        entry = (score(item), index, item)
        if len(best) < k:
            heapq.heappush(best, entry)
        elif entry[0] > best[0][0]:
            # A strictly better score wins the cut; at equal score the earlier
            # item already in the heap survives, so input order is kept.
            heapq.heapreplace(best, entry)
    best.sort(key=lambda e: (-e[0], e[1]))
    return [item for _, _, item in best]


def bottom_k(iterable: Iterable[T], k: int, key: Callable[[T], float] | None = None) -> list[T]:
    """The k smallest items, worst first (ascending score), in O(n log k) time."""
    if k < 0:
        raise ValueError("k must be >= 0")
    score = key or (lambda item: item)
    worst: list[tuple[float, int, T]] = []  # max-heap keyed on -(score, index)
    for index, item in enumerate(iterable):
        entry = (-score(item), index, item)
        if len(worst) < k:
            heapq.heappush(worst, entry)
        elif entry[0] > worst[0][0]:
            # A strictly better score (lower) evicts the weakest kept item; at
            # equal score the earlier item already in the heap survives.
            heapq.heapreplace(worst, entry)
    worst.sort(key=lambda e: (-e[0], e[1]))  # scores ascending, ties by input order
    return [item for _, _, item in worst]
