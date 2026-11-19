"""Epic 337: the negotiation prep one-pager — the twelve lines the reader carries in.

Same law as the offer-letter trio: every digit-run in the one-pager belongs to the snapshot
or the prep is silence. The note is addressed to the reader, not to the company — the test
keeps that shape in place: sections headed in the reader's language, second person, and
the sibling cards never named as leverage.

Six tests, deliberately: grounded kept, foreign-digit dropped, Chinese kept, relay death
answers null, no-anchor-no-note, silence when the draft is empty.
"""
from __future__ import annotations

import pytest

from app.features import negotiation_prep as prep_mod

_OFFER = {
    "label": "Platform Engineer, Acme (New York)",
    "base": 300000,
    "bonus": 30000,
    "annualEquity": 40000,
    "totalComp": 370000,
    "currency": "USD",
    "remoteType": "hybrid",
    "deadline": "2026-12-01",
    "notes": None,
}

_SIBLINGS = [
    {"label": "Senior Eng, Globex", "totalComp": 400000, "currency": "USD"},
    {"label": "Staff Eng, Initech", "totalComp": 360000, "currency": "USD"},
]

_SECTIONS = ("The anchor read", "The number you own", "The pause", "The floor", "If they pass")


@pytest.mark.asyncio
async def test_a_grounded_prep_is_kept(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"prep": ("The anchor read: 370,000 total in USD, hybrid, deadline 2026-12-01.\n"
                         "The number you own: 300,000 base is the cleanest figure you hold — lead with it.\n"
                         "The pause: walk me through the full package once and tell me how to answer by the deadline.\n"
                         "The floor: keep the same total restructured — a signing piece instead of a base jump.\n"
                         "If they pass: thank the team, take the band you can live with, close the loop cleanly.")}
    monkeypatch.setattr(prep_mod, "ask_json", fake_ask_json)
    out = await prep_mod.negotiation_prep(_OFFER, _SIBLINGS, locale="en")
    assert out["prep"] is not None
    for section in _SECTIONS:
        assert section in out["prep"]


@pytest.mark.asyncio
async def test_a_prep_citing_only_foreign_digits_is_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"prep": ("The anchor read: ask for 500,000 total and a 75,000 sign-on fee.\n"
                         "If they pass: ask again next week for another 25,000.")}
    monkeypatch.setattr(prep_mod, "ask_json", fake_ask_json)
    out = await prep_mod.negotiation_prep(_OFFER, _SIBLINGS, locale="en")
    assert out["prep"] is None


@pytest.mark.asyncio
async def test_the_chinese_prep_survives(monkeypatch):
    offer = {**_OFFER, "label": "平台后端工程师，Acme（上海）"}
    sections = ("锚点解读", "你手里最硬的一位", "缓一缓", "底线", "如果他们拒绝")

    async def fake_ask_json(req, **kw):
        return {"prep": ("锚点解读：总包 370,000（美元岗位），截止日 2026-12-01。\n"
                         "你手里最硬的一位：300,000 的 base 是最干净的数字，从它讲起。\n"
                         "缓一缓：感谢邀约，请给我一周走完材料——按截止日回答。\n"
                         "底线：总包保持不变，把结构再排一遍。\n"
                         "如果他们拒绝：这一轮就按这个数定，关系不坏。")}
    monkeypatch.setattr(prep_mod, "ask_json", fake_ask_json)
    out = await prep_mod.negotiation_prep(offer, _SIBLINGS, locale="zh")
    assert out["prep"] is not None
    for section in sections:
        assert section in out["prep"]


@pytest.mark.asyncio
async def test_relay_failure_answers_a_null_prep(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("relay down")
    monkeypatch.setattr(prep_mod, "ask_json", boom)
    out = await prep_mod.negotiation_prep(_OFFER, _SIBLINGS, locale="en")
    assert out["prep"] is None


@pytest.mark.asyncio
async def test_an_offer_with_no_anchoring_numbers_answers_null(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"prep": "any content at all"}
    monkeypatch.setattr(prep_mod, "ask_json", fake_ask_json)
    out = await prep_mod.negotiation_prep({"label": "?"}, [], locale="en")
    assert out["prep"] is None


@pytest.mark.asyncio
async def test_an_empty_draft_answers_null_without_an_exception(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {}
    monkeypatch.setattr(prep_mod, "ask_json", fake_ask_json)
    out = await prep_mod.negotiation_prep(_OFFER, _SIBLINGS, locale="en")
    assert out["prep"] is None
