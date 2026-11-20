"""Cover letter generation + variants (PRD §12)."""

import re

from app.agents.stategraph import NodeResult, StateGraph
from app.core.ai import ask, stable_messages, wrap_untrusted
from app.core.skills import extract_skills, normalize
from app.providers.base import LLMMessage, LLMRequest
from app.rag.pipeline import retrieve

BASE_SYSTEM = """You write job-application cover letters grounded ONLY in the provided
resume evidence and company facts. Never invent experience. Structure: 3-4 short
paragraphs — opening hook tied to the role/company, 2 concrete proof paragraphs
(the most relevant experiences with numbers), motivation + closing. Tone: confident,
specific, zero fluff. Output plain letter text, no markdown headers."""

VARIANTS = {
    "regenerate": "Write a fresh version with different angles/examples from the evidence.",
    "shorten": "Compress to under 180 words, keep the strongest proof only.",
    "formal": "More formal register; traditional business-letter phrasing.",
    "concise": "Punchy, one idea per sentence, no filler.",
}

TONE_DIRECTIVES = {
    "formal": "Use a formal, traditional business-letter register.",
    "concise": "Be direct: short sentences, no filler or pleasantries.",
    "confident": "Project confident, assured ownership of achievements.",
    "balanced": "",
}

LENGTH_DIRECTIVES = {
    "short": "Keep the whole letter under 180 words.",
    "standard": "Aim for roughly 300 words.",
    "detailed": "Aim for roughly 450 words with fuller proof.",
}


def style_directives(tone: str, length: str) -> list[str]:
    """Map the UI's tone/length knobs to prompt directives (independent of mode)."""
    out = []
    t = TONE_DIRECTIVES.get((tone or "").strip().lower())
    if t:
        out.append(t)
    ln = LENGTH_DIRECTIVES.get((length or "").strip().lower())
    if ln:
        out.append(ln)
    return out


_MAX_DRAFTS = 2


