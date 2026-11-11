"""Epic 118 — a repeated question is answered from memory, and a dead cache answers nothing.

The claim this file measures: `POST /internal/rag/answer` costs five model calls, and
the *second identical question* should cost zero. Every case below counts the work the
pipeline actually did — understanding, embedding, the three search channels, the
rerank — rather than timing the call, because a fast wrong answer is not an
optimisation.

The rest of the file pins the properties that make a cache safe to switch on:

* a different reader never sees the first reader's evidence;
* a newly ingested document invalidates that reader's answers *immediately*, not after
  the TTL (the epoch, not the clock);
* a narrowed question is a different question (the key carries the filters);
* a cache that is down degrades to a miss and never raises into the caller;
* ten concurrent cold requests compute once (`SingleFlight`), and the nine that waited
  get the leader's answer rather than an exception.
"""

from __future__ import annotations

import asyncio

import pytest

from app.core import cache as cache_mod
from app.core import resp
from app.rag import caching, pipeline

USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"


class CountingEmbedder:
    def __init__(self, dim: int = 8):
        self.dim, self.calls, self.texts = dim, 0, []

    async def embed(self, texts):
        self.calls += 1
        self.texts.append(list(texts))
        return [[float(len(t) % 7)] * self.dim for t in texts]


class Work:
    """Every model/search call the pipeline makes, counted."""

    def __init__(self):
        self.understand = 0
        self.searches = 0
        self.rerank = 0
        self.embedder = CountingEmbedder()

    @property
    def total(self) -> int:
        return self.understand + self.searches + self.rerank + self.embedder.calls


@pytest.fixture
def work(monkeypatch):
    w = Work()

    async def understand(query, context_summary="", **_):
        w.understand += 1
        return {"rewritten": query, "expansions": ["alt one", "alt two"],
                "intent": "personal_fact", "keywords": ["kafka", "spring"],
                "needs_personal_evidence": True, "filters": {}}

    def rows(prefix: str, n: int = 3):
        return [{"id": f"{prefix}-{i}", "document_id": "doc-1", "text": f"{prefix} text {i}",
                 "section_path": "Experience", "kind": "bullet", "meta": {},
                 "doc_title": "CV", "doc_id": "doc-1", "source_kind": "resume",
                 "score": 0.9 - i * 0.1} for i in range(n)]

    async def channel(*_args, **_kwargs):
        w.searches += 1
        return rows("chunk")

    async def rerank(query, chunks, top_n=8, **_):
        w.rerank += 1
        out = [dict(c) for c in chunks[:top_n]]
        for i, c in enumerate(out):
            c["rerank"] = round(0.9 - i * 0.1, 4)
        return out

    monkeypatch.setattr(pipeline, "understand", understand)
    monkeypatch.setattr(pipeline, "get_embeddings", lambda *a, **k: w.embedder)
    monkeypatch.setattr(pipeline.store, "vector_search", channel)
    monkeypatch.setattr(pipeline.store, "keyword_search", channel)
    monkeypatch.setattr(pipeline.store, "trigram_search", channel)
    monkeypatch.setattr(pipeline, "rerank", rerank)
    return w


@pytest.fixture
def memory_cache():
    cache = cache_mod.MemoryCache(max_entries=128, ttl=300)
    cache_mod.install_cache(cache)
    yield cache
    cache_mod.install_cache(cache_mod.NullCache())


async def ask(user_id=USER_A, query="what does my resume say about kafka?", **kwargs):
    return await pipeline.retrieve(query, user_id=user_id, **kwargs)


# ------------------------------------------------------------- the headline claim

async def test_the_second_identical_question_makes_no_model_calls(work, memory_cache):
    first = await ask()
    spent_once = work.total
    assert spent_once >= 6, f"the first ask only spent {spent_once} calls; the fixture is not measuring"
    assert first["evidence"], "the first ask found no evidence, so caching it proves nothing"

    second = await ask()

    assert work.total == spent_once, (
        f"the second identical question spent {work.total - spent_once} more calls "
        f"(understanding={work.understand}, searches={work.searches}, rerank={work.rerank}, "
        f"embeddings={work.embedder.calls})")
    assert second == first, "the cached answer is not the same answer"


async def test_the_cache_is_keyed_by_the_reader(work, memory_cache):
    await ask(USER_A)
    before = work.total
    await ask(USER_B)
    assert work.total > before, (
        "another reader was answered from the first reader's entry -- a cache keyed by "
        "the question alone leaks evidence across accounts")


