"""The measured saving is stated honestly, and the invalidation boundary is named.

Epic 118's headline -- "the second identical question makes zero model calls" --
was only ever *measured with a MemoryCache installed by hand*. Every shipped
default is ``cache_backend=off``. This file makes both facts explicit and adds two
things Epic 118 never pinned:

1. **An A/B baseline across the three real backends** (off / memory / layered),
   counting the model+search work the pipeline actually does on the second ask.
   The claim is not "caching is always faster" (a fast wrong answer is not an
   optimisation) but: off recomputes, memory and layered both collapse the second
   ask to zero work. Counts are the assertion; wall-clock is recorded only as a
   loose sanity bound, because timing on a shared CI box proves nothing.

2. **The invalidation boundary, stated rather than hidden.** ``invalidate_user``
   is wired in exactly one place: ai-service's own ingestion pipeline. A backend
   that writes document chunks *directly* (SQL, another service, a backfill job)
   without going through that call does **not** bump the epoch. This test proves
   the cache will then serve the stale answer -- not to endorse it, but to pin the
   boundary so nobody claims epoch invalidation covers a write path it cannot see.
   The honest remediation is recorded in the plan doc: every corpus writer must
   call the invalidation seam, or the cache must stay off for that path.

Counts come from a Work counter around the pipeline's model/search seams, the same
technique as ``test_the_second_question_is_free.py``. No real Redis, no provider.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.core import cache as cache_mod
from app.rag import caching, pipeline

USER = "11111111-1111-1111-1111-111111111111"


class _Embedder:
    def __init__(self, dim=8):
        self.dim, self.calls = dim, 0

    async def embed(self, texts):
        self.calls += 1
        return [[float(len(t) % 7)] * self.dim for t in texts]


class Work:
    def __init__(self):
        self.understand = 0
        self.searches = 0
        self.rerank = 0
        self.embedder = _Embedder()

    @property
    def total(self):
        return self.understand + self.searches + self.rerank + self.embedder.calls


@pytest.fixture
def work(monkeypatch):
    w = Work()

    async def understand(query, context_summary="", **_):
        w.understand += 1
        return {"rewritten": query, "expansions": ["alt one", "alt two"],
                "intent": "personal_fact", "keywords": ["kafka", "spring"],
                "needs_personal_evidence": True, "filters": {}}

    def rows(prefix="chunk", n=3, tag="a"):
        return [{"id": f"{prefix}-{i}", "chunk_id": f"{tag}-{prefix}-{i}",
                 "document_id": "doc-1", "text": f"{tag} {prefix} text {i}",
                 "section_path": "Experience", "kind": "bullet", "meta": {},
                 "doc_title": "CV", "doc_id": "doc-1", "source_kind": "resume",
                 "score": 0.9 - i * 0.1} for i in range(n)]

    async def channel(*_args, **_kwargs):
        w.searches += 1
        # A backend "direct write" changes the corpus tag the search sees. The
        # cache, keyed only by query+generation, cannot know it changed. Read from
        # the Work *instance* so the test's `work.corpus_tag = "b"` takes effect.
        return rows(tag=w.corpus_tag)

    async def rerank(query, chunks, top_n=8, **_):
        w.rerank += 1
        out = []
        for i, c in enumerate(chunks[:top_n]):
            d = dict(c)
            d["rerank"] = round(0.9 - i * 0.1, 4)
            out.append(d)
        return out

    w.corpus_tag = "a"
    monkeypatch.setattr(pipeline, "understand", understand)
    monkeypatch.setattr(pipeline, "get_embeddings", lambda *a, **k: w.embedder)
    monkeypatch.setattr(pipeline.store, "vector_search", channel)
    monkeypatch.setattr(pipeline.store, "keyword_search", channel)
    monkeypatch.setattr(pipeline.store, "trigram_search", channel)
    monkeypatch.setattr(pipeline, "rerank", rerank)
    return w


def _install(backend: str):
    """Build a real backend offline. layered uses a MemoryCache as the shared
    layer's stand-in so the A/B needs no Redis server."""
    if backend == "off":
        cache = cache_mod.NullCache()
    elif backend == "memory":
        cache = cache_mod.MemoryCache(max_entries=128, ttl=300)
    elif backend == "layered":
        cache = cache_mod.LayeredCache(
            cache_mod.MemoryCache(max_entries=128, ttl=30),
            cache_mod.MemoryCache(max_entries=128, ttl=300))
    else:
        raise ValueError(backend)
    cache_mod.install_cache(cache)
    return cache


@pytest.fixture(autouse=True)
def _reset():
    yield
    cache_mod.install_cache(cache_mod.NullCache())
    flight = cache_mod.get_single_flight()
    flight.joined = flight.leaders = 0


async def ask(**kwargs):
    return await pipeline.retrieve("what does my resume say about kafka?",
                                   user_id=USER, **kwargs)


