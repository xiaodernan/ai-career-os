"""A failing retrieval channel must not fail the retrieval.

`retrieve` fans out over three Postgres-dependent channels (vector / keyword /
trigram) plus an embedding provider. Before this, any one of them raising -- a
missing `pgvector`/`pg_trgm` extension, a transient connection error, an embedding
provider that is down -- aborted the whole call, so the healthy channels' results
were lost with it. Each channel is now isolated: it contributes nothing, the
failure is logged and traced, and the lexical channels still answer.

These tests hold that contract, because "the hybrid is more robust" is a claim
about the failure path, and the happy path proves nothing about it.
"""

import pytest

from app.rag import pipeline
from app.rag import store


class Ok:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    async def __call__(self, *a, **k):
        self.calls += 1
        return self.rows


class Boom:
    def __init__(self, exc=None):
        self.exc = exc or RuntimeError("pgvector is not installed")
        self.calls = 0

    async def __call__(self, *a, **k):
        self.calls += 1
        raise self.exc


class FakeEmbedder:
    def __init__(self, exc=None):
        self.exc = exc
        self.calls = 0

    async def embed(self, texts):
        self.calls += 1
        if self.exc:
            raise self.exc
        return [[0.1, 0.2, 0.3] for _ in texts]


def _chunk(cid):
    return {"id": cid, "document_id": f"doc-{cid}", "text": "led a team of 6",
            "section_path": "resume > experience", "kind": "bullet_group",
            "meta": {}, "doc_title": "resume doc", "source_kind": "resume"}


def _patch(monkeypatch, *, vector=None, keyword=None, trigram=None, embedder=None,
           understanding=None):
    vec = vector if vector is not None else Ok([_chunk("v1")])
    kw = keyword if keyword is not None else Ok([_chunk("k1")])
    tri = trigram if trigram is not None else Ok([_chunk("t1")])
    monkeypatch.setattr(store, "vector_search", vec)
    monkeypatch.setattr(store, "keyword_search", kw)
    monkeypatch.setattr(store, "trigram_search", tri)

    async def fake_understand(*a, **k):
        return understanding or {"rewritten": "backend experience",
                                 "expansions": ["messaging"], "intent": "personal_fact",
                                 "keywords": ["Kafka"], "needs_personal_evidence": True,
                                 "filters": {}, "original": "kafka experience"}

    async def fake_rerank(query, chunks, top_n=8, **k):
        return chunks[:top_n]

    traces: list[tuple[str, dict]] = []

    async def fake_trace(run_id, kind, agent, payload):
        traces.append((kind, payload))

    monkeypatch.setattr(pipeline, "understand", fake_understand)
    monkeypatch.setattr(pipeline, "get_embeddings",
                        lambda *a, **k: (embedder if embedder is not None else FakeEmbedder()))
    monkeypatch.setattr(pipeline, "rerank", fake_rerank)
    monkeypatch.setattr(pipeline, "compress", lambda terms, chunks: chunks)
    monkeypatch.setattr(pipeline.observability, "trace", fake_trace)
    return vec, kw, tri, traces


@pytest.mark.asyncio
async def test_a_dead_vector_channel_does_not_kill_keyword_and_trigram(monkeypatch):
    vec, kw, tri, _ = _patch(monkeypatch, vector=Boom())
    out = await pipeline.retrieve("kafka experience", user_id="u", top_k=5, run_id="r1")
    ids = {e["chunk_id"] for e in out["evidence"]}
    assert ids == {"k1", "t1"}  # the two healthy channels still answered
    assert vec.calls >= 1       # it was attempted, not silently skipped


@pytest.mark.asyncio
async def test_a_dead_keyword_channel_does_not_kill_the_other_two(monkeypatch):
    _vec, kw, tri, _ = _patch(monkeypatch, keyword=Boom(ConnectionError("db reset")))
    out = await pipeline.retrieve("kafka experience", user_id="u", top_k=5, run_id="r1")
    ids = {e["chunk_id"] for e in out["evidence"]}
    assert ids == {"v1", "t1"}
    assert kw.calls >= 1


@pytest.mark.asyncio
async def test_a_dead_trigram_channel_does_not_kill_the_other_two(monkeypatch):
    _vec, kw, tri, _ = _patch(monkeypatch, trigram=Boom())
    out = await pipeline.retrieve("kafka experience", user_id="u", top_k=5, run_id="r1")
    ids = {e["chunk_id"] for e in out["evidence"]}
    assert ids == {"v1", "k1"}
    assert tri.calls >= 1


@pytest.mark.asyncio
async def test_all_channels_dead_returns_empty_not_an_exception(monkeypatch):
    _v, _k, _t, _ = _patch(monkeypatch, vector=Boom(), keyword=Boom(), trigram=Boom())
    out = await pipeline.retrieve("kafka experience", user_id="u", top_k=5, run_id="r1")
    assert out["evidence"] == []


@pytest.mark.asyncio
async def test_a_dead_embedder_falls_back_to_lexical_channels(monkeypatch):
    _v, kw, tri, _ = _patch(monkeypatch, embedder=FakeEmbedder(
        exc=ConnectionError("ollama is down")))
    out = await pipeline.retrieve("kafka experience", user_id="u", top_k=5, run_id="r1")
    ids = {e["chunk_id"] for e in out["evidence"]}
    assert ids == {"k1", "t1"}  # semantic is gone; lexical still answers


@pytest.mark.asyncio
async def test_a_channel_failure_is_traced_not_silently_swallowed(monkeypatch):
    _v, _k, _t, traces = _patch(monkeypatch, vector=Boom())
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5, run_id="r1")
    errors = [p for kind, p in traces
              if kind == "retrieval" and p.get("stage") == "channel_error"]
    # One trace per attempted query (the rewritten query plus each expansion), each
    # naming the channel that failed -- a fallback a run can be told apart from a
    # genuine "nothing matched".
    assert errors
    assert {e["channel"] for e in errors} == {"vector"}
    assert all("pgvector" in e["error"] for e in errors)


@pytest.mark.asyncio
async def test_an_embedder_failure_is_traced(monkeypatch):
    _v, _k, _t, traces = _patch(monkeypatch, embedder=FakeEmbedder(exc=OSError("refused")))
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5, run_id="r1")
    stages = [p.get("stage") for kind, p in traces if kind == "retrieval"]
    assert "embedding_error" in stages


@pytest.mark.asyncio
async def test_a_channel_failure_without_a_run_id_still_answers(monkeypatch):
    # No run_id means nowhere to trace; the degradation must still work, not raise.
    _v, kw, tri, _ = _patch(monkeypatch, vector=Boom())
    out = await pipeline.retrieve("kafka experience", user_id="u", top_k=5)
    ids = {e["chunk_id"] for e in out["evidence"]}
    assert ids == {"k1", "t1"}
