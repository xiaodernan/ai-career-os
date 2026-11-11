"""`RERANK_MODE=bm25`: a lexical rerank that costs no model call.

The LLM pass is a model call (money + latency) on every retrieval that has more
than `top_n` candidates. BM25 answers the same "order these snippets by relevance"
question on the CPU in microseconds. These tests pin the contract that makes it a
drop-in: the same `rerank` field in 0..1 (so `to_evidence`'s `max(rerank, rrf)`
cannot be poisoned by an out-of-scale score), stable ties, no-LLM-call, and a
Chinese path that actually tokenises Chinese instead of scoring everything zero.
"""

import pytest

from app.rag import rerank as rerank_mod
from app.rag.rerank import _rerank_tokens, _bm25_order, rerank
from app.rag.pipeline import to_evidence

from types import SimpleNamespace


def _patch_mode(monkeypatch, mode):
    monkeypatch.setattr(rerank_mod, "get_settings",
                        lambda: SimpleNamespace(rerank_mode=mode))


def _chunks(texts):
    """RRF order = c0, c1, ... (higher rrf first); text is what BM25 scores."""
    return [{"id": f"c{i}", "text": text, "source_kind": "resume",
             "section_path": "S", "rrf": 1.0 / (i + 1)}
            for i, text in enumerate(texts)]


async def _refuse_llm(*a, **k):
    raise AssertionError("bm25 mode must never touch the model")


# --------------------------------------------------------------- ordering

async def test_bm25_puts_the_lexically_relevant_chunk_first(monkeypatch):
    _patch_mode(monkeypatch, "bm25")
    monkeypatch.setattr(rerank_mod, "ask_json", _refuse_llm)
    chunks = _chunks(["unrelated weather today", "python async io internals",
                      "a note about cooking", "python garbage collection"])
    out = await rerank("python memory", chunks, top_n=2)
    # both python chunks outrank the two non-python ones
    assert {c["id"] for c in out} == {"c1", "c3"}
    assert out[0]["id"] in {"c1", "c3"}


async def test_bm25_injects_normalised_scores_in_zero_to_one(monkeypatch):
    _patch_mode(monkeypatch, "bm25")
    monkeypatch.setattr(rerank_mod, "ask_json", _refuse_llm)
    chunks = _chunks(["python python python", "python", "cooking recipe", "java tools"])
    out = await rerank("python", chunks, top_n=3)
    scores = [c["rerank"] for c in out]
    assert all(isinstance(s, float) and 0.0 <= s <= 1.0 for s in scores)
    assert max(scores) == 1.0, "the top hit must normalise to 1.0"
    assert scores == sorted(scores, reverse=True), "output must be score-descending"


async def test_bm25_scores_fit_the_evidence_score_scale(monkeypatch):
    """The whole reason for normalising: to_evidence takes max(rerank, rrf)."""
    _patch_mode(monkeypatch, "bm25")
    monkeypatch.setattr(rerank_mod, "ask_json", _refuse_llm)
    chunks = _chunks(["kubernetes kubernetes kubernetes", "k8s", "unrelated", "docker swarm"])
    out = await rerank("kubernetes", chunks, top_n=3)
    evidence = to_evidence(out)
    assert evidence, "evidence must still be produced"
    assert all(0.0 <= e["score"] <= 1.0 for e in evidence), (
        "a BM25 score above 1.0 would blow past the rrf scale and fabricate confidence")


async def test_bm25_keeps_rrf_order_when_nothing_matches(monkeypatch):
    _patch_mode(monkeypatch, "bm25")
    monkeypatch.setattr(rerank_mod, "ask_json", _refuse_llm)
    chunks = _chunks(["alpha", "beta", "gamma", "delta"])
    out = await rerank("zzzqqq", chunks, top_n=3)
    assert [c["id"] for c in out] == ["c0", "c1", "c2"]
    assert all(c["rerank"] == 0.0 for c in out)


async def test_bm25_ties_keep_the_fused_order(monkeypatch):
    _patch_mode(monkeypatch, "bm25")
    monkeypatch.setattr(rerank_mod, "ask_json", _refuse_llm)
    # Four equal docs: identical scores, first three (fused order) survive.
    chunks = _chunks(["python a", "python b", "python c", "python d"])
    out = await rerank("python", chunks, top_n=3)
    assert [c["id"] for c in out] == ["c0", "c1", "c2"]


async def test_bm25_within_top_n_returns_untouched_without_scoring(monkeypatch):
    """The <= top_n early return is shared by all modes and injects nothing."""
    _patch_mode(monkeypatch, "bm25")
    monkeypatch.setattr(rerank_mod, "ask_json", _refuse_llm)
    chunks = _chunks(["python", "cooking"])
    out = await rerank("python", chunks, top_n=8)
    assert [c["id"] for c in out] == ["c0", "c1"]
    assert all("rerank" not in c for c in out)


# --------------------------------------------------------------- chinese

def test_the_tokeniser_emits_cjk_bigrams_and_latin_words():
    assert _rerank_tokens("Python 机器学习") == [
        "python", "机器", "器学", "学习"]
    assert _rerank_tokens(" abort") == ["abort"]
    assert _rerank_tokens("学") == ["学"]  # single char still indexed


async def test_chinese_query_reorders_chinese_chunks(monkeypatch):
    """A `[a-z0-9]+`-only tokeniser would score everything zero here."""
    _patch_mode(monkeypatch, "bm25")
    monkeypatch.setattr(rerank_mod, "ask_json", _refuse_llm)
    chunks = _chunks(["天气预报", "机器学习与深度学习", "菜谱与烹饪", "机器学习框架"])
    out = await rerank("机器学习", chunks, top_n=2)
    assert {c["id"] for c in out} == {"c1", "c3"}


# --------------------------------------------------------------- internals

def test_bm25_order_is_pure_cpu_and_candidate_bounded():
    """_bm25_order scores the list it is handed and returns it ordered."""
    chunks = _chunks(["redis cache", "redis", "postgres index"])
    ordered, scores = _bm25_order("redis", chunks)
    assert set(scores) == {0, 1, 2}
    assert len(ordered) == 3
    assert all("rerank" in c for c in ordered)


async def test_unknown_mode_falls_through_to_the_llm_path(monkeypatch):
    """An unrecognised mode must not silently become 'no rerank'."""
    async def scored(req, **k):
        return {"scores": {"0": 0.1, "1": 0.9}}
    _patch_mode(monkeypatch, "mystery")
    monkeypatch.setattr(rerank_mod, "ask_json", scored)
    chunks = _chunks(["a", "b", "c"])
    out = await rerank("q", chunks, top_n=2)
    assert out[0]["id"] == "c1"  # LLM scored index 1 highest
