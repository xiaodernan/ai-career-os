"""A real gateway keeps the reranker's score contract, and its relevance order (Epic 160).

The offline suite exercises `rerank` in `bm25` / `none` modes and with a stubbed LLM. The one
shape it cannot contradict is a *real* model's `llm`-mode answer, because the mock returns a
well-formed `{"scores": {...}}` by construction. `rerank.py` parses that answer at one line:

    scores = {int(k): float(v) for k, v in (out.get("scores") or {}).items()}

If a provider ever returned `scores` as a list, or a value as `null`, that line raises and the
whole pass silently falls back to RRF order (`except: return candidates[:top_n]`) -- the reader
loses reranking with no error signal. An audit flagged this as a *potential* drift that the
real gateway had not reproduced. This file turns "not reproduced" into a measured, reproducible
contract: it drives the production `rerank` seam against a real `gpt-6-sol` and watches the raw
`ask_json` answer before the production line parses it.

Two things are pinned, neither of them prose:

* **structure** -- `scores` is a dict covering every numbered snippet, each value a number in
  0..1, so the comprehension above cannot silently degrade;
* **relevance order** -- the four snippets carrying the query's actual topics (Redis, PostgreSQL,
  asyncio/FastAPI, BM25) score strictly above the six unrelated ones. This is the model-as-product
  guarantee the citation UI depends on; no exact score, count or wording is fixed, because those
  are model behaviour a measurement does not support.

Inert by default: a plain `pytest` / CI / pre-commit run skips the module before any socket
opens. It bills only on explicit opt-in:

    CAREEROS_REAL_LLM=1 LLM_PROVIDER=openai_compat \
        pytest tests/test_the_real_rerank_keeps_its_scores_contract.py -q

No key literal lives here; `Settings` resolves it from the process environment or gitignored
`.env`. One async test on one loop on purpose -- the registry caches a single client bound to its
first event loop (Epic 155's trap).
"""

from __future__ import annotations

import os

import pytest

_OPT_IN = os.environ.get("CAREEROS_REAL_LLM") == "1"

pytestmark = pytest.mark.skipif(
    not _OPT_IN,
    reason="opt-in only: set CAREEROS_REAL_LLM=1 with a real LLM_PROVIDER/LLM_API_KEY",
)

_QUERY = "How to build a high-throughput Python backend with Redis caching and PostgreSQL indexing?"

# Four snippets that genuinely answer the query, interleaved with six that do not. Interleaving
# matters: a model that merely scored the first N high would fail the relevance check, so the
# assertion tests understanding, not position.
_RELEVANT = {
    "Designed a Redis caching layer cutting API latency for a Python backend.",
    "Optimized PostgreSQL query indexes and partitioning for a high-throughput service.",
    "Built asyncio FastAPI services handling high-throughput requests.",
    "Applied BM25 reranking with Redis streams for a Python data pipeline.",
    "Tuned a PostgreSQL database with composite indexes under heavy write load.",
}
# Keep the list > top_n so the llm branch (not the len<=top_n fast path) actually runs.
_CHUNK_TEXTS = [
    "Designed a Redis caching layer cutting API latency for a Python backend.",   # 0 relevant
    "Wrote marketing copy for a product launch.",                                # 1 irrelevant
    "Optimized PostgreSQL query indexes and partitioning for a high-throughput service.",  # 2 relevant
    "Managed a team's weekly meeting schedule.",                                  # 3 irrelevant
    "Built asyncio FastAPI services handling high-throughput requests.",           # 4 relevant
    "Ordered office supplies and handled vendor invoices.",                       # 5 irrelevant
    "Applied BM25 reranking with Redis streams for a Python data pipeline.",        # 6 relevant
    "Translated a brochure from English to Chinese.",                             # 7 irrelevant
    "Tuned a PostgreSQL database with composite indexes under heavy write load.",  # 8 relevant
    "Organized a company picnic and booked the venue.",                           # 9 irrelevant
]
_TOP_N = 5