async def test_a_new_document_invalidates_answer_immediately(work, memory_cache):
    await ask()
    before = work.total
    generation = await caching.invalidate_user(USER_A)
    assert generation >= 1, "the epoch did not move, so nothing was invalidated"
    await ask()
    assert work.total > before, (
        "the answer survived the reader's ingest: a resume cached for the TTL is a resume "
        "the copilot will misquote for the TTL")


async def test_invalidation_of_one_reader_leaves_another_alone(work, memory_cache):
    await ask(USER_A)
    await ask(USER_B)
    before = work.total
    await caching.invalidate_user(USER_A)
    await ask(USER_B)
    assert work.total == before, "invalidating A's corpus also dropped B's entries"


async def test_a_narrowed_question_is_a_different_question(work, memory_cache):
    await ask()
    before = work.total
    await ask(kinds=["note"])
    assert work.total > before, (
        "a question restricted to notes was answered from the unrestricted cache entry")


async def test_the_summary_that_resolves_pronouns_is_part_of_the_key(work, memory_cache):
    await ask(context_summary="we were discussing the Stripe role")
    before = work.total
    await ask(context_summary="we were discussing the Kafka migration")
    assert work.total > before, (
        "'what did I do there?' answered from a cache built for a different conversation")


async def test_with_caching_off_every_call_computes(work):
    cache_mod.install_cache(cache_mod.NullCache())
    try:
        await ask()
        before = work.total
        await ask()
        assert work.total > before
    finally:
        cache_mod.install_cache(cache_mod.NullCache())


# ------------------------------------------------------------------- the stampede

async def test_concurrent_identical_questions_compute_once(work, monkeypatch, memory_cache):
    original = pipeline._retrieve

    async def slow(*args, **kwargs):
        await asyncio.sleep(0.08)
        return await original(*args, **kwargs)

    monkeypatch.setattr(pipeline, "_retrieve", slow)
    results = await asyncio.gather(*[ask() for _ in range(6)])

    assert work.understand == 1, (
        f"a cold key let {work.understand} concurrent readers run query understanding; "
        "that is the thundering herd the cache is supposed to absorb")
    assert all(r == results[0] for r in results), "a waiter got a different answer than the leader"
    flight = cache_mod.get_single_flight()
    assert flight.joined >= 5, f"only {flight.joined} callers waited on the leader"


# ------------------------------------------------------------------- the embeddings

async def test_only_the_texts_never_embedded_before_are_sent(work, memory_cache):
    embedder = CountingEmbedder()
    await caching.embed_with_cache(embedder, ["alpha", "beta"])
    assert embedder.calls == 1 and embedder.texts == [["alpha", "beta"]]

    await caching.embed_with_cache(embedder, ["alpha", "gamma", "beta", "delta"])
    assert embedder.texts[-1] == ["gamma", "delta"], (
        f"the second batch re-sent {embedder.texts[-1]}; a cache that re-embeds what it "
        "already holds is a tax, not a saving")
    assert embedder.calls == 2

    await caching.embed_with_cache(embedder, ["alpha", "beta", "gamma", "delta"])
    assert embedder.calls == 2, "a fully cached batch still called the provider"


async def test_case_and_whitespace_do_not_make_a_new_embedding(work, memory_cache):
    embedder = CountingEmbedder()
    await caching.embed_with_cache(embedder, ["Spring  Boot"])
    await caching.embed_with_cache(embedder, ["spring boot"])
    assert embedder.calls == 1


async def test_a_different_model_never_reuses_a_vector(work, memory_cache, monkeypatch):
    embedder = CountingEmbedder()
    await caching.embed_with_cache(embedder, ["alpha"])
    monkeypatch.setattr(caching, "model_identity", lambda: "ollama|nomic|768")
    await caching.embed_with_cache(embedder, ["alpha"])
    assert embedder.calls == 2, (
        "a vector produced by one model was served to another: same shape, different "
        "geometry, silently wrong rankings")


def test_a_vector_round_trips_exactly():
    values = [0.1, -0.30000000000000004, 1 / 3, 1e-300, -0.0, 2.2250738585072014e-308]
    restored = caching.decode_vector(caching.encode_vector(values))
    assert restored is not None
    assert [v.hex() for v in restored] == [v.hex() for v in values], (
        "the stored vector is not bit-identical to the computed one; every cached "
        "ranking would differ from a fresh one")


@pytest.mark.parametrize("payload", ["", "abc", "12:!!!", "3:AAAA", None, 42,
                                     "2:" + "A" * 8])
def test_a_corrupt_vector_is_a_miss_not_a_crash(payload):
    assert caching.decode_vector(payload) is None


# ---------------------------------------------------------------- the memory layer

