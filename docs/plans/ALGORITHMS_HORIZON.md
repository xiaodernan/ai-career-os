# Algorithms horizon — Epics 132+

The product's loop is complete and the performance horizon (118–131) closed every
cost claim it made with a measurement. This horizon answers a different question
the operator actually pays for: **where does the algorithm come from, and is it
the cheapest one that gives the same answer?**

Epic 132 shipped a dependency-free algorithms package (`ai-service/app/algorithms`)
— an O(1) LRU/TTL, a stable O(n log k) heap top-K, dense/sparse cosine, Okapi BM25,
and the skill-gap/job-rank scorers — with 48 measured tests. A package nobody calls
is dead weight, so this horizon's rule is the repo's existing Definition of Done:
**an algorithm lands only when it replaces a live call site, and the replacement
is pinned by a test that fails if the old complexity sneaks back.**

| Epic | Claim | Verification |
|---|---|---|
| 132 | The primitives exist and are measured | `test_the_algorithms_module.py` (50) |
| 133 | The top-K helper uses the *right* heap for the scale | measurement + stability/streaming contract; fusion keeps its sort on purpose |
| 134 | A rerank that costs no model call is available and honest | `RERANK_MODE=bm25`, mode census, offline rerank tests |
| 135 | (next) The lexical channel can be scored in-process without pg_trgm when the corpus is small | to be measured |

## Rules
- No placeholder endpoints. Every mode/config knob is read by real code and pinned by
  the env/RAG-doc censuses in the same change.
- Complexity claims are measured with `time.perf_counter`, not asserted in prose.
- An algorithm that changes ranking is a behaviour change: the old ordering is pinned
  first, then the replacement must reproduce it. A mode that skips the model must say
  so in `describe()`/logs and never fabricate a score.
- Offline harness: `LLM_PROVIDER=mock EMBEDDING_PROVIDER=hash`. Docker-dependent suites
  stay recorded as not-run on this host.

## Epic 133 — the top-K helper uses the right heap for the scale **DONE (measured 2026-11-11)**

**This epic changed shape when it was measured, and the change is the point.** The
first sketch was to replace the full sort in `_fuse_rrf` (`app/agents/tools.py`)
with the bounded-heap `top_k`. Two measurements killed that idea before it shipped:

1. **The candidates are already SQL-LIMITed.** Both the keyword and semantic legs
   carry `LIMIT $n` with n clamped to ~10, so the fused set is a small constant.
   At that size a heap's asymptotic advantage is invisible and its per-item Python
   overhead is pure cost — the right tool is Timsort. Replacing it would have been
   optimising a number the database had already made small.
2. **A hand-written Python heap is slower than the C sort at every size tested.**
   Measured on this host (median of 9, `key` on descending RRF-like scores):

   | n (k=10) | `sorted` | Python tuple-heap `top_k` | `heapq.nlargest` |
   |---|---|---|---|
   | 1,000 | 0.058 ms | 0.123 ms | 0.064 ms |
   | 50,000 | 4.775 ms | 9.556 ms | **3.497 ms** |
   | 200,000 | 35.072 ms | 41.208 ms | **27.109 ms** |

**Do (what actually shipped).** `top_k` now delegates to the C-level
`heapq.nlargest` / `nsmallest`, which is stable, byte-for-byte equal to
`sorted(..., reverse=True)[:k]`, keeps only k items (O(k) space), and is the only
variant that actually wins at large n (~1.3x at 200k). `_fuse_rrf` deliberately keeps
its sort and now carries a comment recording *why*, so a future reader does not
re-attempt the same non-optimisation. The algorithms tests pin: stability across
scales and heavy ties, equivalence with a full sort, and selection over a 50k
generator (no `__len__`), which a materialise-and-sort helper would handle differently.

**Honest bound recorded in the test:** selection is still O(n) — it must see every
input; only *space* drops to O(k). An unbounded source has no "top k" and the helper
does not pretend to answer one. The C-heap win is for places n is genuinely large,
which Epic 134 begins to exercise (scoring a candidate corpus in-process).

**Done when** `test_the_algorithms_module.py` 50/50 and `test_job_search_hybrid.py`
unchanged/green; `_fuse_rrf` still returns byte-for-byte the same order.

## Epic 134 — a rerank that costs no model call

**Measured.** `rag/rerank.py` offers two modes: `llm` (an LLM relevance pass, one model
call, tens of tokens per candidate) and `none` (skip entirely — fused RRF order). There
is no middle: on a host with no provider configured, or on a query where spending a
model call is not worth it, the reader gets either a bill or no lexical re-scoring at
all. Meanwhile `app.algorithms.Bm25` is a pure-Python ranker that scores the same
fused candidates against the query in microseconds and needs no network.

**Do.** Add `RERANK_MODE=bm25`: build a BM25 index over the fused candidate texts,
re-order down to `top_n` by `score(query, i)`, and inject a `rerank` field that is
*the normalized BM25 score* — the same field the LLM path writes, so `to_evidence`
and the citation path need no change. `none` still skips. Keep `llm` the default so
no deployment changes behaviour until an operator opts in.

**Done when** (a) the mode census (`test_the_rag_doc_names_what_the_code_ships.py`)
and env-declaration census pass with `bm25` named in config comment, `.env.example`
and `docs/RAG.md`; (b) offline tests prove `bm25` orders by lexical relevance, keeps
stable ties, injects finite normalized scores, and never calls `ask_json`; (c) the
existing six rerank degradation tests still pass; (d) a measured note records the
BM25 pass's wall time on a 40-candidate corpus.
