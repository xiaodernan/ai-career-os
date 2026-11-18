"""Epic 327: the decision letter — the offer you passed on, addressed to yourself.

Same discipline as the editors: the model may cite only digits in the payload,
no invented people or places, silence on any failure. The letter is a keepsake.
"""
from __future__ import annotations

import pytest

from app.features import offer_letter as letter_mod


_PAYLOAD = {
    "label": "云帆",
    "base": 340000, "bonus": 20000, "annualEquity": 0,
    "totalComp": 360000, "currency": "CNY", "remoteType": "hybrid",
    "deadline": "2026-12-01", "decision": "declined",
    "notes": "the call felt off, not the offer",
}
_SIBS = [
    {"label": "星海云", "totalComp": 337100, "currency": "CNY"},
    {"label": "云帆", "totalComp": 360000, "currency": "CNY"},
]


@pytest.mark.asyncio
async def test_the_grounded_letter_is_kept(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": "你没选 360000 的云帆，因为那通电话让你知道自己先要什么。下一次再遇到 340000 的底薪，你会快 10 秒钟看清这件事。"}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.letter(_PAYLOAD, _SIBS, locale="zh")
    assert out["letter"].startswith("你没选")


@pytest.mark.asyncio
async def test_a_letter_citing_only_foreign_digits_is_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": "By 2028 this turns into $1.2 million and a corner office."}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.letter(_PAYLOAD, [], locale="en")
    assert out["letter"] is None


@pytest.mark.asyncio
async def test_relay_failure_answers_a_null_letter(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("relay down")
    monkeypatch.setattr(letter_mod, "ask_json", boom)
    out = await letter_mod.letter(_PAYLOAD, [], locale="en")
    assert out["letter"] is None


@pytest.mark.asyncio
async def test_english_letter_channel_works(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": "You passed on 360000 because your bar is higher than the number; 340000 minus 20000 was never the question."}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.letter(_PAYLOAD, [], locale="en")
    assert out["letter"] is not None
