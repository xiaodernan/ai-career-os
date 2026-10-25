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
    """The user's durable memory as prompt text, or "" when it cannot be built.

    Memory is a prompt enhancement, not the answer: the copilot can still answer a
    turn without it. A failed read used to abort the turn *before any tool ran*, and a
    row missing `kind`/`content` raised KeyError on the way to the prompt -- both made
    a cosmetic input the reason the user got nothing. The write side
    (`extract_and_store`) is documented as best-effort; this makes the read side match.
    """
    try:
        memories = await domain.get_memories(user_id, limit=40)
    except Exception as e:
        log.warning("memory context unavailable, continuing without it: %s", e)
        return ""
    if not memories:
        return ""
    by_kind: dict[str, list[str]] = {}
    for m in memories:
        if not isinstance(m, dict):
            continue
        content = m.get("content")
        if not isinstance(content, str) or not content.strip():
            continue  # a row with no text has nothing to put in the prompt
        kind = str(m.get("kind") or "fact")
        key = m.get("key")
        by_kind.setdefault(kind, []).append(f"{key}: {content}" if key else content)
    lines = ["## Long-term memory about this user"]
    for kind, items in by_kind.items():
        label = _KIND_LABEL.get(kind, kind)
        for line in items:
            lines.append(f"- [{label}] {line}")
    return "\n".join(lines) if len(lines) > 1 else ""


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


async def record_interview_outcome(user_id: str, session_id: str, evaluation: dict,
                                   run_id: str | None = None) -> int:
    """Persist an interview report as durable `interview` memory.

    An interview is the most expensive thing the product does for the user, and its
    verdict is the one finding that should outlive the session: `interview` was a
    declared kind in §17 from the start, yet nothing but chat extraction could ever
    produce one, so a completed mock interview left no durable trace for the next run
    to build on. Only the report's own numbers are stored -- never the transcript --
    and only what it actually reported.
    """
    weak = [w for w in (evaluation.get("what_was_weak") or []) if isinstance(w, str)]
    missing = [w for w in (evaluation.get("missing_concepts") or []) if isinstance(w, str)]
    parts: list[str] = []
    if weak:
        parts.append("weak: " + "; ".join(weak[:3]))
    if missing:
        parts.append("missing concepts: " + "; ".join(missing[:3]))
    if not parts:
        return 0
    content = " | ".join(parts)
    key = f"interview:{session_id[:12]}"
    try:
        await domain.upsert_memory(user_id, "interview", key, content[:4000],
                                   source="interview", importance=0.7)
        await observability.trace(run_id, "step_start", "interview",
                                  {"stage": "memory_write", "kind": "interview"})
    except Exception:
        log.warning("interview memory write failed", exc_info=True)
        return 0
    return 1
