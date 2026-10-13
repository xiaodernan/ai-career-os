"""The kinds-filter retry: guessing a filter that matches nothing must widen once.

The pipeline's subtlest branch, and until now no behavioral test held it. Query understanding
infers a source-`kinds` filter, and a guess matching every document empties retrieval
*silently* — a real provider does this: asked "what backend frameworks does the candidate
know?", qwen2.5:7b returned `kinds: ["project"]` for a user whose only source is a resume,
and 13 of 15 golden cases came back with no evidence at all. The mock never showed it
because its canned understanding emits no filter.

The rule under test is three-part:
  1. an *inferred* filter that starves retrieval is dropped and retrieval retried once;
  2. a *caller-supplied* filter is never dropped — that is a request, not a guess;
  3. the retry happens once, not in a loop, and is traced so an experiment can see it.

`test_rag_filter.py` holds the per-channel filter binding and `test_core_modules.py` the
compression and RRF math; this file holds the pipeline's recovery from its own starved guess.
"""

import pytest

from app.rag import pipeline
from app.rag import store


def _chunk(cid, source_kind="resume"):
    return {"id": cid, "document_id": f"doc-{cid}", "text": "led a team of 6",
            "section_path": "resume > experience", "kind": "bullet_group",
            "meta": {}, "doc_title": f"{source_kind} doc", "source_kind": source_kind}


class SwitchingStore:
    """Answers empty while its call count is still inside the starved rounds, rows afterwards.

    Models the starved-guess case exactly: the first (narrowed) round finds nothing because
    the kinds filter excludes every row, the second (unfiltered) round finds them. Starvation
    is measured in whole rounds -- each channel fans out a different number of calls per
    round (vector: one per query embedding; keyword: one per phrase; trigram: one), so a
    bare call count would starve only a prefix of the round and the retry would never fire.
    """

    def __init__(self, starved_rounds, rows, fanout):
        self.starved_rounds = starved_rounds
        self.rows = rows
        self.fanout = fanout
        self.calls = []

    async def __call__(self, user_id, arg, **kwargs):
        self.calls.append({"user_id": user_id, "arg": arg, "kwargs": kwargs})
        if len(self.calls) <= self.starved_rounds * self.fanout:
            return []
        return self.rows

    @property
    def kinds_seen(self):
        return [c["kwargs"].get("kinds") for c in self.calls]


class FakeEmbedder:
    async def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _patch(monkeypatch, understanding, starved_rounds=1, rows=None):
    rows = rows or [_chunk("p1")]
    # Calls per round: vector one per query embedding, keyword one per phrase, trigram one.
    vec_fanout = 1 + len(understanding.get("expansions") or [])
    kw_fanout = len(pipeline.keyword_phrases(understanding)) or 1
    vec = SwitchingStore(starved_rounds, rows, fanout=vec_fanout)
    kw = SwitchingStore(starved_rounds, rows, fanout=kw_fanout)
    tri = SwitchingStore(starved_rounds, rows, fanout=1)
    monkeypatch.setattr(store, "vector_search", vec)
    monkeypatch.setattr(store, "keyword_search", kw)
    monkeypatch.setattr(store, "trigram_search", tri)

    async def fake_understand(*a, **k):
        return understanding

    async def fake_rerank(query, chunks, top_n=8, **k):
        return chunks[:top_n]

    monkeypatch.setattr(pipeline, "understand", fake_understand)
    monkeypatch.setattr(pipeline, "get_embeddings", lambda *a, **k: FakeEmbedder())
    monkeypatch.setattr(pipeline, "rerank", fake_rerank)
    monkeypatch.setattr(pipeline, "compress", lambda terms, chunks: chunks)
    return vec, kw, tri


def _understanding(kinds=None):
    return {"rewritten": "backend experience", "expansions": ["messaging"],
            "intent": "personal_fact", "keywords": ["Kafka"],
            "needs_personal_evidence": True,
            "filters": {"kinds": kinds} if kinds else {},
            "original": "kafka experience"}


def _traces(monkeypatch):
    traced = []

    async def fake_trace(run_id, kind, agent, payload):
        traced.append(payload)

    async def noop(*a, **k):
        return None

    monkeypatch.setattr(pipeline.observability, "trace", fake_trace)
    monkeypatch.setattr(pipeline.observability, "create_run", noop)
    return traced


@pytest.mark.asyncio
async def test_an_inferred_kinds_that_starves_retrieval_is_dropped_once(monkeypatch):
    """The qwen2.5 failure, end to end: the guessed `kinds: ["project"]` excludes a
    resume-only corpus, the narrowed round empties, the unfiltered round recovers."""
    vec, kw, tri = _patch(monkeypatch, _understanding(kinds=["project"]))
    out = await pipeline.retrieve("kafka experience", user_id="u", top_k=5)
    assert [str(e["chunk_id"]) for e in out["evidence"]] == ["p1"], (
        "a starved guess must not be reported as an honest empty")
    # Every channel: first round bound the guess, second round bound nothing.
    # Every channel: the first round bound the guess, the retry bound nothing. Vector runs
    # once per query (rewritten + 1 expansion), keyword once per phrase, trigram once — so
    # the per-channel call count is (rounds x its own fan-out).
    assert vec.kinds_seen == [["project"], ["project"], None, None]
    assert kw.kinds_seen == [["project"], ["project"], None, None]
    assert tri.kinds_seen == [["project"], None]


