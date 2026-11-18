"""Epic 332: the inbox analyst.

The words settle the intent when they can — a letter that says "unfortunately" is a
rejection no matter what the model wrote; the model reads only what the rules
leave open. Everything else obeys the same law as the other editors: digits come
from the message or the field is dropped; silence on any failure.
"""
from __future__ import annotations

import pytest

from app.features import reply_decode as decode_mod

_BODY = {
    "subject": "Your application — next steps",
    "body": ("Hi Ada, thanks for applying to the Platform role. We would like to move forward "
              "to a technical interview. Could you let us know your availability this week, "
              "and confirm the date of 2026-11-27 works? 2 stages, about 90 minutes total."),
}


@pytest.mark.asyncio
async def test_a_grounded_decode_is_kept(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {
            "intent": "interview",
            "deadline": "2026-11-27",
            "next_action": "Reply with availability and confirm 2026-11-27 works for a 90 minute interview in 2 stages.",
            "asks": ["Confirm availability this week", "Confirm 2026-11-27 works"],
            "reply": "Hi, yes — 2026-11-27 works for a 90 minute interview in 2 stages. Looking forward to it!",
        }
    monkeypatch.setattr(decode_mod, "ask_json", fake_ask_json)
    out = await decode_mod.decode_reply(_BODY, locale="en")
    d = out["decode"]
    assert d is not None
    assert d["intent"] == "interview"
    assert d["deadline"] == "2026-11-27"
    assert d["next_action"]


@pytest.mark.asyncio
async def test_a_rejection_stays_a_rejection_even_if_the_model_dreams(monkeypatch):
    letter = {
        "subject": "Update",
        "body": "Thank you for interviewing. Unfortunately, we cannot offer you the position this time and will not proceed further.",
    }
    async def fake_ask_json(req, **kw):
        return {"intent": "offer", "deadline": None,
                "next_action": "Wait for our records review.",
                "asks": [], "reply": "Thank you for the chance to interview."}
    monkeypatch.setattr(decode_mod, "ask_json", fake_ask_json)
    out = await decode_mod.decode_reply(letter, locale="en")
    assert out["decode"]["intent"] == "rejection"


@pytest.mark.asyncio
async def test_foreign_digits_in_the_ask_drop_the_ask_not_the_decode(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {
            "intent": "interview",
            "deadline": "2026-11-27",
            "next_action": "Reply with availability.",
            "asks": ["Confirm 2026-11-27", "Send 47 letters of recommendation"],
            "reply": "Happy to confirm 2026-11-27.",
        }
    monkeypatch.setattr(decode_mod, "ask_json", fake_ask_json)
    out = await decode_mod.decode_reply(_BODY, locale="en")
    asks = out["decode"]["asks"]
    assert "Send 47 letters of recommendation" not in asks
    assert "Confirm 2026-11-27" in asks


@pytest.mark.asyncio
async def test_a_foreign_deadline_is_not_invented(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {
            "intent": "interview",
            "deadline": "2027-03-01",
            "next_action": "Reply with availability.",
            "asks": [], "reply": "Thank you for the update.",
        }
    monkeypatch.setattr(decode_mod, "ask_json", fake_ask_json)
    out = await decode_mod.decode_reply(_BODY, locale="en")
    assert out["decode"]["deadline"] is None
    assert out["decode"]["next_action"] == "Reply with availability."


@pytest.mark.asyncio
async def test_foreign_digits_in_next_action_answer_null(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"intent": "info", "deadline": None,
                "next_action": "Bring 3 portfolios to the meeting.",
                "asks": [], "reply": "Will do."}
    monkeypatch.setattr(decode_mod, "ask_json", fake_ask_json)
    out = await decode_mod.decode_reply(_BODY, locale="en")
    assert out["decode"] is None


@pytest.mark.asyncio
async def test_a_chinese_decode_survives(monkeypatch):
    letter = {"subject": "关于您的申请——下一步",
              "body": "您好，感谢您申请平台研发岗位。我们希望安排一次技术面试，可否告知您2026-11-27是否方便？共2轮，大约90分钟。"}
    async def fake_ask_json(req, **kw):
        return {"intent": "interview", "deadline": "2026-11-27",
                "next_action": "确认2026-11-27是否方便，参加2轮、约90分钟的技术面试。",
                "asks": ["确认2026-11-27是否方便"],
                "reply": "您好，2026-11-27方便，我会参加2轮、约90分钟的面试。期待与您交流。"}
    monkeypatch.setattr(decode_mod, "ask_json", fake_ask_json)
    out = await decode_mod.decode_reply(letter, locale="zh")
    assert out["decode"] is not None
    assert out["decode"]["deadline"] == "2026-11-27"


@pytest.mark.asyncio
async def test_a_reply_with_invented_digits_is_dropped_but_the_parse_survives(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"intent": "info", "deadline": None,
                "next_action": "Wait for their update.",
                "asks": [],
                "reply": "Thank you for the update — I have 9 referees ready to go."}
    monkeypatch.setattr(decode_mod, "ask_json", fake_ask_json)
    out = await decode_mod.decode_reply(_BODY, locale="en")
    assert out["decode"] is not None
    assert out["decode"]["reply"] is None
    assert out["decode"]["next_action"] == "Wait for their update."


@pytest.mark.asyncio
async def test_relay_failure_answers_a_null_decode(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("relay down")
    monkeypatch.setattr(decode_mod, "ask_json", boom)
    out = await decode_mod.decode_reply(_BODY, locale="en")
    assert out["decode"] is None


@pytest.mark.asyncio
async def test_a_body_too_short_to_read_answers_null(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"intent": "info", "deadline": None, "next_action": "x", "asks": [], "reply": None}
    monkeypatch.setattr(decode_mod, "ask_json", fake_ask_json)
    out = await decode_mod.decode_reply({"subject": "hi", "body": "ok."}, locale="en")
    assert out["decode"] is None
