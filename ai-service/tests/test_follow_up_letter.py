"""Epic 334: the stalled-offer check-in letter.

Same discipline: digits only from the payload, silence on any failure. This letter travels
into the outbox — its tone must hold to what the reader has actually seen, not to a script.
"""
from __future__ import annotations

import pytest

from app.features import follow_up_letter as letter_mod

_OFFER = {
    "label": "Staff Engineer, Globex (remote)",
    "base": 340000,
    "bonus": 40000,
    "annualEquity": 60000,
    "totalComp": 440000,
    "currency": "USD",
    "remoteType": "remote",
    "deadline": "2026-12-15",
    "notes": "panel loop went well; awaiting verdict",
}


@pytest.mark.asyncio
async def test_a_grounded_letter_is_kept(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {
            "letter": ("Hello — following up on the offer conversation; the deadline you gave was 2026-12-15. "
                       "I'm still interested in the package: 340,000 base, 40,000 bonus, 60,000 equity — 440,000 total. "
                       "If it helps, I'm ready to sign this week. What's the next date on your side?"),
        }
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.follow_up_letter(_OFFER, locale="en")
    assert out["letter"] is not None


@pytest.mark.asyncio
async def test_a_letter_citing_only_foreign_digits_is_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": "Hello — following up on your timeline of April 9, 2024."}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.follow_up_letter(_OFFER, locale="en")
    assert out["letter"] is None


@pytest.mark.asyncio
async def test_the_chinese_letter_survives(monkeypatch):
    offer = {**_OFFER, "label": "高级工程师，Globex（远程）"}
    async def fake_ask_json(req, **kw):
        return {"letter": ("您好，我想跟进一下您上周发来的要约（总包 440,000 USD）。"
                           "如果您这边正在准备，我想知道接下来是否有确定的时间节点——"
                           "我这周可以随时签约。感谢。")}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.follow_up_letter(offer, locale="zh")
    assert out["letter"] is not None


@pytest.mark.asyncio
async def test_relay_failure_answers_a_null_letter(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("relay down")
    monkeypatch.setattr(letter_mod, "ask_json", boom)
    out = await letter_mod.follow_up_letter(_OFFER, locale="en")
    assert out["letter"] is None


@pytest.mark.asyncio
async def test_an_offer_with_no_anchoring_numbers_answers_null(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": "Hi there."}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.follow_up_letter({"label": "???"}, locale="en")
    assert out["letter"] is None
