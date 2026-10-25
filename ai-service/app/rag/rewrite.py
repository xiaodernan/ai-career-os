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


def _str_list(value, limit: int) -> list[str]:
    """A list of non-empty phrases from a model field that should have been an array.

    JSON can hand a bare string where the schema asks for `["..."]`. Iterating a
    string yields its *characters*, which is how `keywords: "Kafka Spring"` became
    `['K', 'a', 'f']` and sent the keyword channel after single letters -- a silent
    retrieval-quality collapse, not an error anyone would see. A bare string is
    therefore read as one phrase, split on commas when it carries them.
    """
    if isinstance(value, str):
        raw: list = value.split(",")
    elif isinstance(value, (list, tuple)):
        raw = list(value)
    else:
        return []
    return [v.strip() for v in raw if isinstance(v, str) and v.strip()][:limit]


def _as_bool(value, default: bool = True) -> bool:
    """A JSON flag, where the string "false" must not read as true.

    `bool("false")` is True, so a model that answered with a string instead of a
    literal flipped the flag to the opposite of what it said.
    """
    if isinstance(value, str):
        return value.strip().lower() not in ("", "false", "0", "no", "none", "null")
    if value is None:
        return default
    return bool(value)


async def understand(query: str, context_summary: str = "", *, user_id=None, run_id=None,
                     agent="rag") -> dict:
    context = context_summary if isinstance(context_summary, str) else ""
    req = LLMRequest(
        messages=[
            LLMMessage("system", _SYSTEM),
            LLMMessage("user", f"Conversation context:\n{context[:1500] or '(none)'}\n\n"
                               f"User query: {query}"),
        ],
        temperature=0.0, max_tokens=500)
    try:
        out = await ask_json(req, user_id=user_id, run_id=run_id, agent=agent,
                             kind="query_understanding")
    except Exception:
        out = {}
    # `rewritten` is the single field every channel consumes, so a non-string here
    # must fall back to the raw query rather than flow on as a list or a number.
    rewritten = out.get("rewritten")
    if not isinstance(rewritten, str) or not rewritten.strip():
        rewritten = query if isinstance(query, str) else ""
    return {
        "rewritten": rewritten,
        "expansions": _str_list(out.get("expansions"), 3),
        "intent": out.get("intent") if out.get("intent") in _INTENTS else "other",
        "keywords": _str_list(out.get("keywords"), 8),
        "needs_personal_evidence": _as_bool(out.get("needs_personal_evidence")),
        "filters": out.get("filters") if isinstance(out.get("filters"), dict) else {},
        "original": query,
    }
