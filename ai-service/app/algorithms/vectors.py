"""Vector math for ranking, without a numpy dependency.

`cosine_similarity` agrees with the dense-vector path to float precision;
`SparseVector` covers the same ground when the terms are the coordinates.
Both guard the two degenerate inputs the cosine formula leaves undefined: a
zero-norm vector on either side scores 0.0 rather than nan.
"""

from __future__ import annotations

import math
from typing import Iterable


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    values_a = list(a)
    values_b = list(b)
    if len(values_a) != len(values_b):
        raise ValueError("vectors must have the same dimension")
    if not values_a:
        raise ValueError("vectors must not be empty")
    dot = norm_a = norm_b = 0.0
    for x, y in zip(values_a, values_b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / math.sqrt(norm_a * norm_b)


def rank_by_cosine(
    query: Iterable[float],
    documents: Iterable[Iterable[float]],
    k: int | None = None,
) -> list[tuple[int, float]]:
    """The documents' indices ranked by cosine against the query, best first.

    Ties break to the earlier document, so the ranking is stable across
    identical scores. Only the top ``k`` are returned when given.
    """
    query_list = list(query)
    scored = []
    for index, document in enumerate(documents):
        scored.append((index, cosine_similarity(query_list, document)))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored if k is None else scored[:k]


class SparseVector:
    """A dict-backed sparse vector: terms are the coordinates.

    `norm`, `dot` and `cosine` match the dense path to float precision, so a
    caller can mix the two representations on the same data without the
    answers drifting apart.
    """

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, float] | None = None) -> None:
        self._data: dict[str, float] = dict(data or {})

    @classmethod
    def from_tokens(cls, tokens: Iterable[str]) -> "SparseVector":
        """Term-frequency weights, count-1 smoothed like a plain histogram."""
        counts: dict[str, float] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0.0) + 1.0
        return cls(counts)

    def __len__(self) -> int:
        return len(self._data)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SparseVector) and self._data == other._data

    def __repr__(self) -> str:
        return f"SparseVector({self._data!r})"

    def norm(self) -> float:
        return math.sqrt(sum(value * value for value in self._data.values()))

    def dot(self, other: "SparseVector") -> float:
        # O(min(n, m)): iterate the smaller side of the coordinate intersection.
        small, big = (self, other) if len(self) <= len(other) else (other, self)
        return sum(small._data[term] * big._data[term] for term in small._data if term in big._data)

    def cosine(self, other: "SparseVector") -> float:
        denominator = self.norm() * other.norm()
        if denominator == 0.0:
            return 0.0
        return self.dot(other) / denominator

    def weight(self, term: str) -> float:
        return self._data.get(term, 0.0)
