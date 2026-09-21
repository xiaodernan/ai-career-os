"""Pointwise LLM reranking with graceful fallback to RRF order."""

import json

from app.core.ai import ask_json
from app.core.config import get_settings
from app.providers.base import LLMMessage, LLMRequest


async def rerank(query: str, chunks: list[dict], top_n: int = 8, *,
                 user_id=None, run_id=None, agent="rag") -> list[dict]:
    s = get_settings()
    if s.rerank_mode == "none" or len(chunks) <= top_n:
        return chunks[:top_n]
    candidates = chunks[:25]
    numbered = "\n\n".join(
        f"[{i}] ({c.get('source_kind') or c.get('kind')}/{c.get('section_path','')}) "
        f"{c['text'][:600]}" for i, c in enumerate(candidates))
    req = LLMRequest(
        messages=[
            LLMMessage("system",
                       "You score how relevant each numbered evidence snippet is to the "
                       "user's need for answering their question. JSON only: "
                       '{"scores": {"<index>": 0.0-1.0}}. Be strict: unrelated = 0.'),
            LLMMessage("user", f"Query context: {query}\n\nSnippets:\n{numbered}"),
        ],
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
            "scores": [{"chunk_id": str(c["id"]), "rrf": round(c.get("rrf", 0), 5),
                        "rerank": c.get("rerank")} for c in ordered[:top_n]]})
    return ordered[:top_n]
