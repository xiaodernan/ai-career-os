"""Epic 336: the thank-you letter sent after an interview.

Same discipline: digits in the letter must all trace back to the snapshot; silence on
any failure. The letter travels straight into the outbox — a wrong detail costs the
candidate the room they believed they were in.
"""
from __future__ import annotations

import pytest

from app.features import thank_you_letter as letter_mod

_PAYLOAD = {
    "role": "Staff Backend Engineer, Platform",
    "company": "Acme — payroll unit",
    "turns": [
        {"role": "interviewer", "content": "Walk me through how you debug a production incident in your current system."},
        {"role": "candidate", "content": "First I alert paging, freeze deploys, then read the last deploy log and the business error rate. I once debugged a 503 spike in 40 minutes."},
        {"role": "interviewer", "content": "How do you decide between fixing and rolling back?"},
        {"role": "candidate", "content": "If more users are blocked than the change fixes, rollback; otherwise iterate in place. Recently rolling back took the error rate to zero."},
        {"role": "interviewer", "content": "What do you want to learn in the next six months?"},
        {"role": "candidate", "content": "Distributed tracing — I keep seeing gaps in observability tooling."},
    ],
}


@pytest.mark.asyncio
async def test_a_grounded_letter_is_kept(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {
            "letter": ("Hi — thank you for the interview. Walking through the 40-minute production"
                       " incident debug was the part of the conversation that told me the most about this team."
                       " I'd be glad to join the payroll unit. The distributed-tracing question is where I"
                       " hope to grow in the next six months. Whenever you'd like to talk next, I'm ready."
                       " Best, your interviewer's next candidate."),
        }
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.thank_you_letter(_PAYLOAD, locale="en")
    assert out["letter"] is not None


@pytest.mark.asyncio
async def test_a_letter_citing_foreign_digits_is_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": "Hi — I want to thank you for the 7 questions. Looking forward to hearing back on 03/14."}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.thank_you_letter(_PAYLOAD, locale="en")
    assert out["letter"] is None


@pytest.mark.asyncio
async def test_the_chinese_letter_survives(monkeypatch):
    payload = dict(_PAYLOAD)
    payload["company"] = "Acme · 薪资核算组"
    async def fake_ask_json(req, **kw):
        return {"letter": ("您好，谢谢您今天安排的交流。生产环境事故排查那个环节，是我最感兴趣的，"
                          "团队处理 503 激增的思路也给我留下了印象。下一六个月我希望去补强分布式追踪"
                          "能力。我这周随时可以对话。期待您的回复。")}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.thank_you_letter(payload, locale="zh")
    assert out["letter"] is not None


@pytest.mark.asyncio
async def test_relay_failure_answers_a_null_letter(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("relay down")
    monkeypatch.setattr(letter_mod, "ask_json", boom)
    out = await letter_mod.thank_you_letter(_PAYLOAD, locale="en")
    assert out["letter"] is None


@pytest.mark.asyncio
async def test_no_turns_at_all_answers_null(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": "Anything."}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.thank_you_letter({"role": "x", "company": "y", "turns": []}, locale="en")
    assert out["letter"] is None
