"""Agent memory (PRD §17).

Short-term: conversation history assembled by the orchestrator.
Long-term: distilled facts in user_memories, retrieved into every run's system
context and extracted after meaningful turns.
"""

import logging

from app.core.ai import ask_json, wrap_untrusted
from app.db import domain, observability
from app.providers.base import LLMMessage, LLMRequest

log = logging.getLogger("agents.memory")

MEMORY_KINDS = {"profile", "skill", "preference", "interview", "goal", "fact"}

_KIND_LABEL = {
    "profile": "Profile", "skill": "Skills", "preference": "Preferences",
    "interview": "Interview history", "goal": "Goals", "fact": "Facts",
}


async def build_memory_context(user_id: str) -> str:
    memories = await domain.get_memories(user_id, limit=40)
    if not memories:
        return ""
    by_kind: dict[str, list[dict]] = {}
    for m in memories:
        by_kind.setdefault(m["kind"], []).append(m)
    lines = ["## Long-term memory about this user"]
    for kind, items in by_kind.items():
        label = _KIND_LABEL.get(kind, kind)
        for m in items:
            key = f"{m['key']}: " if m.get("key") else ""
            lines.append(f"- [{label}] {key}{m['content']}")
    return "\n".join(lines)


EXTRACT_SYSTEM = """You maintain long-term memory for a career assistant.
From the conversation turn below, extract ONLY durable, user-level facts worth
remembering later (skills, preferences, goals, facts about experience, interview
outcomes). Ignore small talk and one-off phrasing. Never store secrets or
credentials. Return JSON: {"memories": [{"kind": "profile|skill|preference|
interview|goal|fact", "key": "short-slug", "content": "one sentence",
"importance": 0.0-1.0}]}. Return {"memories": []} if nothing qualifies."""


async def extract_and_store(user_id: str, user_text: str, answer: str,
                            run_id: str | None = None) -> int:
    """Distill long-term memories from a completed turn; best-effort, never raises."""
    prompt = (f"User message:\n{wrap_untrusted('USER_MESSAGE', user_text[:3000])}\n\n"
              f"Assistant reply:\n{answer[:2000]}")
    try:
        data = await ask_json(
            LLMRequest(messages=[LLMMessage("system", EXTRACT_SYSTEM),
                                 LLMMessage("user", prompt)],
                       temperature=0.0, max_tokens=800),
            user_id=user_id, run_id=run_id, agent="career", kind="memory_extract")
    except Exception:
        log.warning("memory extraction failed", exc_info=True)
        return 0
    saved = 0
    for m in (data.get("memories") or [])[:4]:
        kind = m.get("kind")
        content = (m.get("content") or "").strip()
        if kind not in MEMORY_KINDS or len(content) < 8:
            continue
        key = (m.get("key") or "").strip() or content[:40]
        try:
            importance = max(0.0, min(1.0, float(m.get("importance", 0.6))))
        except (TypeError, ValueError):
            importance = 0.6
        await domain.upsert_memory(user_id, kind, key, content, source="chat",
                                   importance=importance)
        saved += 1
    if saved:
        await observability.trace(run_id, "step_start", "career",
                                  {"stage": "memory_extract", "saved": saved})
    return saved
