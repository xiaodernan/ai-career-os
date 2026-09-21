"""Cover letter generation + variants (PRD §12)."""

from app.core.ai import ask, wrap_untrusted
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


async def generate(resume_structured: dict, resume_text: str, jd: dict,
                   company: dict | None, goal: str, *, user_id: str,
                   mode: str = "generate", previous: str = "",
                   run_id: str | None = None) -> dict:
    query = " ".join([s.get("name", "") for s in (jd.get("requiredSkills") or [])][:10])
    r = await retrieve(query or jd.get("title", "top achievements"), user_id=user_id,
                       run_id=run_id, top_k=6, kinds=["resume", "project", "goal"])
    facts = [
        f"ROLE: {jd.get('title','')}",
        f"COMPANY: {company.get('name') if company else jd.get('company','')}",
        f"COMPANY OVERVIEW: {wrap_untrusted('COMPANY', (company or {}).get('overview','')) if company else ''}",
        f"JD TOP REQUIREMENTS: {[s.get('name') for s in (jd.get('requiredSkills') or [])][:10]}",
        f"CANDIDATE: {resume_structured.get('profile',{}).get('name','')} - "
        f"{resume_structured.get('profile',{}).get('headline','')}",
        f"CAREER GOAL: {goal}" if goal else "",
        f"EVIDENCE:\n{r.get('context_block','')}",
    ]
    prompt = "\n".join(f for f in facts if f)
    if previous and (mode in VARIANTS or mode == "customize"):
        instruction = VARIANTS.get(mode) or str(jd.get("customization", "make it better"))
        prompt = (f"{prompt}\n\nPREVIOUS VERSION:\n{previous}\n\nINSTRUCTION: "
                  f"{instruction}")
    resp = await ask(LLMRequest(
        messages=[LLMMessage("system", BASE_SYSTEM), LLMMessage("user", prompt)],
        temperature=0.6 if mode in ("regenerate",) else 0.4, max_tokens=900),
        user_id=user_id, run_id=run_id, agent="resume", kind="cover_letter")
    return {"letter": resp.text, "sources": r["evidence"], "mode": mode,
            "model": resp.model}
