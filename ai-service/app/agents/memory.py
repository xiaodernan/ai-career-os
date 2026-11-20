"""Agent memory (PRD §17).

Short-term: conversation history assembled by the orchestrator.
Long-term: distilled facts in user_memories, retrieved into every run's system
context and extracted after meaningful turns.
"""

import logging

from app.core import db
from app.core.ai import ask_json, stable_messages, wrap_untrusted
from app.core.skills import normalize
from app.db import domain, observability
from app.providers.base import LLMMessage, LLMRequest
from app.agents.stategraph import NodeResult, StateGraph

log = logging.getLogger("agents.memory")

MEMORY_KINDS = {"profile", "skill", "preference", "interview", "goal", "fact"}

_KIND_LABEL = {
    "profile": "Profile", "skill": "Skills", "preference": "Preferences",
    "interview": "Interview history", "goal": "Goals", "fact": "Facts",
}


async def build_memory_context(user_id: str) -> str:  # noqa: F811  (placeholder anchor kept for clarity below)
    return await _memory_context(user_id)


async def _memory_context(user_id: str) -> str:
    """The user's durable memory as prompt text, or "" when it cannot be built."""
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
    entries: list[tuple[str, str]] = []
    for kind, items in by_kind.items():
        label = _KIND_LABEL.get(kind, kind)
        for line in items:
            entries.append((label, line))
    # Deterministic order, not retrieval order: `get_memories` returns rows by
    # importance/updated_at, so a single correction anywhere in the block
    # reshuffles every line after it — and a prefix cache that matches on
    # bytes misses from the first shuffled line on. Sorted, an edit moves
    # nothing that does not reference it, and the block is byte-identical
    # whenever the user's memory is unchanged.
    entries.sort(key=lambda item: (item[0], item[1]))
    for label, line in entries:
        lines.append(f"- [{label}] {line}")
    return "\n".join(lines) if len(lines) > 1 else ""


# ---------------------------------------------------------------- dossier --


def _trim(text: str | None, limit: int) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip()
    return text[:limit]


def _order_distinct_apps(rows: list[dict], *, cap: int) -> list[dict]:
    """Collapse floods of identical (title, company, status) rows into single lines.

    The wire's e2e accounts apply to the same posting sixty-one times; listing the
    triple sixty-one times floods the prefix cache with bytes that say nothing and
    tells the model a lie about variety. The honest count costs one line and never
    hides the material: ``×N`` is the true row count, unbounded. ``cap`` bounds how
    many distinct triples are rendered.
    """
    counts: dict[tuple[str, str, str], int] = {}
    for r in rows:
        key = (_trim(r.get("title"), 64),
               _trim(r.get("company"), 48),
               _trim(r.get("status"), 12))
        if not any(key):
            continue
        counts[key] = counts.get(key, 0) + 1
    emitted: set[tuple[str, str, str]] = set()
    out: list[dict] = []
    for r in rows:
        key = (_trim(r.get("title"), 64),
               _trim(r.get("company"), 48),
               _trim(r.get("status"), 12))
        if not any(key) or key in emitted:
            continue
        emitted.add(key)
        out.append({**r, "_count": counts[key]})
        if len(out) >= cap:
            break
    return out


