"""Epic 335: the acceptance playbook.

Same discipline: every digit-run in the playbook must appear in the snapshot; silence on any failure.
The moment is fragile — this is the one output the reader might hand to HR — so the verifier is strict.
"""
from __future__ import annotations

import pytest

from app.features import acceptance_playbook as playbook_mod

_OFFER = {
    "label": "Senior Engineer, Globex (remote)",
    "base": 360000,
    "bonus": 50000,
    "annualEquity": 80000,
    "totalComp": 490000,
    "currency": "USD",
    "remoteType": "remote",
    "deadline": "2026-12-01",
    "notes": "peer team is customer-engagements; bisemantic interview loop went well",
}


@pytest.mark.asyncio
async def test_a_grounded_playbook_is_kept(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {
            "playbook": ("Day 1: show up prepared — read the full offer again (360,000 base, 50,000 bonus, "
                         "80,000 equity). Day 30: ship the first small thing the customer reaches. "
                         "Day 60: close the feedback loop from your manager — what does your manager see? "
                         "Day 90: you are a contributor now; the only review left is your own."),
        }
    monkeypatch.setattr(playbook_mod, "ask_json", fake_ask_json)
    out = await playbook_mod.acceptance_playbook(_OFFER, locale="en")
    assert out["playbook"] is not None
    assert "Day 1" in out["playbook"]


@pytest.mark.asyncio
async def test_a_playbook_citing_foreign_digits_is_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"playbook": "Day 1: read all 123456 documents you hold."}
    monkeypatch.setattr(playbook_mod, "ask_json", fake_ask_json)
    out = await playbook_mod.acceptance_playbook(_OFFER, locale="en")
    assert out["playbook"] is None


@pytest.mark.asyncio
async def test_the_chinese_playbook_survives(monkeypatch):
    offer = {**_OFFER, "label": "高级工程师，Globex（远程）"}

    async def fake_ask_json(req, **kw):
        return {"playbook": ("第1天：新 offer 数字再读一遍——360,000 基本，50,000 奖金，80,000 期权。\n"
                             "第30天：交给客户看的第一件小交付——一个小而亮的东西。\n"
                             "第60天：来自你的 manager 的反馈闭环——他看到什么？\n"
                             "第90天：你是正式贡献者了。剩下的是你自己的 Review。")}
    monkeypatch.setattr(playbook_mod, "ask_json", fake_ask_json)
    out = await playbook_mod.acceptance_playbook(offer, locale="zh")
    assert out["playbook"] is not None


@pytest.mark.asyncio
async def test_relay_failure_answers_a_null_playbook(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("relay down")
    monkeypatch.setattr(playbook_mod, "ask_json", boom)
    out = await playbook_mod.acceptance_playbook(_OFFER, locale="en")
    assert out["playbook"] is None


@pytest.mark.asyncio
async def test_an_offer_with_no_anchoring_numbers_answers_null(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"playbook": "Anything"}
    monkeypatch.setattr(playbook_mod, "ask_json", fake_ask_json)
    out = await playbook_mod.acceptance_playbook({"label": "?"}, locale="en")
    assert out["playbook"] is None
