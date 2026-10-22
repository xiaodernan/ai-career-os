"""The retrieval-strategy knob must actually select channels (PRD §32).

The reranker was the only switch the RAG harness had, so "does the hybrid beat
keyword alone?" could not be answered by a run. `retrieve(strategy=...)` now names
which channels feed the fusion; these tests hold each name to the channels it
promises, because a knob that silently keeps the default on every code path makes
every experiment report the same experiment.
"""

import asyncio

import pytest

from app.rag import pipeline
from app.rag import store


class Recorder:
    def __init__(self, rows, name):
        self.rows = rows
        self.name = name
        self.calls = 0

    async def __call__(self, *a, **k):
        self.calls += 1
        return self.rows


class FakeEmbedder:
    async def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _chunk(cid, source_kind="resume"):
    return {"id": cid, "document_id": f"doc-{cid}", "text": "led a team of 6",
            "section_path": "resume > experience", "kind": "bullet_group",
            "meta": {}, "doc_title": f"{source_kind} doc", "source_kind": source_kind}


def _patch(monkeypatch, understanding=None):
    vec = Recorder([_chunk("v1")], "vector")
    kw = Recorder([_chunk("k1")], "keyword")
    tri = Recorder([_chunk("t1")], "trigram")
    monkeypatch.setattr(store, "vector_search", vec)
    monkeypatch.setattr(store, "keyword_search", kw)
    monkeypatch.setattr(store, "trigram_search", tri)

    async def fake_understand(*a, **k):
        return understanding or {"rewritten": "backend experience",
                                 "expansions": ["messaging"],
                                 "intent": "personal_fact", "keywords": ["Kafka"],
                                 "needs_personal_evidence": True, "filters": {},
                                 "original": "kafka experience"}

    async def fake_rerank(query, chunks, top_n=8, **k):
        return chunks[:top_n]

    monkeypatch.setattr(pipeline, "understand", fake_understand)
    monkeypatch.setattr(pipeline, "get_embeddings", lambda *a, **k: FakeEmbedder())
    monkeypatch.setattr(pipeline, "rerank", fake_rerank)
    monkeypatch.setattr(pipeline, "compress", lambda terms, chunks: chunks)
    return vec, kw, tri


@pytest.mark.asyncio
async def test_the_default_keeps_all_three_channels(monkeypatch):
    vec, kw, tri = _patch(monkeypatch)
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5)
    assert vec.calls >= 1 and kw.calls >= 1 and tri.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy,expect", [
    ("vector", {"vec"}),
    ("keyword", {"kw"}),
    ("trigram", {"tri"}),
    ("vector,keyword", {"vec", "kw"}),
    ("keyword,trigram", {"kw", "tri"}),
])
async def test_a_named_strategy_keeps_only_its_channels(monkeypatch, strategy, expect):
    vec, kw, tri = _patch(monkeypatch)
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5, strategy=strategy)
    fired = set()
    if vec.calls:
        fired.add("vec")
    if kw.calls:
        fired.add("kw")
    if tri.calls:
        fired.add("tri")
    assert fired == expect, (
        f"strategy='{strategy}' ran {fired or '{}'} — a knob that keeps the default on "
        "every path makes every experiment report the same experiment")


@pytest.mark.asyncio
async def test_an_unknown_strategy_falls_back_to_hybrid_rather_than_silently_nothing(monkeypatch):
    vec, kw, tri = _patch(monkeypatch)
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5, strategy="bits")
    assert vec.calls >= 1 and kw.calls >= 1 and tri.calls == 1


@pytest.mark.asyncio
async def test_an_empty_strategy_name_is_not_a_zero_channel_run(monkeypatch):
    vec, kw, tri = _patch(monkeypatch)
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5, strategy="")
    assert vec.calls >= 1 and kw.calls >= 1 and tri.calls == 1


@pytest.mark.asyncio
async def test_spaces_around_channel_names_are_tolerated(monkeypatch):
    vec, kw, tri = _patch(monkeypatch)
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5,
                            strategy=" vector , keyword ")
    assert vec.calls >= 1 and kw.calls >= 1 and tri.calls == 0


