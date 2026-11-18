"""Epic 331: the assistant's one proactive first step.

Same discipline as the editors: the model may cite only digits already in the
payload; silence on any failure; locale-aware.
"""
from __future__ import annotations

import pytest

from app.features import proactive_step as step_mod


_PAYLOAD = {
    "totalApplications": 23,
    "attentionCount": 4,
    "reminderDue": 1,
    "staleCount": 3,
    "interviewsStartedLast7Days": 2,
    "offersPending": 0,
}


@pytest.mark.asyncio
async def test_a_grounded_step_is_kept(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"step": "Knock out the 1 due reminder first; the 3 sleepiest applications will keep for tomorrow."}
    monkeypatch.setattr(step_mod, "ask_json", fake_ask_json)
    out = await step_mod.proactive_step(_PAYLOAD, locale="en")
    assert out["step"].startswith("Knock out")


@pytest.mark.asyncio
async def test_a_step_citing_only_foreign_digits_is_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"step": "Buy the 11 cert, ping 55 recruiters, and apply tomorrow."}
    monkeypatch.setattr(step_mod, "ask_json", fake_ask_json)
    out = await step_mod.proactive_step(_PAYLOAD, locale="en")
    assert out["step"] is None


@pytest.mark.asyncio
async def test_the_chinese_step_survives_to_the_client(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"step": "先处理那 1 个到期的提醒，再挑 3 个最久没动的投递补一封信——今天这两件顶一切。"}
    monkeypatch.setattr(step_mod, "ask_json", fake_ask_json)
    out = await step_mod.proactive_step(_PAYLOAD, locale="zh")
    assert out["step"] is not None


@pytest.mark.asyncio
async def test_a_zero_workspace_produces_an_honest_first_move(monkeypatch):
    zero = {k: 0 for k in _PAYLOAD}
    async def fake_ask_json(req, **kw):
        return {"step": "当前收到 0 份投递——先建立第一份简历并完成第一次投递，今天就走完第一步。"}
    monkeypatch.setattr(step_mod, "ask_json", fake_ask_json)
    out = await step_mod.proactive_step(zero, locale="zh")
    assert out["step"] is not None


@pytest.mark.asyncio
async def test_relay_failure_answers_a_null_step(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("relay down")
    monkeypatch.setattr(step_mod, "ask_json", boom)
    out = await step_mod.proactive_step(_PAYLOAD, locale="en")
    assert out["step"] is None