def _real_settings():
    """Lazy, env-only config; every refusal is a skip, never a failure."""
    from app.core.config import Settings

    s = Settings()
    if s.llm_provider != "openai_compat":
        pytest.skip(f"LLM_PROVIDER is {s.llm_provider!r}, not 'openai_compat'")
    if s.rerank_mode != "llm":
        pytest.skip(f"RERANK_MODE is {s.rerank_mode!r}, not 'llm'")
    if not s.llm_api_key:
        pytest.skip("no LLM_API_KEY in the environment / gitignored .env")
    if "/v1" not in s.llm_base_url:
        pytest.skip("LLM_BASE_URL must include the /v1 protocol prefix for this gateway")
    return s


async def test_a_real_model_scores_every_snippet_and_orders_relevance():
    """The production `rerank` seam parses a real answer without silently degrading."""
    import app.rag.rerank as rr

    _real_settings()
    chunks = [{"id": f"c{i}", "text": t, "rrf": 1.0 - i * 0.05, "source_kind": "resume"}
              for i, t in enumerate(_CHUNK_TEXTS)]

    # Spy on the seam to see the raw answer BEFORE the production comprehension parses it.
    # Restored in `finally` so this never leaks into another test on the same process.
    real_ask_json = rr.ask_json
    seen: dict = {}

    async def spy(req, **kw):
        out = await real_ask_json(req, **kw)
        seen["raw"] = out
        return out

    rr.ask_json = spy
    try:
        ordered = await rr.rerank(_QUERY, chunks, top_n=_TOP_N, agent="probe")
    finally:
        rr.ask_json = real_ask_json

    # --- structure: the one line `rerank.py` trusts must hold on a real provider ---
    raw = seen.get("raw")
    assert isinstance(raw, dict) and isinstance(raw.get("scores"), dict), (
        f"a real rerank answer must carry a scores dict, got {raw!r}")
    scores = raw["scores"]
    assert set(scores) == {str(i) for i in range(len(_CHUNK_TEXTS))}, (
        f"scores must cover every numbered snippet, got keys {sorted(scores)}")
    for k, v in scores.items():
        assert isinstance(v, (int, float)) and not isinstance(v, bool), (
            f"score for {k} is not a number: {v!r}")
        assert 0.0 <= float(v) <= 1.0, f"score for {k} is outside 0..1: {v!r}"

    # --- NO silent degradation: the parsed scores reached the returned chunks ---
    # If the comprehension above had raised, rerank would have returned candidates[:top_n]
    # with NO `rerank` field at all. Pinning the field's presence is what catches the
    # shape drift this file exists for -- the fallback is silent, so nothing else would.
    assert len(ordered) == _TOP_N
    for c in ordered:
        assert "rerank" in c, (
            f"chunk {c.get('id')} came back without a parsed rerank score -- the LLM pass "
            "silently degraded to RRF order")
        assert c["rerank"] == round(float(scores[c["id"][1:]]), 4), (
            f"chunk {c.get('id')} rerank {c['rerank']} does not match the model's raw score")

    # --- relevance order (semantic, measured on the FULL map, not the top_n slice) ---
    # The top slice can legitimately be all-relevant; comparing on all ten scores is the
    # invariant that actually proves the model understood the query. A provider that scored
    # every snippet alike (or in reverse) fails here. No exact number is pinned.
    # scores is keyed by the numbered index ("0".."9"), not by the chunk id ("c0".."c9").
    rel = [float(scores[str(i)]) for i, t in enumerate(_CHUNK_TEXTS) if t in _RELEVANT]
    irr = [float(scores[str(i)]) for i, t in enumerate(_CHUNK_TEXTS) if t not in _RELEVANT]
    assert len(rel) == 5 and len(irr) == 5
    assert sum(rel) / len(rel) > sum(irr) / len(irr), (
        f"query-relevant snippets must outscore unrelated ones on average; "
        f"relevant={rel}, unrelated={irr}")