@pytest.mark.asyncio
async def test_the_trace_records_the_channels_not_a_count(monkeypatch):
    """The old trace reported `"channels": len(lists)` — a number that said nothing
    about *which* channels ran, which is the one thing an experiment needs to read."""
    traced = []
    _patch(monkeypatch)

    async def fake_trace(run_id, kind, agent, payload):
        traced.append(payload)

    async def fake_noop(*a, **k):
        return None

    monkeypatch.setattr(pipeline.observability, "trace", fake_trace)
    monkeypatch.setattr(pipeline.observability, "create_run", fake_noop)
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5,
                            strategy="keyword", run_id="r1")
    hybrid = [t for t in traced if t.get("stage") == "hybrid"]
    assert hybrid, "no hybrid trace emitted"
    assert hybrid[0]["channels"] == ["keyword"], (
        f"trace must name the channels: {hybrid[0].get('channels')}")


@pytest.mark.asyncio
async def test_max_expansions_caps_the_multi_query_fanout(monkeypatch):
    seen = []

    class CountingEmbedder:
        async def embed(self, texts):
            seen.append(len(texts))
            return [[0.1] * 3 for _ in texts]

    _patch(monkeypatch, {"rewritten": "backend experience",
                         "expansions": ["messaging", "queues", "streaming", "shard"],
                         "intent": "personal_fact", "keywords": ["Kafka"],
                         "needs_personal_evidence": True, "filters": {},
                         "original": "kafka experience"})
    monkeypatch.setattr(pipeline, "get_embeddings", lambda *a, **k: CountingEmbedder())

    # default (no cap): rewritten + 4 expansions = 5 queries
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5)
    assert sum(seen) == 5

    seen.clear()
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5, max_expansions=1)
    assert sum(seen) == 2, "max_expansions did not cap the multi-query fan-out"


# ---------------- hostile input (compress over retrieved rows) ----------------

def test_compress_survives_none_and_junk_rows():
    from app.rag.compress import compress
    assert compress(None, None) == []
    # a non-dict row and a present-null text are skipped, the real row survives
    chunks = [None, "junk", {"text": None, "id": "c1"},
              {"text": "Built a Go service. Scaled it to 10k QPS.", "id": "c2"}]
    out = compress(["Go"], chunks)
    assert [c["id"] for c in out] == ["c2"]
    assert out[0]["text_original"] == "Built a Go service. Scaled it to 10k QPS."
    assert "Go" in out[0]["text"]
    # non-str query terms are dropped rather than raising in the join
    assert compress([None, 7, "Go"], chunks)[0]["id"] == "c2"


def test_rerank_survives_none_and_junk_rows(monkeypatch):
    from app.rag import rerank as R
    # a None list and non-dict rows must not crash the numbered-prompt build
    out = asyncio.run(R.rerank("q", None))
    assert out == []
    chunks = [None, "junk", {"id": "c1", "text": None},
              {"id": "c2", "text": "Built a Go service", "section_path": "exp"}]
    got = asyncio.run(R.rerank("q", chunks, top_n=2))
    assert [c["id"] for c in got] == ["c1", "c2"]


def test_understand_survives_none_context(monkeypatch):
    from app.rag import rewrite as W
    async def fake_ask_json(req, **kw):
        raise AssertionError("must not be reached -- context handling is upstream")

    monkeypatch.setattr(W, "ask_json", fake_ask_json)
    # a None context summary used to raise TypeError on the slice
    out = asyncio.run(W.understand(None, None))
    assert out["intent"] == "other"
    assert out["rewritten"] == ""        # a None query degrades, not crashes


def test_keyword_phrases_and_to_evidence_survive_hostile_input():
    assert pipeline.keyword_phrases(None) == []
    assert pipeline.keyword_phrases({}) == []
    assert pipeline.keyword_phrases({"rewritten": None, "keywords": None}) == []
    # non-str rows in keywords are dropped, not joined into a crash
    assert pipeline.keyword_phrases({"rewritten": "go jobs", "keywords": [None, 7, "kafka"]}) == [
        "go jobs", "kafka"]

    assert pipeline.to_evidence(None) == []
    rows = pipeline.to_evidence([None, "junk", {"id": "c1", "document_id": "d1",
                                                "text": None, "rerank": "high"},
                                 {"id": "c2", "document_id": "d2", "text": "quote",
                                  "rerank": 0.5, "rrf": 0.25}])
    assert [r["chunk_id"] for r in rows] == ["c1", "c2"]
    assert rows[0]["quote"] == "" and rows[0]["score"] == 0.0   # junk signal -> 0
    assert rows[1]["score"] == 0.5                              # best of rerank/rrf
