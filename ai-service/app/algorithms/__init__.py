"""Algorithm building blocks for AI Career OS.

A small, dependency-light collection of the data-structure and algorithm
primitives the product leans on: an O(1) LRU/TTL cache (the OS-level cache shape
the rest of the system borrows), a stable bounded-heap top-K selector (priority
queue used for ranking, backed by the C-level `heapq`), vector math for
similarity, Okapi BM25 for lexical ranking, and the skill-gap/job-rank scorers.

Nothing here imports the web stack. Each module is independently testable,
which is the point: the interesting claims (cache eviction order, heap stability,
cosine vs. numpy agreement, BM25's hand-computable scores) are checked in
``tests/test_the_algorithms_module*.py``. Complexity claims are measured, not
assumed: a Python-level heap loop measured *slower* than Timsort at every size on
this host, so `top_k` deliberately delegates to the C `heapq.nlargest` path --
see that module's docstring and `docs/plans/ALGORITHMS_HORIZON.md`.
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
