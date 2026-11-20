"""Adaptive interview engine (PRD §13-15).

Dynamic — never a pre-generated question list. Each candidate answer is evaluated,
then the agent decides: drill deeper with a follow-up chain, switch topic, or wrap
up. Difficulty adapts to answer quality; the question/answer tree becomes the
"interview depth trajectory".
"""

import json

from app.agents.stategraph import NodeResult, StateGraph
from app.core.ai import ask, ask_json, stable_messages, wrap_untrusted
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
    rows = [t for t in (turns or []) if isinstance(t, dict)]
    convo = "\n".join(
        f"{'INTERVIEWER' if t.get('role')=='interviewer' else 'CANDIDATE'}: "
        f"{str(t.get('content') or '')[:350]}"
        for t in rows[-10:])
    ctx = resume_ctx if isinstance(resume_ctx, str) else ""
    diff = float(difficulty) if isinstance(difficulty, (int, float)) else 0.0
    return (f"Persona: {persona}\nMode: {mode}\nQuestion {qnum} asked so far / target "
            f"{max_q}. Difficulty now: {diff:.2f}.\n"
            f"Suggested topics: {jd_topics}\nCandidate context:\n"
            f"{wrap_untrusted('CANDIDATE_CONTEXT', ctx[:7500])}\n\nConversation:\n{convo}")


def opening_meta(topic: str) -> dict:
    """The `question_meta` the first turn of a session carries.

    Its own function because that dict is the wire shape -- the backend stores it verbatim into
    `interview_turns.question_meta` -- and the contract gate binds the browser's reads of it to the
    single literal that states it.
    """
    return {"topic": topic, "depth_level": 0, "expected_points": [], "phase": "opening"}


