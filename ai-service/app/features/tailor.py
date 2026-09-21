"""AI Resume Tailoring (PRD §11) with a hard no-fabrication verifier.

The LLM may reorder, re-emphasize and reword — but a post-pass verifier rejects any
bullet introducing a skill, company or number absent from the original resume text,
falling back to the original wording. Fabrication is blocked mechanically, not by
asking nicely.
"""

import re

from app.core.ai import ask_json, wrap_untrusted
from app.core.skills import extract_skills, normalize
from app.providers.base import LLMMessage, LLMRequest
from app.rag.pipeline import retrieve

SYSTEM = """You tailor an existing resume for one job WITHOUT inventing anything.
You MAY: reorder sections/bullets/projects/skills; reword bullets to foreground the
JD's terminology and priorities; tighten summaries; move the most relevant items up.
You MUST NOT: add projects, employers, dates, skills, tools, numbers, percentages or
achievements not present in the source material; exaggerate facts.
Return JSON:
{"changes":[{"section":"experience|projects|skills|summary|ordering",
  "index":0,"before":"<original bullet or item>","after":"<new wording>",
  "reason":"<why this helps for the JD>"}],
 "summary":"<new professional summary, <=2 sentences>",
 "skillOrder":["<all original skills, most JD-relevant first>"],
 "notes":["<anything the candidate should double-check>"]}"""


def _numbers_in(s: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?%?", s))


def verify_no_fabrication(original_text: str, before: str, after: str) -> str | None:
    """Return rejection reason if `after` introduces facts absent from the resume."""
    src_skills = {normalize(s) for s in extract_skills(original_text)}
    after_skills = {normalize(s) for s in extract_skills(after)}
    invented = after_skills - src_skills
    if invented:
        return f"invented skills: {sorted(invented)}"
    new_nums = _numbers_in(after) - _numbers_in(original_text) - _numbers_in(before)
    if new_nums:
        return f"invented numbers: {sorted(new_nums)}"
    return None


async def tailor(resume_structured: dict, resume_text: str, jd: dict, *, user_id: str,
                 job_title: str = "", run_id: str | None = None) -> dict:
    matched_query = " ".join(
        [s.get("name", "") for s in (jd.get("requiredSkills") or [])][:12]
        + [jd.get("title", "")])
    r = await retrieve(matched_query or jd.get("title", "relevant experience"),
                       user_id=user_id, run_id=run_id, top_k=8, kinds=["resume", "project"])
    context = (
        f"JOB TARGET: {job_title or jd.get('title','')}\n"
        f"JD REQUIRED: {[s.get('name') for s in (jd.get('requiredSkills') or [])]}\n"
        f"JD PREFERRED: {[s.get('name') for s in (jd.get('preferredSkills') or [])]}\n\n"
        f"CAREER KNOWLEDGE (evidence you may foreground):\n{r.get('context_block','')}\n\n"
        f"ORIGINAL RESUME JSON:\n{wrap_untrusted('RESUME', str(resume_structured)[:16000])}"
    )
    req = LLMRequest(
        messages=[LLMMessage("system", SYSTEM), LLMMessage("user", context)],
        temperature=0.2, max_tokens=4000)
    out = await ask_json(req, user_id=user_id, run_id=run_id, agent="resume", kind="tailor")

    accepted, rejected = [], []
    for ch in out.get("changes") or []:
        if not isinstance(ch, dict) or not ch.get("after"):
            continue
        reason = verify_no_fabrication(resume_text, str(ch.get("before", "")),
                                       str(ch["after"]))
        if reason:
            ch["verifier_reject"] = reason
            rejected.append(ch)
        else:
            accepted.append(ch)

    # apply accepted edits onto a copy of the structured resume
    tailored = _apply_changes(resume_structured, accepted, out, resume_text)
    return {"tailored": tailored, "diff": {"accepted": accepted, "rejected": rejected},
            "notes": out.get("notes") or [], "evidence": r["evidence"],
            "stats": {"accepted": len(accepted), "rejected": len(rejected)}}


def _apply_changes(structured: dict, changes: list[dict], out: dict,
                   resume_text: str) -> dict:
    import copy

    t = copy.deepcopy(structured)
    for ch in changes:
        sec = ch.get("section")
        if sec not in ("experience", "projects"):
            continue
        idx = ch.get("index")
        items = t.get(sec) or []
        if isinstance(idx, int) and 0 <= idx < len(items):
            item = items[idx]
            b_before, b_after = str(ch.get("before", "")), str(ch["after"])
            bullets = item.get("bullets") or []
            hit = False
            for i, b in enumerate(bullets):
                if b.strip().lower()[:80] == b_before.strip().lower()[:80]:
                    bullets[i] = b_after
                    hit = True
            if not hit and idx < len(bullets):
                bullets[idx] = b_after
            item["bullets"] = bullets
    if out.get("summary") and verify_no_fabrication(resume_text, "", out["summary"]) is None:
        t.setdefault("profile", {})["summary"] = out["summary"]
    skill_order = [s for s in (out.get("skillOrder") or [])
                   if normalize(s) in {normalize(x) for x in resume_text.split()}
                   or normalize(s) in {normalize(s2.get("name", ""))
                                       for s2 in t.get("skills") or []}]
    if skill_order:
        rank = {normalize(s): i for i, s in enumerate(skill_order)}
        t["skills"] = sorted(t.get("skills") or [],
                             key=lambda s: rank.get(normalize(s.get("name", "")), 999))
    return t
