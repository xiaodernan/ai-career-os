"""Adaptive interview engine (PRD §13-15).

Dynamic — never a pre-generated question list. Each candidate answer is evaluated,
then the agent decides: drill deeper with a follow-up chain, switch topic, or wrap
up. Difficulty adapts to answer quality; the question/answer tree becomes the
"interview depth trajectory".
"""

from app.core.ai import ask, ask_json, wrap_untrusted
from app.providers.base import LLMMessage, LLMRequest

# These keys ARE the mode vocabulary: `opening_question` and `advance` fall back to the `mixed`
# persona for a mode listed nowhere here, so a mode that exists in one author and not the other
# silently changes which interview the candidate gets. `@/lib/interview-modes` is the client's
# one list of them; `test_the_interview_mode_vocabulary_has_one_author.py` keeps the two together.
_INTERVIEWER_PERSONA = {
    "behavioral": "an experienced hiring manager probing ownership, conflict and impact",
    "technical": "a senior engineer drilling into fundamentals and code-level decisions",
    "system_design": "a staff engineer running an open-ended design interview",
    "ai_llm": "an AI-platform interviewer covering LLM/RAG/agent engineering",
    "rag": "an interviewer focused specifically on retrieval systems",
    "agent": "an interviewer focused on autonomous agents, tools and orchestration",
    "backend": "a backend interviewer covering APIs, storage, concurrency and reliability",
    "mixed": "a pragmatic senior interviewer mixing behavioral and technical rounds",
}

DIMENSIONS = ["technical_accuracy", "communication", "depth", "structure",
              "problem_solving", "system_thinking", "ai_knowledge", "backend_knowledge"]

EVAL_SYSTEM = f"""You grade ONE interview answer. JSON only:
{{"score": 0.0-1.0,
 "dims": {{{", ".join(f'"{d}": 0.0-1.0' for d in DIMENSIONS[:4])}}},
 "strengths": [""], "weaknesses": [""], "missing_concepts": [""],
 "better_answer": "<concise model answer, <=120 words>",
 "question_was_answered": true|false}}
Be a strict but fair senior interviewer. Judge only the answer given."""

ADVANCE_SYSTEM = """You are the interview director. Given the interview state, decide the
single next move. JSON only:
{"action": "followup" | "next_topic" | "finish",
 "question": "<exact next question, or empty for finish>",
 "topic": "<topic of the next question>",
 "difficulty": 0.0-1.0,
 "reasoning": "<one line>"}
Rules:
- If the last answer was weak or vague: action=followup, a clarifying/simplifying probe,
  difficulty slightly LOWER.
- If strong: action=followup, a deeper probe (why-this-not-that, failure modes, scale
  it up, trade-offs), difficulty HIGHER. Classic ladder: mechanism -> alternative ->
  failure handling -> scale.
- After 2-3 follow-ups on one topic (or when the topic is exhausted): action=next_topic.
- Total planned length is in state; prefer finish when reached or answers show the
  candidate's ceiling is measured.
- Questions must fit the persona, reference the candidate's own resume context when
  natural, and stay in the interview language."""


def _state_brief(persona: str, mode: str, turns: list[dict], difficulty: float,
                 qnum: int, max_q: int, resume_ctx: str, jd_topics: list[str]) -> str:
    convo = "\n".join(
        f"{'INTERVIEWER' if t['role']=='interviewer' else 'CANDIDATE'}: {t['content'][:350]}"
        for t in turns[-10:])
    return (f"Persona: {persona}\nMode: {mode}\nQuestion {qnum} asked so far / target "
            f"{max_q}. Difficulty now: {difficulty:.2f}.\n"
            f"Suggested topics: {jd_topics}\nCandidate context:\n"
            f"{wrap_untrusted('CANDIDATE_CONTEXT', resume_ctx[:2500])}\n\nConversation:\n{convo}")


def opening_meta(topic: str) -> dict:
    """The `question_meta` the first turn of a session carries.

    Its own function because that dict is the wire shape -- the backend stores it verbatim into
    `interview_turns.question_meta` -- and the contract gate binds the browser's reads of it to the
    single literal that states it.
    """
    return {"topic": topic, "depth_level": 0, "expected_points": [], "phase": "opening"}


async def opening_question(*, mode: str, company: str, position: str, resume_ctx: str,
                          jd_topics: list[str], candidate_name: str = "",
                          user_id: str | None = None, run_id: str | None = None) -> dict:
    persona = _INTERVIEWER_PERSONA.get(mode, _INTERVIEWER_PERSONA["mixed"])
    prompt = _state_brief(persona, mode, [], 0.5, 0, 8, resume_ctx, jd_topics) + \
        f"\n\nCompany: {company} Position: {position}. Open the interview: one short " \
        f"greeting{' using the name ' + candidate_name if candidate_name else ''}, " \
        "one sentence on format, then the FIRST question only."
    resp = await ask(LLMRequest(
        messages=[LLMMessage("system", "You conduct realistic mock job interviews. "
                                       "Ask exactly ONE question. Be concise."),
                  LLMMessage("user", prompt)],
        temperature=0.7, max_tokens=260),
        user_id=user_id, run_id=run_id, agent="interview", kind="interview_open")
    text = resp.text.strip()
    topic = (jd_topics or ["background"])[0]
    return {"question": text, "meta": opening_meta(topic), "model": resp.model}


