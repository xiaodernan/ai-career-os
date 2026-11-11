"""Algorithm building blocks for AI Career OS.

A small, dependency-light collection of the data-structure and algorithm
primitives the product leans on: an O(1) LRU cache (the OS-level cache the
rest of the system borrows), a heap-based top-K selector (priority queue used
for ranking), vector math for similarity, and BM25 for lexical ranking.

Nothing here imports the web stack. Each module is independently testable,
which is the point: the interesting claims (cache eviction order, heap
stability, cosine vs. numpy agreement) are checked in
``tests/test_the_algorithms_module_*.py``.
"""

from app.algorithms.lru import LruCache, TtlCache
from app.algorithms.topk import top_k, bottom_k
from app.algorithms.vectors import cosine_similarity, rank_by_cosine, SparseVector
from app.algorithms.bm25 import Bm25
from app.algorithms.recommend import skill_gap, rank_jobs

__all__ = [
    "LruCache",
    "TtlCache",
    "top_k",
    "bottom_k",
    "cosine_similarity",
    "rank_by_cosine",
    "SparseVector",
    "Bm25",
    "skill_gap",
    "rank_jobs",
]