def unwrap_text_envelope(text: str) -> str:
    """Unwrap a JSON envelope some models emit despite a plain-text prompt.

    The opening question is prompted as prose ("one short greeting ... the FIRST
    question only"), and the real relay (gpt-6.1-terra via the current relay) answered it with
    `{"message": "Hi, thanks for joining today. ..."}` -- the turn stored the whole
    envelope as the question text, and the runner rendered raw JSON to the reader.
    A plain-text caller wants the words, not the wrapping. Anything that is not a
    JSON object whose single preferred key holds the text passes through untouched.
    """
    s = text.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return s
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return s
    if not isinstance(obj, dict):
        return s
    for key in ("message", "question", "text", "content", "answer", "reply"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    strings = [v for v in obj.values() if isinstance(v, str) and v.strip()]
    if len(obj) == 1 and len(strings) == 1:
        return strings[0].strip()
    return s


def _clamp01(value, default):
    """Coerce to a float in [0, 1]. Returns (value, dropped): `dropped` counts a value
    the model gave that was unusable (non-number, NaN, ±inf) — the caller decides what
    the default means for its contract."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default, True
    if f != f or f == float("inf") or f == float("-inf"):
        return default, True
    return max(0.0, min(1.0, f)), False


def _string_list(value, *, cap: int, item_chars: int):
    """Coerce to a list of <= `cap` non-blank strings, each trimmed to `item_chars`.
    Returns (items, dropped): a list-typed answer with junk rows drops the junk rows;
    a non-list answer drops to the empty list."""
    if not isinstance(value, list):
        return [], 1 if value is not None else 0
    items: list[str] = []
    dropped = 0
    for it in value:
        if len(items) >= cap:
            dropped += 1
            continue
        if isinstance(it, str) and it.strip():
            items.append(it.strip()[:item_chars])
        else:
            dropped += 1
    return items, dropped


async def opening_question(*, mode: str, company: str, position: str, resume_ctx: str,
                          jd_topics: list[str], candidate_name: str = "",
                          user_id: str | None = None, run_id: str | None = None) -> dict:
    persona = _INTERVIEWER_PERSONA.get(mode, _INTERVIEWER_PERSONA["mixed"])
    prompt = _state_brief(persona, mode, [], 0.5, 0, 8, resume_ctx, jd_topics) + \
        f"\n\nCompany: {company} Position: {position}. Open the interview: one short " \
        f"greeting{' using the name ' + candidate_name if candidate_name else ''}, " \
        "one sentence on format, then the FIRST question only."

    # The opening turn rides the bounded spine too: the model drafts the prose, the
    # verify node undoes the JSON-envelope failure mode the renderer used to ship raw,
    # bounds the length, and replaces an empty answer with a deterministic opening so
    # the session can never dead-end on a blank turn.
    async def _draft(state: dict) -> NodeResult:
        resp = await ask(LLMRequest(
            messages=stable_messages("You conduct realistic mock job interviews. "
                                     "Ask exactly ONE question. Be concise.",
                                     LLMMessage("user", prompt)),
            temperature=0.0, max_tokens=260),
            user_id=user_id, run_id=run_id, agent="interview", kind="interview_open")
        return NodeResult({"raw": resp.text, "model": resp.model}, "verify",
                          trace={"rawChars": len(resp.text or "")})

    async def _verify(state: dict) -> NodeResult:
        raw = str(state.get("raw") or "")
        text = unwrap_text_envelope(raw).strip()
        unwrapped = text != raw.strip()
        truncated = False
        if len(text) > 1200:
            text = text[:1200].rsplit(" ", 1)[0].rstrip()
            truncated = True
        empty = not text
        if empty:
            text = "Could you walk me through your background and why this role?"
        return NodeResult({"question": text}, "render",
                          trace={"unwrapped": unwrapped, "truncated": truncated,
                                 "empty": empty})

    async def _render(state: dict) -> NodeResult:
        topic = (jd_topics or ["background"])[0]
        return NodeResult({"question": state["question"], "meta": opening_meta(topic),
                           "model": state.get("model")}, None)

    graph = StateGraph("draft", {"draft": _draft, "verify": _verify, "render": _render},
                       max_steps=3)
    final = await graph.run({}, run_id=run_id, agent="interview")
    return {"question": final["question"], "meta": final["meta"], "model": final.get("model")}


async def evaluate_answer(*, mode: str, question: str, answer: str, resume_ctx: str,
                          user_id: str | None = None, run_id: str | None = None) -> dict:
    ctx = resume_ctx if isinstance(resume_ctx, str) else ""
    ans = answer if isinstance(answer, str) else ""
    prompt = (f"Interview context (candidate's real background, untrusted):\n"
              f"{wrap_untrusted('CANDIDATE_CONTEXT', ctx[:7500])}\n\n"
              f"QUESTION: {question}\n\nCANDIDATE ANSWER:\n"
              f"{wrap_untrusted('ANSWER', ans[:4000])}")

    # The evaluator rides the bounded spine: the model drafts, the verify node clamps
    # every number into [0, 1], whitelists the dims the prompt promised, drops junk rows
    # honestly counted in the trace — the reader never sees an 88.0 "score".
    async def _draft(state: dict) -> NodeResult:
        try:
            ev = await ask_json(LLMRequest(
                messages=stable_messages(EVAL_SYSTEM, LLMMessage("user", prompt)),
                temperature=0.1, max_tokens=900),
                user_id=user_id, run_id=run_id, agent="interview", kind="answer_eval")
        except Exception:
            ev = {"score": 0.5, "question_was_answered": True}
        if not isinstance(ev, dict):
            ev = {}
        return NodeResult({"model": ev}, "verify",
                          trace={"scoreIsNumber": isinstance(ev.get("score"), (int, float))})

    async def _verify(state: dict) -> NodeResult:
        ev = state.get("model") or {}
        out: dict = {}
        dropped = 0

        score, s_dropped = _clamp01(ev.get("score"), 0.5)
        dropped += int(s_dropped)
        out["score"] = score

        dims = ev.get("dims")
        if isinstance(dims, dict):
            clean: dict[str, float] = {}
            for key in DIMENSIONS[:4]:
                if key not in dims:
                    continue
                f, dd = _clamp01(dims.get(key), 0.0)
                if dd:
                    dropped += 1
                    continue
                clean[key] = f
            # The prompt names exactly four dims; extra keys are dropped, not shipped.
            extra = [k for k in dims if isinstance(k, str) and k not in DIMENSIONS[:4]]
            dropped += len(extra)
            out["dims"] = clean

        for field in ("strengths", "weaknesses", "missing_concepts"):
            items, dd = _string_list(ev.get(field), cap=5, item_chars=200)
            dropped += dd
            out[field] = items

        better = ev.get("better_answer")
        out["better_answer"] = (better.strip()[:600]
                                if isinstance(better, str) else "")
        if better is not None and not isinstance(better, str):
            dropped += 1

        answered = ev.get("question_was_answered")
        if isinstance(answered, bool):
            out["question_was_answered"] = answered
        elif isinstance(answered, str):
            out["question_was_answered"] = answered.strip().lower() in (
                "true", "yes", "1")
        elif isinstance(answered, (int, float)):
            out["question_was_answered"] = bool(answered)
        else:
            out["question_was_answered"] = True

        return NodeResult({"verified": out}, "render",
                          trace={"droppedFields": dropped})

    async def _render(state: dict) -> NodeResult:
        out = dict(state.get("verified") or {})
        out.setdefault("score", 0.5)
        out.setdefault("question_was_answered", True)
        return NodeResult({"result": out}, None)

    graph = StateGraph("draft", {"draft": _draft, "verify": _verify, "render": _render},
                       max_steps=3)
    final = await graph.run({}, run_id=run_id, agent="interview")
    return final["result"]


def decide_next(out: dict, *, difficulty: float, qnum: int, max_q: int,
                turns: list[dict]) -> dict:
    """Coerce the LLM's raw advance output into the session's next-move contract.

    Pure and deterministic (no I/O): the action is whitelisted, the interview is
    force-finished once the question budget is spent, and difficulty is clamped to
    the band the adaptive ladder is designed for. Split out of ``advance`` so the
    decision rule is unit-testable without an LLM.
    """
    out = out if isinstance(out, dict) else {}
    action = out.get("action") if out.get("action") in ("followup", "next_topic",
                                                        "finish") else "next_topic"
    rows = [t for t in (turns or []) if isinstance(t, dict)]
    if qnum >= max_q and action != "finish":
        action = "finish" if rows and rows[-1].get("role") == "candidate" else action
    try:
        d = float(out.get("difficulty", difficulty))
    except (TypeError, ValueError):
        d = difficulty
    d = max(0.1, min(0.95, d))
    question = out.get("question")
    return {"action": action,
            "question": (question if isinstance(question, str) else "").strip(),
            "topic": out.get("topic") or "", "difficulty": d,
            "reasoning": out.get("reasoning", "")}


async def advance(*, mode: str, turns: list[dict], difficulty: float, qnum: int,
                  max_q: int, resume_ctx: str, jd_topics: list[str],
                  user_id: str | None = None, run_id: str | None = None) -> dict:
    persona = _INTERVIEWER_PERSONA.get(mode, _INTERVIEWER_PERSONA["mixed"])
    prompt = _state_brief(persona, mode, turns, difficulty, qnum, max_q, resume_ctx,
                          jd_topics)

    # The interview director rides the bounded spine: the model drafts the move,
    # decide_next is the deterministic verify (action whitelist, budget force-finish,
    # difficulty clamped to the adaptive band), the renderer ships the exact shape
    # the session runner reads.
    async def _draft(state: dict) -> NodeResult:
        try:
            out = await ask_json(LLMRequest(
                messages=stable_messages(ADVANCE_SYSTEM, LLMMessage("user", prompt)),
                temperature=0.5, max_tokens=350),
                user_id=user_id, run_id=run_id, agent="interview",
                kind="interview_advance")
        except Exception:
            out = {"action": "next_topic", "question": "Could you tell me about another "
                   "project relevant to this role?", "topic": "general",
                   "difficulty": difficulty, "reasoning": "fallback"}
        if not isinstance(out, dict):
            out = {}
        return NodeResult({"model": out}, "verify")

    async def _verify(state: dict) -> NodeResult:
        decided = decide_next(state.get("model") or {}, difficulty=difficulty,
                              qnum=qnum, max_q=max_q, turns=turns)
        return NodeResult({"decided": decided}, "render",
                          trace={"action": decided["action"],
                                 "difficulty": decided["difficulty"]})

    async def _render(state: dict) -> NodeResult:
        return NodeResult({"result": state["decided"]}, None)

    graph = StateGraph("draft", {"draft": _draft, "verify": _verify, "render": _render},
                       max_steps=3)
    final = await graph.run({}, run_id=run_id, agent="interview")
    out = final["result"]
    # Rebuild the wire shape explicitly so the response-shape contract gate can read
    # the hop through `advance` and see its nested keys without guessing.
    return {"action": out["action"],
            "question": out["question"],
            "topic": out["topic"],
            "difficulty": out["difficulty"],
            "reasoning": out["reasoning"]}


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

# ...and the pair each stronger answer is written as. Stated as data for the same reason: the
# report's rewrite reader may only ask for names this prompt asks for, and 61.1 is the first
# reader to ask for any of them.
BETTER_ANSWER_FIELDS = ("question", "model_answer")

# Written by `finalize` itself rather than asked of the model, so it is guaranteed on every report
# -- and it is the key the trajectory fold reads when the row list arrives inside the summary map
# instead of as `EvaluationItem.trajectory`.
FINALIZE_COMPUTED_FIELDS = ("trajectory_detail",)


async def finalize(*, mode: str, turns: list[dict], resume_ctx: str,
                   user_id: str | None = None, run_id: str | None = None) -> dict:
    rows = [t for t in (turns or []) if isinstance(t, dict)]
    convo = "\n".join(
        f"{'Q' if t.get('role')=='interviewer' else 'A'}: "
        f"{str(t.get('content') or '')[:600]}"
        for t in rows)
    ctx = resume_ctx if isinstance(resume_ctx, str) else ""
    prompt = (f"Mode {mode}. Candidate context (untrusted):\n"
              f"{wrap_untrusted('CTX', ctx[:7500])}\n\nTRANSCRIPT:\n{convo}")

    # The report rides the bounded StateGraph (Epic 302) — retrieve-shaped: the model drafts,
    # the graph bounds, the renderer lands. Verify is deterministic by design: everything the
    # reader sees must hold promises the prompt gave, and no promise else.
    async def _draft(state: dict) -> NodeResult:
        try:
            out = await ask_json(LLMRequest(
                messages=stable_messages(FINALIZE_SYSTEM, LLMMessage("user", prompt)),
                temperature=0.2, max_tokens=1600),
                user_id=user_id, run_id=run_id, agent="interview",
                kind="interview_finalize")
        except Exception:
            out = {}
        if not isinstance(out, dict):
            out = {}
        return NodeResult({"draft": out}, "verify", trace={"modelReturnedDims": bool(out.get("dims"))})

    async def _verify(state: dict) -> NodeResult:
        draft = state.get("draft") or {}
        dims = draft.get("dims") if isinstance(draft.get("dims"), dict) else {}
        # The reader promises scores in [0, 1] for every dimension; the model did not always
        # hold that (88.0 reads like a report and is a bug). Every dimension is coerced, kept
        # only when it is a real number, clamped otherwise — never dropped into the UI.
        clean: dict[str, float] = {}
        dropped = 0
        for key, value in dims.items():
            if not isinstance(key, str) or not key:
                dropped += 1
                continue
            try:
                f = float(value)
            except (TypeError, ValueError):
                dropped += 1
                continue
            if f != f or f == float("inf") or f == float("-inf"):
                dropped += 1
                continue
            clean[key[:64]] = max(0.0, min(1.0, f))
        # Overall follows the same rule: keep the model's number when it is legally bounded,
        # clamp it into the band when it is not — never invent one from thin air.
        overall = draft.get("overall")
        try:
            overall_f = float(overall) if overall is not None else None
        except (TypeError, ValueError):
            overall_f = None
        if overall_f is None or overall_f != overall_f:
            overall_f = 0.5
        overall_f = max(0.0, min(1.0, overall_f))
        return NodeResult(
            {"verified": {**draft, "dims": clean, "overall": overall_f}},
            "render",
            trace={"droppedDimensions": dropped},
        )

    async def _render(state: dict) -> NodeResult:
        out = dict(state.get("verified") or {})
        out["dims"] = out.get("dims") or {}
        out["overall"] = out.get("overall") if out.get("overall") is not None else 0.5
        out["trajectory_detail"] = _trajectory_detail(turns)
        return NodeResult({"result": out}, None, trace={})

    graph = StateGraph("draft", {"draft": _draft, "verify": _verify, "render": _render},
                       max_steps=4)
    final = await graph.run({"mode": mode, "turns": rows, "convo": convo, "resume_ctx": ctx},
                            run_id=run_id, agent="interview")
    return final["result"]


def _trajectory_detail(turns: list[dict]) -> list[dict]:
    """Per-turn trajectory the interview report renders (topic/depth/score may be absent
    for a turn that never got a question_meta or evaluation)."""
    rows: list[dict] = []
    for t in turns or []:
        if not isinstance(t, dict):
            continue
        meta = t.get("question_meta")
        meta = meta if isinstance(meta, dict) else {}
        ev = t.get("evaluation")
        ev = ev if isinstance(ev, dict) else {}
        rows.append({"seq": t.get("seq"), "role": t.get("role"),
                     "topic": meta.get("topic"),
                     "depth": meta.get("depth_level"),
                     "score": ev.get("score")})
    return rows
