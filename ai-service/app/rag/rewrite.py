"""Query understanding: rewrite, multi-query expansion, intent detection."""

from app.core.ai import ask_json
from app.providers.base import LLMMessage, LLMRequest

_INTENTS = [
    "career_advice",        # general guidance about user's search
    "match_analysis",       # user vs a specific job/jd
    "skill_gap",            # what is missing
    "resume_improvement",   # feedback on resume content
    "job_search",           # find/recommend jobs
    "interview_prep",       # practice/explain topics
    "personal_fact",        # asking about their own history
    "other",
]

_SYSTEM = f"""You are the query-understanding stage of a career RAG system.
Return JSON only:
{{"rewritten": "<self-contained query, resolve pronouns using context>",
  "expansions": ["<2-3 semantically different phrasings>"],
  "intent": "<one of: {', '.join(_INTENTS)}>",
  "keywords": ["<5-8 retrieval keywords incl. skill names>"],
  "needs_personal_evidence": <true|false>,
  "filters": {{"kinds": [<subset of resume|note|jd|company|interview_feedback|project|certificate|course|goal, empty if none>]}}}}"""


async def understand(query: str, context_summary: str = "", *, user_id=None, run_id=None,
                     agent="rag") -> dict:
    req = LLMRequest(
        messages=[
            LLMMessage("system", _SYSTEM),
            LLMMessage("user", f"Conversation context:\n{context_summary[:1500] or '(none)'}\n\n"
                               f"User query: {query}"),
        ],
        temperature=0.0, max_tokens=500)
    try:
        out = await ask_json(req, user_id=user_id, run_id=run_id, agent=agent,
                             kind="query_understanding")
    except Exception:
        out = {}
    return {
        "rewritten": out.get("rewritten") or query,
        "expansions": [e for e in (out.get("expansions") or []) if isinstance(e, str)][:3],
        "intent": out.get("intent") if out.get("intent") in _INTENTS else "other",
        "keywords": [k for k in (out.get("keywords") or []) if isinstance(k, str)][:8],
        "needs_personal_evidence": bool(out.get("needs_personal_evidence", True)),
        "filters": out.get("filters") if isinstance(out.get("filters"), dict) else {},
        "original": query,
    }
