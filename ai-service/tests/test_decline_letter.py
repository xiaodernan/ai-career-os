"""Epic 339: the gracious decline.

Same discipline as the shelf letters: digits only from the payload, silence on any failure.
This letter travels to the company — its courtesy must hold to what the reader has actually
seen, never to a script or an invented excuse.
"""
from __future__ import annotations

import pytest

from app.features import decline_letter as letter_mod

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
            "letter": ("Thank you for the offer — and for the care the team showed through the process. "
                       "After careful thought I've decided not to accept this time. "
                       "I have real admiration for Globex and what you're building; "
                       "please keep my door open. Thank you for understanding."),
        }
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.decline_letter(_OFFER, locale="en")
    assert out["letter"] is not None


@pytest.mark.asyncio
async def test_a_letter_citing_only_foreign_digits_is_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": "Thank you, but I will not make it by the April 9, 2024 deadline."}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.decline_letter(_OFFER, locale="en")
    assert out["letter"] is None


@pytest.mark.asyncio
async def test_the_chinese_letter_survives(monkeypatch):
    offer = {**_OFFER, "label": "全栈工程师（Globex，远程）"}

    async def fake_ask_json(req, **kw):
        return {"letter": ("非常感谢贵团队给予的机会，以及流程中每一步的耐心与专业。"
                           "经过慎重考虑，这一次我决定不接受这份 offer。"
                           "我由衷欣赏 Globex 正在做的事情，期待未来还有合作的机会。"
                           "感谢理解。")}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.decline_letter(offer, locale="zh")
    assert out["letter"] is not None


@pytest.mark.asyncio
async def test_relay_failure_answers_a_null_letter(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("relay down")
    monkeypatch.setattr(letter_mod, "ask_json", boom)
    out = await letter_mod.decline_letter(_OFFER, locale="en")
    assert out["letter"] is None


@pytest.mark.asyncio
async def test_an_offer_with_no_anchoring_numbers_answers_null(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": "Hi there."}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.decline_letter({"label": "???"}, locale="en")
    assert out["letter"] is None


@pytest.mark.asyncio
async def test_a_digit_free_letter_needs_no_snapshot_digits(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": ("Thank you for the offer. After thoughtful consideration, "
                           "this is not the right fit for me at this stage. "
                           "I'm grateful for your time and wish the team well.")}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.decline_letter(_OFFER, locale="en")
    assert out["letter"] is not None