@pytest.mark.asyncio
async def test_a_caller_supplied_kinds_is_never_widened(monkeypatch):
    """A caller's `kinds` is a request, not a guess: `?kinds=project&` asking for project
    chunks in a resume-only corpus must answer EMPTY, not somebody's resume rows. Widening
    it would hand the caller evidence they explicitly scoped out."""
    vec, kw, tri = _patch(monkeypatch, _understanding(kinds=["project"]))
    out = await pipeline.retrieve("kafka experience", user_id="u", top_k=5,
                                  kinds=["project"])
    assert out["evidence"] == []
    for rec in (vec, kw, tri):
        assert rec.calls, "no channel ran at all"
        assert rec.kinds_seen and all(k == ["project"] for k in rec.kinds_seen), (
            f"a caller-supplied filter was widened: {rec.kinds_seen}")


@pytest.mark.asyncio
async def test_an_understanding_with_no_inferred_filter_runs_once(monkeypatch):
    """The happy path the mock always exercised: no filter, no starvation, one round.
    Without this, a retry-on-every-empty would be indistinguishable from recovery."""
    vec, kw, tri = _patch(monkeypatch, _understanding(kinds=None), starved_rounds=0)
    out = await pipeline.retrieve("kafka experience", user_id="u", top_k=5)
    assert [str(e["chunk_id"]) for e in out["evidence"]] == ["p1"]
    assert len(vec.calls) == 2 and len(kw.calls) == 2 and len(tri.calls) == 1, (
        f"a second round ran uninvited: vec={len(vec.calls)} kw={len(kw.calls)} "
        f"tri={len(tri.calls)}")
    assert all(k in ([], None) for k in vec.kinds_seen), (
        f"a filter appeared without an inference: {vec.kinds_seen}")


@pytest.mark.asyncio
async def test_the_retry_happens_once_and_reports_empty_when_it_recovers_nothing(monkeypatch):
    """Bounded, not looping: if even the unfiltered retrieve is empty the pipeline answers
    empty once and returns. An unbounded loop would fan out forever against an empty
    corpus — every request an unbounded number of queries."""
    vec, kw, tri = _patch(monkeypatch, _understanding(kinds=["project"]),
                         starved_rounds=10 ** 6)
    out = await pipeline.retrieve("kafka experience", user_id="u", top_k=5)
    assert out["evidence"] == []
    # One narrowed attempt per channel phrase + exactly one retry, not a third round.
    # One narrowed attempt per channel phrase + exactly one retry, not a third round.
    # (vector/keyword fan out 2 queries each per round, trigram 1.)
    assert len(vec.calls) == 4 and len(kw.calls) == 4 and len(tri.calls) == 2, (
        f"expected exactly two rounds: vec={len(vec.calls)} kw={len(kw.calls)} "
        f"tri={len(tri.calls)}")


@pytest.mark.asyncio
async def test_the_recovery_is_traced_with_the_guess_and_what_it_recovered(monkeypatch):
    """The trace is the only way an experiment can tell 13-of-15-empty from an honest
    empty corpus. Retry without the trace would make the recovery invisible."""
    traced = _traces(monkeypatch)
    _patch(monkeypatch, _understanding(kinds=["project"]))
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5, run_id="r1")
    dropped = [t for t in traced if t.get("stage") == "kinds_filter_dropped"]
    assert dropped and dropped[0]["guessed"] == ["project"]
    assert dropped[0]["recovered"] == 1


@pytest.mark.asyncio
async def test_the_hybrid_trace_records_the_widened_result_after_recovery(monkeypatch):
    """The `hybrid` stage trace is what the report reads for `merged`. After a recovery it
    must name the widened count (3 rows), not the starved zero."""
    traced = _traces(monkeypatch)
    _patch(monkeypatch, _understanding(kinds=["project"]), rows=[_chunk("p1"), _chunk("p2"),
                                                                  _chunk("p3")])
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5, run_id="r2")
    hybrid = [t for t in traced if t.get("stage") == "hybrid"]
    assert hybrid and hybrid[-1]["merged"] == 3


@pytest.mark.asyncio
async def test_an_inferred_filter_that_finds_rows_runs_once_and_keeps_them(monkeypatch):
    """The inferred filter is not a lie: when it matches rows they are the answer and no
    widening happens — a retry here would discard the narrowed result for the broad one."""
    vec, kw, tri = _patch(monkeypatch, _understanding(kinds=["resume"]), starved_rounds=0)
    out = await pipeline.retrieve("kafka experience", user_id="u", top_k=5)
    assert [str(e["chunk_id"]) for e in out["evidence"]] == ["p1"]
    assert vec.kinds_seen == [["resume"], ["resume"]]
    assert kw.kinds_seen == [["resume"], ["resume"]]
    assert tri.kinds_seen == [["resume"]]