def _numbers_in(s: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?%?", s if isinstance(s, str) else ""))


def verify_no_fabrication(source_text: str, letter: str) -> str | None:
    """Return a rejection reason if `letter` introduces facts absent from the sources.

    Deterministic, parse-only, offline. The verifier never rewrites and never grades
    style — it only asks whether the numbers and the skills the letter names appear
    anywhere in the resume, JD, company facts, or the reader's stated goal. A miss is
    a reason, and the draft node retries with it. A letter that still fails renders
    with the rejection recorded instead of silently passing.
    """
    source_text = source_text if isinstance(source_text, str) else ""
    letter = letter if isinstance(letter, str) else ""
    src_skills = {normalize(s) for s in extract_skills(source_text)}
    letter_skills = {normalize(s) for s in extract_skills(letter)}
    invented = letter_skills - src_skills
    if invented:
        return f"invented skills: {sorted(invented)}"
    new_nums = _numbers_in(letter) - _numbers_in(source_text)
    if new_nums:
        return f"invented numbers: {sorted(new_nums)}"
    return None


def _source_text(resume_structured: object, resume_text: str, jd: object,
                 company: object, goal: str) -> str:
    return " ".join([str(resume_structured or {}), str(resume_text or ""),
                     str(jd or {}), str(company or {}), str(goal or "")])


async def generate(resume_structured: dict, resume_text: str, jd: dict,
                   company: dict | None, goal: str, *, user_id: str,
                   mode: str = "generate", previous: str = "",
                   tone: str = "", length: str = "",
                   run_id: str | None = None) -> dict:
    jd = jd if isinstance(jd, dict) else {}
    query = " ".join([s.get("name", "") for s in (jd.get("requiredSkills") or [])
                      if isinstance(s, dict)][:10])
    source_text = _source_text(resume_structured, resume_text, jd, company, goal)

    async def retrieve_node(state):
        r = await retrieve(query or jd.get("title", "top achievements"), user_id=user_id,
                           run_id=run_id, top_k=6, kinds=["resume", "project", "goal"])
        prompt = _build_prompt(resume_structured, jd, company, goal,
                               r.get("context_block", ""), tone, length, mode, previous)
        return NodeResult(state={"context": prompt, "evidence": r["evidence"]},
                          goto="draft",
                          trace={"context_chars": len(prompt)})

    async def draft_node(state):
        prompt = state["context"]
        if state.get("verifier_feedback"):
            prompt += ("\n\nVERIFIER REJECTION (rewrite with the rejected claims REMOVED, "
                       f"not reworded; everything it rejected must not reappear): "
                       f"{state['verifier_feedback']}")
        resp = await ask(LLMRequest(
            messages=stable_messages(BASE_SYSTEM, LLMMessage("user", prompt)),
            temperature=0.0 if mode in ("regenerate",) else 0.0, max_tokens=900),
            user_id=user_id, run_id=run_id, agent="resume", kind="cover_letter")
        return NodeResult(state={"letter": resp.text, "model": resp.model,
                                 "attempts": state["attempts"] + 1},
                          goto="verify",
                          trace={"attempt": state["attempts"] + 1})

    async def verify_node(state):
        reason = verify_no_fabrication(source_text, state["letter"])
        if reason and state["attempts"] < _MAX_DRAFTS:
            return NodeResult(state={"rejected": [reason], "verifier_feedback": reason},
                              goto="draft",
                              trace={"reject": reason})
        return NodeResult(state={"rejected": [reason] if reason else []},
                          goto="render",
                          trace={"routing": "render", "rejected": bool(reason)})

    async def render_node(state):
        # The veto decision rides the trace ledger (graph_node rows), the same channel
        # the resume tailor's verify verdicts already ride. The answer frame stays
        # exactly {letter, sources, mode, model} — the browser census pins that row.
        return NodeResult(
            state={"letter": state["letter"], "sources": state["evidence"],
                   "mode": mode, "model": state["model"]},
            goto=None,
            trace={"rejected_count": len(state.get("rejected", []))})

    graph = StateGraph("retrieve",
                       {"retrieve": retrieve_node, "draft": draft_node,
                        "verify": verify_node, "render": render_node},
                       max_steps=6)
    final = await graph.run({"attempts": 0}, run_id=run_id, agent="resume")
    # the graph's shallow merge accumulates state; the wire keeps exactly the documented row
    return {"letter": final["letter"], "sources": final["sources"],
            "mode": final["mode"], "model": final["model"]}


def _build_prompt(resume_structured: dict, jd: dict, company: dict | None, goal: str,
                  context_block: str, tone: str, length: str, mode: str,
                  previous: str) -> str:
    """Assemble the cover-letter user prompt. Pure (no LLM/DB) so the conditional
    assembly — empty-fact dropping, company fallback, STYLE and previous-version gating —
    is unit-testable in isolation."""
    jd = jd if isinstance(jd, dict) else {}
    resume_structured = resume_structured if isinstance(resume_structured, dict) else {}
    profile = resume_structured.get("profile")
    profile = profile if isinstance(profile, dict) else {}
    facts = [
        f"ROLE: {jd.get('title','')}",
        f"COMPANY: {company.get('name') if company else jd.get('company','')}",
        (f"COMPANY OVERVIEW: {wrap_untrusted('COMPANY', company.get('overview',''))}"
         if company else ""),
        f"JD TOP REQUIREMENTS: {[s.get('name') for s in (jd.get('requiredSkills') or []) if isinstance(s, dict)][:10]}",
        f"CANDIDATE: {profile.get('name','')} - {profile.get('headline','')}",
        f"CAREER GOAL: {goal}" if goal else "",
        f"EVIDENCE:\n{context_block}",
    ]
    prompt = "\n".join(f for f in facts if f)
    directives = style_directives(tone, length)
    if directives:
        prompt = f"{prompt}\n\nSTYLE: " + " ".join(directives)
    if previous and (mode in VARIANTS or mode == "customize"):
        instruction = VARIANTS.get(mode) or str(jd.get("customization", "make it better"))
        prompt = (f"{prompt}\n\nPREVIOUS VERSION:\n{previous}\n\nINSTRUCTION: "
                  f"{instruction}")
    return prompt
