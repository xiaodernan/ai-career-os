"""Pointwise reranking: an LLM relevance pass, in-process BM25, or RRF order.

Three modes, selected by `RERANK_MODE`:

* ``llm`` (default) — the original pointwise LLM pass, graceful fallback to RRF.
* ``bm25`` — Okapi BM25 over the fused candidate texts. No model call, no network,
  deterministic, microseconds. The score is min-max normalised to 0..1 (top hit
  = 1.0) so `pipeline.to_evidence` can take `max(rerank, rrf)` without a scale
  mismatch. Chinese is handled with character bigrams (see `_rerank_tokens`), the
  standard trick when no word segmenter is available; a query sharing no token
  with any candidate scores all-zero and keeps the fused order, exactly like a
  stubbed LLM would.
* ``none`` — skip the pass entirely, keep the fused RRF order.

The two computed modes both inject the same ``rerank`` field, so the citation and
observability paths do not branch on the mode. Together with the trace ``mode``
key, an operator can tell from the run log which ranker decided the order.
"""

import re

from app.algorithms import Bm25
from app.core.ai import ask_json, stable_messages
from app.core.config import get_settings
from app.providers.base import LLMMessage, LLMRequest

_LATIN = re.compile(r"[a-z0-9]+")
# CJK unified ideographs + kana + hangul: scripts with no whitespace word boundary.
_CJK_RUN = re.compile(
    r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]+")


def _rerank_tokens(text: str) -> list[str]:
    """Lexical tokens for BM25 over mixed Chinese/English evidence.

    Latin runs become lowercased words; CJK runs become overlapping character
    bigrams (plus the single char when the run is length one). Bigrams let a
    Chinese query like "机器学习" share signal with a document saying "机器学习"
    or "机器学习框架" without shipping a segmenter, while rare bigrams get a
    higher IDF just as rare words do. Cost is linear in text length.
    """
    text = (text or "").lower()
    tokens = _LATIN.findall(text)
    for run in _CJK_RUN.findall(text):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    return tokens


def _bm25_order(query: str, candidates: list[dict]) -> tuple[list[dict], dict[int, float]]:
    """Score `candidates` by lexical relevance to `query`, stable on ties.

    Pure CPU, O(total text length). BM25 rewards a term's rarity across the
    candidate set and damps raw term frequency by document length, so a long
    resume chunk cannot win by being long. Scores are min-max normalised to
    (0, 1]; an all-zero result (no query token anywhere) keeps the input/RRF
    order. The candidate list is scored in place (each chunk gains `rerank`).
    """
    doc_tokens = [_rerank_tokens(str(c.get("text") or "")) for c in candidates]
    bm25 = Bm25().fit(doc_tokens)
    raw = bm25.scores(_rerank_tokens(query))
    peak = max(raw, default=0.0)
    scores = {i: (round(raw[i] / peak, 4) if peak > 0 else 0.0)
              for i in range(len(candidates))}
    for i, c in enumerate(candidates):
        c["rerank"] = scores[i]
    # Python's sort is stable: equal scores keep the fused (RRF) order.
    ordered = sorted(candidates, key=lambda c: c.get("rerank", -1), reverse=True)
    return ordered, scores


async def rerank(query: str, chunks: list[dict], top_n: int = 8, *,
                 user_id=None, run_id=None, agent="rag") -> list[dict]:
    s = get_settings()
    rows = [c for c in (chunks or []) if isinstance(c, dict)]
    if s.rerank_mode == "none" or len(rows) <= top_n:
        return rows[:top_n]

    if s.rerank_mode == "bm25":
        ordered, _ = _bm25_order(query, rows[:25])
        if run_id:
            from app.db import observability
            await observability.trace(run_id, "rerank", agent, {
                "mode": "bm25",
                "scores": [{"chunk_id": str(c.get("id")),
                            "rrf": round(c.get("rrf") or 0, 5),
                            "rerank": c.get("rerank")} for c in ordered[:top_n]]})
        return ordered[:top_n]

    candidates = rows[:25]
    numbered = "\n\n".join(
        f"[{i}] ({c.get('source_kind') or c.get('kind')}/{c.get('section_path','')}) "
        f"{str(c.get('text') or '')[:600]}" for i, c in enumerate(candidates))
    req = LLMRequest(
        messages=stable_messages(
            "You score how relevant each numbered evidence snippet is to the "
            "user's need for answering their question. JSON only: "
            '{"scores": {"<index>": 0.0-1.0}}. Be strict: unrelated = 0.',
            LLMMessage("user", f"Query context: {query}\n\nSnippets:\n{numbered}"),
        ),
        temperature=0.0, max_tokens=900)
    try:
        out = await ask_json(req, user_id=user_id, run_id=run_id, agent=agent, kind="rerank")
        scores = {int(k): float(v) for k, v in (out.get("scores") or {}).items()}
    except Exception:
        return candidates[:top_n]
    for i, c in enumerate(candidates):
        c["rerank"] = round(scores.get(i, 0.0), 4)
    # keep candidates without an explicit score at their RRF tail
    ordered = sorted(candidates, key=lambda c: c.get("rerank", -1), reverse=True)
    from app.db import observability

    if run_id:
        await observability.trace(run_id, "rerank", agent, {
            "mode": "llm",
            "scores": [{"chunk_id": str(c.get("id")), "rrf": round(c.get("rrf") or 0, 5),
                        "rerank": c.get("rerank")} for c in ordered[:top_n]]})
    return ordered[:top_n]