async def build_dossier_context(user_id: str) -> str:
    """A rich, byte-stable dossier of the user's own material, for the prefix cache.

    The dossier the copilot walks in with, built by the compiler from rows: the latest
    resume plaintext (up to 10 k chars, verbatim), the 25 most recent distinct
    applications with repeated rows shown as ``×N`` (bounds the synthetic-flood case
    without inventing variety), the 15 best-scored matches with their technical and
    missing-skill detail, the 10 most recent interview memories (the interviewer's own
    notes on this candidate), the 14 goals the wire recorded (ambition is the
    highest-signal memory class), and every named skill. Nothing here is invented; the
    only writes are counts the wire already knows. Sections render in a fixed order,
    every ORDER BY in the SQL carries an ``id`` tiebreak, and no timestamps enter —
    the provider-side cache can serve every call after the first for the exact bytes.
    """
    out: list[str] = ["## Candidate dossier"]

    digest_apps: int | None = None
    digest_interviews: int | None = None
    try:
        totals = await db.fetch(
            """SELECT (SELECT count(*) FROM applications WHERE user_id = $1::uuid) AS apps,
                      (SELECT count(*) FROM user_memories
                         WHERE user_id = $1::uuid AND kind = 'interview') AS interviews""",
            user_id)
        if totals:
            digest_apps = totals[0].get("apps")
            digest_interviews = totals[0].get("interviews")
    except Exception as e:
        log.warning("dossier: digest counters unavailable, continuing: %s", e)

    try:
        rv = await domain.get_current_resume_version(user_id)
    except Exception as e:
        log.warning("dossier: resume fetch failed, continuing: %s", e)
        rv = None
    if rv:
        plain = _trim(rv.get("plaintext"), 10000)
        label = _trim(rv.get("label"), 48) or "resume"
        out.append(f"### resume ({label})\n{plain}" if plain else f"### resume ({label})\n(plaintext not stored)")

    try:
        rows = await db.fetch(
            """SELECT title, COALESCE(company_name, '') AS company, status, updated_at, id
               FROM applications
               WHERE user_id = $1::uuid
               ORDER BY updated_at DESC NULLS LAST, created_at DESC, id DESC
               LIMIT 40""",
            user_id,
        )
        apps = _order_distinct_apps(rows, cap=25)
    except Exception as e:
        log.warning("dossier: applications fetch failed, continuing: %s", e)
        apps = []
    for app in apps:
        company = _trim(app.get("company"), 48)
        title = _trim(app.get("title"), 64)
        status = _trim(app.get("status"), 12)
        repeat = app.get("_count") if isinstance(app, dict) else None
        suffix = f" ×{repeat}" if isinstance(repeat, int) and repeat > 1 else ""
        out.append(f"- [app] {title} @{company} — {status}{suffix}")

    try:
        matches = await db.fetch(
            """SELECT j.title, jm.overall, jm.technical, jm.missing_skills, jm.id
               FROM job_matches jm
               JOIN jobs j ON j.id = jm.job_id
               WHERE jm.user_id = $1::uuid
               ORDER BY jm.created_at DESC NULLS LAST, jm.id DESC
               LIMIT 15""",
            user_id,
        )
    except Exception as e:
        log.warning("dossier: matches fetch failed, continuing: %s", e)
        matches = []
    for m in matches:
        title = _trim(m.get("title"), 64)
        overall = m.get("overall")
        technical = m.get("technical")
        overall = overall if isinstance(overall, (int, float)) else 0
        technical = technical if isinstance(technical, (int, float)) else None
        missing = _trim(", ".join([str(s) for s in (m.get("missing_skills") or []) if isinstance(s, str)]), 100)
        tech = f", tech {round(technical):.0%}" if technical is not None else ""
        out.append(f"- [match {round(overall):.0%}{tech}] {title} — missing: {missing}")

    try:
        interviews = await domain.get_memories(user_id, kinds=["interview"], limit=10)
    except Exception as e:
        log.warning("dossier: interviews fetch failed, continuing: %s", e)
        interviews = []
    if interviews:
        out.append("### interview memory (the wire's notes on this candidate)")
        for iv in interviews:
            content = _trim(iv.get("content") if isinstance(iv, dict) else None, 400)
            if content:
                out.append(f"- {content}")

    try:
        goals = await domain.get_memories(user_id, kinds=["goal"], limit=14)
    except Exception as e:
        log.warning("dossier: goals fetch failed, continuing: %s", e)
        goals = []
    if goals:
        out.append("### goals (the candidate's stated ambitions)")
        for g in goals:
            content = _trim(g.get("content") if isinstance(g, dict) else None, 400)
            if content:
                out.append(f"- {content}")

    try:
        profile = await domain.get_profile(user_id)
    except Exception as e:
        log.warning("dossier: profile fetch failed, continuing: %s", e)
        profile = None
    if profile and isinstance(profile, dict):
        ps = profile.get("skills")
        if isinstance(ps, list) and ps:
            canonical = sorted({normalize(s.get("name") or str(s)) for s in ps
                                if isinstance(s, (str, dict))} - {""})
            if canonical:
                out.append(f"### dossier: skills ({len(canonical)} named)\n" +
                           ", ".join(canonical[:60]))

    if digest_apps is not None or digest_interviews is not None:
        out.append(
            f"### the wire at a glance\n"
            f"- applications on file: {digest_apps if digest_apps is not None else 'unknown'}\n"
            f"- mock-interview sessions practiced: {digest_interviews if digest_interviews is not None else 'unknown'}")

    # Epic 270: the NOW sections — what is about to bite and what just arrived. The
    # dossier's other halves are the record; these are the live edge, the two things
    # a copilot turn most often needs to know without a tool round-trip.
    try:
        deadlines = await db.fetch(
            """SELECT reminder_at, title, company_name FROM applications
               WHERE user_id = $1::uuid AND reminder_at IS NOT NULL AND reminder_at > now()
               ORDER BY reminder_at ASC LIMIT 5""",
            user_id)
        if deadlines:
            out.append("### deadlines ahead (the offers and follow-ups about to bite)")
            for r in deadlines:
                when = str(r.get("reminder_at", ""))[:16]
                out.append(f"- {when} · {r.get('title', '')}"
                           + (f" @ {r.get('company_name')}" if r.get("company_name") else ""))
    except Exception as e:
        log.warning("dossier: deadlines fetch failed, continuing: %s", e)

    try:
        replies = await db.fetch(
            """SELECT received_at, company, intent, body_text FROM inbound_mails
               WHERE user_id = $1::uuid ORDER BY received_at DESC LIMIT 3""",
            user_id)
        if replies:
            out.append("### newest recruiter replies (the live edge of the search)")
            for r in replies:
                snippet = str(r.get("body_text", ""))[:200].replace("\n", " ")
                out.append(f"- {str(r.get('received_at', ''))[:10]} · "
                           f"{r.get('company') or '?'} · intent={r.get('intent') or '?'} · {snippet}")
    except Exception as e:
        log.warning("dossier: replies fetch failed, continuing: %s", e)

    return "\n".join(out) if len(out) > 1 else ""


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

    async def _extract(state: dict) -> NodeResult:
        try:
            data = await ask_json(
                LLMRequest(messages=stable_messages(EXTRACT_SYSTEM, LLMMessage("user", prompt)),
                           temperature=0.0, max_tokens=800),
                user_id=user_id, run_id=run_id, agent="career", kind="memory_extract")
        except Exception:
            log.warning("memory extraction failed", exc_info=True)
            return NodeResult({"memories": [], "failed": True}, None, trace={"error": True})
        if not isinstance(data, dict):
            data = {}
        return NodeResult({"memories": data.get("memories") or [], "failed": False},
                           "verify", trace={"raw": len(data.get("memories") or [])})

    async def _verify(state: dict) -> NodeResult:
        kept: list[dict] = []
        drops = 0
        for m in (state.get("memories") or [])[:4]:
            if not isinstance(m, dict):
                drops += 1
                continue
            kind = m.get("kind")
            content = (m.get("content") or "").strip()
            if kind not in MEMORY_KINDS or len(content) < 8:
                drops += 1
                continue
            key = (m.get("key") or "").strip() or content[:40]
            try:
                importance = max(0.0, min(1.0, float(m.get("importance", 0.6))))
            except (TypeError, ValueError):
                importance = 0.6
            kept.append({"kind": kind, "key": key, "content": content,
                         "importance": importance})
        return NodeResult({"kept": kept, "dropped": drops}, "render",
                           trace={"dropped": drops, "kept": len(kept)})

    async def _render(state: dict) -> NodeResult:
        saved = 0
        for m in state.get("kept") or []:
            await domain.upsert_memory(user_id, m["kind"], m["key"], m["content"],
                                        source="chat", importance=m["importance"])
            saved += 1
        if saved:
            await observability.trace(run_id, "step_start", "career",
                                      {"stage": "memory_extract", "saved": saved})
        return NodeResult({"saved": saved, "failed": state.get("failed")}, None,
                          trace={"saved": saved})

    graph = StateGraph("extract", {"extract": _extract, "verify": _verify,
                                    "render": _render},
                       max_steps=4)
    final = await graph.run({"user_text": user_text, "answer": answer},
                            run_id=run_id, agent="career")
    return final["saved"]


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