async def evaluate_answer(*, mode: str, question: str, answer: str, resume_ctx: str,
                          user_id: str | None = None, run_id: str | None = None) -> dict:
    prompt = (f"Interview context (candidate's real background, untrusted):\n"
              f"{wrap_untrusted('CANDIDATE_CONTEXT', resume_ctx[:2500])}\n\n"
              f"QUESTION: {question}\n\nCANDIDATE ANSWER:\n"
              f"{wrap_untrusted('ANSWER', answer[:4000])}")
    try:
        ev = await ask_json(LLMRequest(
            messages=[LLMMessage("system", EVAL_SYSTEM), LLMMessage("user", prompt)],
            temperature=0.1, max_tokens=900),
            user_id=user_id, run_id=run_id, agent="interview", kind="answer_eval")
    except Exception:
        ev = {"score": 0.5, "question_was_answered": True}
    return ev


def decide_next(out: dict, *, difficulty: float, qnum: int, max_q: int,
                turns: list[dict]) -> dict:
    """Coerce the LLM's raw advance output into the session's next-move contract.

    Pure and deterministic (no I/O): the action is whitelisted, the interview is
    force-finished once the question budget is spent, and difficulty is clamped to
    the band the adaptive ladder is designed for. Split out of ``advance`` so the
    decision rule is unit-testable without an LLM.
    """
    action = out.get("action") if out.get("action") in ("followup", "next_topic",
                                                        "finish") else "next_topic"
    if qnum >= max_q and action != "finish":
        action = "finish" if turns and turns[-1]["role"] == "candidate" else action
    try:
        d = float(out.get("difficulty", difficulty))
    except (TypeError, ValueError):
        d = difficulty
    d = max(0.1, min(0.95, d))
    return {"action": action, "question": (out.get("question") or "").strip(),
            "topic": out.get("topic") or "", "difficulty": d,
            "reasoning": out.get("reasoning", "")}


async def advance(*, mode: str, turns: list[dict], difficulty: float, qnum: int,
                  max_q: int, resume_ctx: str, jd_topics: list[str],
                  user_id: str | None = None, run_id: str | None = None) -> dict:
    persona = _INTERVIEWER_PERSONA.get(mode, _INTERVIEWER_PERSONA["mixed"])
    prompt = _state_brief(persona, mode, turns, difficulty, qnum, max_q, resume_ctx,
                          jd_topics)
    try:
        out = await ask_json(LLMRequest(
            messages=[LLMMessage("system", ADVANCE_SYSTEM), LLMMessage("user", prompt)],
            temperature=0.5, max_tokens=350),
            user_id=user_id, run_id=run_id, agent="interview", kind="interview_advance")
    except Exception:
        out = {"action": "next_topic", "question": "Could you tell me about another "
               "project relevant to this role?", "topic": "general",
               "difficulty": difficulty, "reasoning": "fallback"}
    return decide_next(out, difficulty=difficulty, qnum=qnum, max_q=max_q, turns=turns)


FINALIZE_SYSTEM = f"""You produce the interview report. JSON only:
{{"dims": {{{", ".join(f'"{d}": 0.0-1.0' for d in DIMENSIONS)}}},
 "overall": 0.0-1.0,
 "what_you_did_well": [""], "what_was_weak": [""], "missing_concepts": [""],
 "better_answers": [{{"question":"","model_answer":""}}],
 "follow_up_questions_to_prepare": [""],
 "recommended_study": [{{"topic":"","why":"","resource_hint":""}}],
 "trajectory_note": "<one sentence on how depth evolved>"}}
Base every judgement strictly on the transcript."""


# The report contract, as data. The reader in `normalize.ts` may only ask for names in this list,
# and `test_interview_finalize_lock` ties every one of them to the prompt below -- a field that
# leaves the prompt has to leave this tuple in the same change, which is what makes the frontend's
# reads checkable at all (`EvaluationItem.summary` is a free `Map<String,Object>`, so no record
# names these keys for it).
FINALIZE_FIELDS = (
    "dims",
    "overall",
    "what_you_did_well",
    "what_was_weak",
    "missing_concepts",
    "better_answers",
    "follow_up_questions_to_prepare",
    "recommended_study",
    "trajectory_note",
)

# ...and the one nested list the report panel renders cards from.
STUDY_ITEM_FIELDS = ("topic", "why", "resource_hint")

# Written by `finalize` itself rather than asked of the model, so it is guaranteed on every report
# -- and it is the key the trajectory fold reads when the row list arrives inside the summary map
# instead of as `EvaluationItem.trajectory`.
FINALIZE_COMPUTED_FIELDS = ("trajectory_detail",)


async def finalize(*, mode: str, turns: list[dict], resume_ctx: str,
                   user_id: str | None = None, run_id: str | None = None) -> dict:
    convo = "\n".join(
        f"{'Q' if t['role']=='interviewer' else 'A'}: {t['content'][:600]}" for t in turns)
    prompt = (f"Mode {mode}. Candidate context (untrusted):\n"
              f"{wrap_untrusted('CTX', resume_ctx[:1500])}\n\nTRANSCRIPT:\n{convo}")
    try:
        out = await ask_json(LLMRequest(
            messages=[LLMMessage("system", FINALIZE_SYSTEM), LLMMessage("user", prompt)],
            temperature=0.2, max_tokens=1600),
            user_id=user_id, run_id=run_id, agent="interview", kind="interview_finalize")
    except Exception:
        out = {}
    out["trajectory_detail"] = _trajectory_detail(turns)
    out.setdefault("dims", {})
    out.setdefault("overall", 0.5)
    return out


def _trajectory_detail(turns: list[dict]) -> list[dict]:
    """Per-turn trajectory the interview report renders (topic/depth/score may be absent
    for a turn that never got a question_meta or evaluation)."""
    return [{"seq": t.get("seq"), "role": t["role"],
             "topic": (t.get("question_meta") or {}).get("topic"),
             "depth": (t.get("question_meta") or {}).get("depth_level"),
             "score": (t.get("evaluation") or {}).get("score")}
            for t in turns]
