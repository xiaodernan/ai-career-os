"""Epic 313: the interview's three decision calls ride the bounded StateGraph.

`opening_question`, `evaluate_answer` and `advance` used to be bare LLM calls
wearing a defensive parse. They now ride the same draft -> verify -> render
spine `finalize` got in Epic 302, with verifies that are deterministic on
purpose: clamp into the band the reader expects, drop what the prompt never
promised, and keep a playable fallback when the provider fails. These tests
pin exactly those guarantees, hostile model output and provider failure
included.
"""

import math

import pytest

from app.features import interview
from app.features.interview import advance, evaluate_answer, opening_question


# ---------------- opening_question ----------------


@pytest.mark.asyncio
async def test_opening_question_unwraps_the_json_envelope(monkeypatch):
    async def fake_ask(req, **kw):
        class R:
            text = '{"message": "Hi! Tell me about yourself."}'
            model = "m-open"
        return R()
    monkeypatch.setattr("app.features.interview.ask", fake_ask)
    out = await opening_question(mode="mixed", company="Indira", position="SE",
                                 resume_ctx="ctx", jd_topics=["postgres"])
    assert out["question"] == "Hi! Tell me about yourself."
    assert out["meta"]["topic"] == "postgres"
    assert out["model"] == "m-open"


@pytest.mark.asyncio
async def test_opening_question_empty_response_keeps_the_session_playable(monkeypatch):
    async def fake_ask(req, **kw):
        class R:
            text = ""
            model = "m-open"
        return R()
    monkeypatch.setattr("app.features.interview.ask", fake_ask)
    out = await opening_question(mode="mixed", company="Indira", position="SE",
                                 resume_ctx="ctx", jd_topics=["postgres"])
    assert out["question"] == "Could you walk me through your background and why this role?"


@pytest.mark.asyncio
async def test_opening_question_overlong_prose_is_bounded(monkeypatch):
    async def fake_ask(req, **kw):
        class R:
            text = "word " * 400
            model = "m-open"
        return R()
    monkeypatch.setattr("app.features.interview.ask", fake_ask)
    out = await opening_question(mode="mixed", company="Indira", position="SE",
                                 resume_ctx="ctx", jd_topics=["postgres"])
    assert len(out["question"]) <= 1200


# ---------------- evaluate_answer ----------------


@pytest.mark.asyncio
async def test_answer_eval_clamps_percent_score_into_the_band(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"score": 88.0,
                "dims": {"technical_accuracy": 0.7, "communication": "high",
                         "depth": math.nan, "structure": 0.15, "timeline": 0.9},
                "strengths": ["  clear  ", "", 42],
                "weaknesses": "not a list",
                "missing_concepts": ["idempotency"] * 8,
                "better_answer": " x " * 400,
                "question_was_answered": "yes"}
    monkeypatch.setattr("app.features.interview.ask_json", fake_ask_json)
    out = await evaluate_answer(mode="mixed", question="q", answer="a", resume_ctx="ctx")
    assert out["score"] == 1.0                      # 88 clamps, never ships as 88
    assert out["dims"] == {"technical_accuracy": 0.7, "structure": 0.15}
    assert out["strengths"] == ["clear"]            # blanks and non-strings dropped
    assert out["weaknesses"] == []                  # non-list drops
    assert out["missing_concepts"] == ["idempotency"] * 5   # capped at 5
    assert len(out["better_answer"]) <= 600
    assert out["question_was_answered"] is True


@pytest.mark.asyncio
async def test_answer_eval_survives_provider_failure(monkeypatch):
    async def fake_ask_json(req, **kw):
        raise RuntimeError("provider down")
    monkeypatch.setattr("app.features.interview.ask_json", fake_ask_json)
    out = await evaluate_answer(mode="mixed", question="q", answer="a", resume_ctx="ctx")
    assert out["score"] == 0.5
    assert out["question_was_answered"] is True


@pytest.mark.asyncio
async def test_answer_eval_nan_and_false_are_honest(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"score": math.nan, "dims": {"depth": math.inf},
                "question_was_answered": False}
    monkeypatch.setattr("app.features.interview.ask_json", fake_ask_json)
    out = await evaluate_answer(mode="mixed", question="q", answer="a", resume_ctx="ctx")
    assert out["score"] == 0.5
    assert out["dims"] == {}
    assert out["question_was_answered"] is False


@pytest.mark.asyncio
async def test_answer_eval_non_dict_model_answer_keeps_the_floor(monkeypatch):
    async def fake_ask_json(req, **kw):
        return ["nope"]
    monkeypatch.setattr("app.features.interview.ask_json", fake_ask_json)
    out = await evaluate_answer(mode="mixed", question="q", answer="a", resume_ctx="ctx")
    assert out["score"] == 0.5
    assert out["question_was_answered"] is True


# ---------------- advance ----------------


@pytest.mark.asyncio
async def test_advance_whitelist_difficulty_and_budget_force_finish(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"action": "panic", "question": "  follow up?  ",
                "topic": "db", "difficulty": 99.0, "reasoning": "hot"}
    monkeypatch.setattr("app.features.interview.ask_json", fake_ask_json)
    out = await advance(mode="mixed", turns=[], difficulty=0.5, qnum=0, max_q=8,
                        resume_ctx="ctx", jd_topics=["postgres"])
    assert out["action"] == "next_topic"    # not whitelisted -> next_topic
    assert out["difficulty"] == 0.95        # clamped into the band
    assert out["question"] == "follow up?"  # trimmed, never raw


@pytest.mark.asyncio
async def test_advance_budget_spend_force_finishes(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"action": "followup", "question": "why?", "difficulty": 0.5}
    monkeypatch.setattr("app.features.interview.ask_json", fake_ask_json)
    turns = [{"role": "interviewer", "content": "q"}, {"role": "candidate", "content": "a"}]
    out = await advance(mode="mixed", turns=turns, difficulty=0.5, qnum=8, max_q=8,
                        resume_ctx="ctx", jd_topics=["postgres"])
    assert out["action"] == "finish"


@pytest.mark.asyncio
async def test_advance_provider_failure_keeps_the_default_question(monkeypatch):
    async def fake_ask_json(req, **kw):
        raise RuntimeError("provider down")
    monkeypatch.setattr("app.features.interview.ask_json", fake_ask_json)
    out = await advance(mode="mixed", turns=[], difficulty=0.5, qnum=0, max_q=8,
                        resume_ctx="ctx", jd_topics=["postgres"])
    assert out["action"] == "next_topic"
    assert out["topic"] == "general"
    assert out["reasoning"] == "fallback"