# --------------------------------------------------------------- the A/B baseline
@pytest.mark.parametrize("backend,repeats_for_free", [
    ("off", False),
    ("memory", True),
    ("layered", True),
])
def test_the_second_ask_costs_zero_work_only_when_caching_is_on(work, backend,
                                                                repeats_for_free):
    """The honest A/B: off recomputes the whole pipeline; memory and layered both
    collapse the second identical ask to zero model/search calls. This is a count,
    not a stopwatch -- it holds on a loaded box too."""
    _install(backend)
    first = asyncio.run(ask())
    spent_once = work.total
    assert first["evidence"], "the first ask found no evidence; the baseline proves nothing"
    assert spent_once >= 6, f"the fixture only measured {spent_once} calls; it is not counting"

    second = asyncio.run(ask())
    extra = work.total - spent_once
    if repeats_for_free:
        assert extra == 0, (
            f"{backend} spent {extra} more calls on the second identical question; "
            "Epic 118's 'second question is free' did not hold")
        assert second == first, "the cached answer is not the same answer"
    else:
        assert extra > 0, (
            "caching is off yet the second ask recomputed nothing; a disabled "
            "cache must make every ask a full pass (the shipped default)")


def test_off_is_the_shipped_default_not_an_accident():
    """Pin the deployment truth the health report's `off` verdict narrates.

    The code default is what ships; the operator's `.env` is the operator's call, so
    this pin reads the model with the environment file detached rather than the one
    this laptop happens to carry.
    """
    from app.core.config import Settings
    assert Settings(_env_file=None).cache_backend == "off"


def test_layered_counts_the_shared_hit_as_l2_not_a_local_hit():
    """The fleet-cheap signal: a layered cache that answers from the shared layer
    must book an l2 hit, so the health report can tell 'one process warm' from
    'the fleet warm'."""
    cache = _install("layered")
    # Seed only the shared layer; the front is cold, so the first get falls through.
    asyncio.run(cache.shared.set("k", "v"))
    assert asyncio.run(cache.get("k")) == "v"
    assert cache.stats.l2_hits == 1
    assert cache.stats.hits == 1


# --------------------------------------------------------------- the wall-clock sanity bound
def test_a_warm_memory_cache_is_not_slower_than_a_cold_recompute(work):
    """Wall clock is a *sanity bound*, never the claim. The work-count test above
    is the optimisation proof; this only catches a cache that made a hit more
    expensive than the recompute it replaced (a tax disguised as a cache)."""
    async def timed(backend):
        _install(backend)
        t0 = time.perf_counter()
        await ask()
        t1 = time.perf_counter()
        await ask()
        t2 = time.perf_counter()
        return t1 - t0, t2 - t1

    cold_first, cold_second = asyncio.run(timed("off"))
    warm_first, warm_second = asyncio.run(timed("memory"))
    # Loose bound: a warm hit should not cost more than a full recompute. No tight
    # ratio -- shared CI jitter makes that a flaky, meaningless assertion.
    assert warm_second <= cold_second * 1.5 + 0.01, (
        f"a cached hit ({warm_second:.4f}s) cost more than a full recompute "
        f"({cold_second:.4f}s); the cache is a tax, not a saving")


# --------------------------------------------------------------- the invalidation boundary
def test_a_direct_corpus_write_without_invalidate_serves_the_stale_answer(work):
    """THE boundary, stated honestly: ``invalidate_user`` is wired only into
    ai-service's ingestion pipeline. A backend that writes chunks directly and
    skips that seam does not move the epoch, so the cached answer survives a corpus
    that changed underneath it. This pins the limitation, not the desired behaviour:
    every corpus writer must call the invalidation seam or stay cache-off.
    """
    cache = _install("memory")
    first = asyncio.run(ask())
    # `quote` is the chunk text, which the fixture tags with the corpus generation;
    # it is a native evidence field, so no instrumentation leaks into the pipeline.
    quote_before = first["evidence"][0]["quote"]
    generation_before = asyncio.run(caching.epoch(USER))
    assert generation_before == 0

    # Simulate a backend direct write: the corpus the search reads changes, but
    # nobody called caching.invalidate_user(USER). The epoch does not move.
    work.corpus_tag = "b"
    assert asyncio.run(caching.epoch(USER)) == generation_before, (
        "the epoch moved without invalidate_user; the fixture is not modelling a "
        "direct write")

    after_direct_write = asyncio.run(ask())
    quote_after = after_direct_write["evidence"][0]["quote"]
    assert quote_after == quote_before, (
        "the cache noticed a write it has no seam to see; either the boundary is "
        "wider than documented or the fixture is wrong")

    # The documented remediation: the writer calls the invalidation seam.
    generation_after = asyncio.run(caching.invalidate_user(USER))
    assert generation_after > generation_before
    fresh = asyncio.run(ask())
    assert fresh["evidence"][0]["quote"] != quote_before, (
        "even an explicit invalidate did not surface the new corpus; the epoch "
        "invalidation contract is broken")
    assert "b " in fresh["evidence"][0]["quote"]
    assert cache.stats.lookups >= 3
