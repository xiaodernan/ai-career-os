"""Epic 333: the sendable counter-offer letter.

Same law as the decision letter (Epic 327) and the editors: digits belong to the
snapshot or the letter is silence. This letter is *sent* — it is the one
the reader puts in the outbox. The test keeps the soft-lines separate: a
coherent letter in Chinese survives; a foreign number anywhere drops it.
"""
from __future__ import annotations

import pytest

from app.features import counter_letter as letter_mod

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


@pytest.mark.asyncio
async def test_a_grounded_letter_is_kept(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {
            "letter": ("Hello — coming from the offer conversation: I was hoping we could revisit "
                       "the package. My decision is otherwise ready to make left-to-right. The "
                       "numbers I see on the table: 300,000 base, 30,000 bonus, 40,000 equity, "
                       "total 370,000. Offers I am weighing join at roughly the same USD band, "
                       "closer to the 400,000 side. If we can get to 400,000 total, I am ready "
                       "to sign this week. Five minutes on the phone puts the details to bed."),
        }
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.counter_offer_letter(_OFFER, _SIBLINGS, locale="en")
    assert out["letter"] is not None
    assert "400,000" in out["letter"]


@pytest.mark.asyncio
async def test_a_letter_citing_only_foreign_digits_is_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": "Hello — my anchor is 500,000 base and a 75,000 sign-on."}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.counter_offer_letter(_OFFER, _SIBLINGS, locale="en")
    assert out["letter"] is None


@pytest.mark.asyncio
async def test_the_chinese_letter_survives(monkeypatch):
    offer = {**_OFFER, "label": "平台后端工程师，Acme（上海）",
             "notes": "愿意在这家公司待很久"}
    async def fake_ask_json(req, **kw):
        return {"letter": ("您好，感谢 Acme 的邀约（总包 370,000）。能否把 package 的数字再对齐一下？"
                           "我在和另外两份一起斟酌，同级别的数字都到了 300,000 起步。"
                           "如果可以到 400,000 的总包水平，我这周就能回复您——五分钟电话即可。")}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.counter_offer_letter(offer, _SIBLINGS, locale="zh")
    assert out["letter"] is not None


@pytest.mark.asyncio
async def test_relay_failure_answers_a_null_letter(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("relay down")
    monkeypatch.setattr(letter_mod, "ask_json", boom)
    out = await letter_mod.counter_offer_letter(_OFFER, _SIBLINGS, locale="en")
    assert out["letter"] is None


@pytest.mark.asyncio
async def test_an_offer_with_no_anchoring_numbers_answers_null(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"letter": "any content at all"}
    monkeypatch.setattr(letter_mod, "ask_json", fake_ask_json)
    out = await letter_mod.counter_offer_letter({"label": "?"}, [], locale="en")
    assert out["letter"] is None