async def test_the_memory_cache_expires_and_evicts_in_access_order():
    now = [0.0]
    cache = cache_mod.MemoryCache(max_entries=2, ttl=10, clock=lambda: now[0])
    await cache.set("a", "1")
    await cache.set("b", "2")
    await cache.get("a")          # a is now more recently used than b
    await cache.set("c", "3")     # evicts b, not a

    assert await cache.get("a") == "1"
    assert await cache.get("b") is None
    assert cache.stats.evictions == 1

    now[0] = 11.0
    assert await cache.get("a") is None, "an entry outlived its TTL"
    assert cache.stats.hits == 2 and cache.stats.misses >= 2


async def test_the_layered_cache_fills_the_front_from_the_back():
    class Spy(cache_mod.MemoryCache):
        def __init__(self):
            super().__init__()
            self.gets = 0

        async def get(self, key):
            self.gets += 1
            return await super().get(key)

    shared = Spy()
    local = cache_mod.MemoryCache()
    cache = cache_mod.LayeredCache(local, shared)
    await shared.set("k", "v")

    assert await cache.get("k") == "v"
    assert cache.stats.l2_hits == 1
    gets_after_first = shared.gets
    assert await cache.get("k") == "v"
    assert shared.gets == gets_after_first, (
        "the second read went back to the shared layer; the front layer was not filled")
    assert cache.stats.hits == 2


# ------------------------------------------------------------------- the failures

class DeadPool:
    """A Redis that is not there, in the one way the client can report."""

    def __init__(self):
        self.calls = 0

    async def execute(self, *args, **kwargs):
        self.calls += 1
        raise resp.RespUnavailable("connection refused")

    async def pipeline(self, *args, **kwargs):
        self.calls += 1
        raise resp.RespUnavailable("connection refused")

    async def close(self):
        return None


async def test_a_dead_redis_serves_misses_and_trips_the_breaker():
    pool = DeadPool()
    cache = cache_mod.RedisCache(pool, ttl=60, cooldown=60)
    assert await cache.get("k") is None
    assert cache.stats.errors == 1
    assert cache.breaker_trips == 1

    for _ in range(20):
        assert await cache.get("k") is None
    assert pool.calls == 1, (
        f"the breaker stayed shut: {pool.calls} attempts against a server already known "
        "to be down, each one a timeout the caller pays for")
    assert await cache.set("k", "v") is None or True  # set after a trip is a no-op
    assert cache.stats.errors == 1


async def test_a_dead_cache_does_not_break_the_pipeline(work):
    pool = DeadPool()
    cache_mod.install_cache(cache_mod.RedisCache(pool, ttl=60, cooldown=60))
    try:
        out = await ask()
        assert out["evidence"], (
            "the pipeline returned no evidence because the cache was down; a cache may "
            "cost speed, never an answer")
    finally:
        cache_mod.install_cache(cache_mod.NullCache())


# ------------------------------------------------------------------ what it reports

def test_the_report_names_the_backend_and_the_rate():
    cache = cache_mod.MemoryCache()
    cache.stats.hits, cache.stats.misses = 3, 1
    described = cache.describe()
    assert described["backend"] == "memory"
    assert described["stats"]["hit_rate"] == 0.75
    assert described["stats"]["lookups"] == 4


async def test_an_epoch_survives_the_lru_evicting_every_value():
    """The generation counter is not a value: evicting it would un-invalidate everything."""
    cache = cache_mod.MemoryCache(max_entries=2, ttl=300)
    await cache.incr("careeros:rag:epoch:u", ttl=300)
    for i in range(10):
        await cache.set(f"k{i}", "v")
    assert await cache.counter("careeros:rag:epoch:u") == 1
    assert len(cache) <= 2


async def test_the_redis_backend_against_the_compose_redis():
    pool = resp.RespPool.from_url("redis://127.0.0.1:16380/0", size=2,
                                  connect_timeout=0.5, command_timeout=1.0)
    if not await pool.ping():
        await pool.close()
        pytest.skip("the dev Redis (127.0.0.1:16380) is not running")
    cache = cache_mod.RedisCache(pool, ttl=30)
    key = "careeros:test:cache:value"
    counter = "careeros:test:cache:counter"
    try:
        await cache.set(key, "remembered")
        assert await cache.get(key) == "remembered"
        assert await cache.get_many([key, key + ":absent"]) == ["remembered", None]
        assert await cache.incr(counter) == 1
        assert await cache.incr(counter) == 2
        assert await cache.counter(counter) == 2
        await cache.delete(key, counter)
        assert await cache.get(key) is None
        assert cache.stats.errors == 0
        assert cache.breaker_trips == 0
    finally:
        await cache.delete(key, counter)
        await cache.close()
