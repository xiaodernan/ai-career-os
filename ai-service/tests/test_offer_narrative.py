"""Epic 323: the offer decision's grounded narrative.

Same discipline as the Monday letter's editor and the overseer's counsel: the
model may speak only about digits that exist in the comparison snapshot, silence
on any failure, locale-aware. The ranking itself is untouched — the engine owns
the arithmetic.
"""
from __future__ import annotations

import pytest

from app.features import offer_narrative as narrate_mod


_PAYLOAD = {
    "currency": "CNY",
    "sampleSize": 41,
    "offers": [{"label": "A", "base": 280000, "bonus": 40000, "firstYearCash": 320000,
                "annualEquity": 60000, "totalComp": 380000,
                "assessment": {"verdict": "above_market", "vsP50Pct": 32.0, "toP50": 0, "toP75": 0},
                "leverage": "strong"},
               {"label": "B", "base": 340000, "bonus": 20000, "firstYearCash": 360000,
                "annualEquity": 0, "totalComp": 360000,
                "assessment": {"verdict": "within_market", "vsP50Pct": 44.0, "toP50": 0, "toP75": 0},
                "leverage": "moderate"}],
    "bestByComp": "A",
    "notes": ["Above the market band: A", "Highest total comp: A."],
}


@pytest.mark.asyncio
async def test_the_grounded_narrative_is_kept(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"narrative": "Offer A leads on total comp: 380000 against 360000 — the 60000 of annualized equity is the whole gap."}
    monkeypatch.setattr(narrate_mod, "ask_json", fake_ask_json)
    out = await narrate_mod.narrate(_PAYLOAD)
    assert out["narrative"].startswith("Offer A leads")


@pytest.mark.asyncio
async def test_a_narrative_citing_only_foreign_digits_is_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"narrative": "Offer A will 2.5x you out in the IPO next spring for $9 million."}
    monkeypatch.setattr(narrate_mod, "ask_json", fake_ask_json)
    out = await narrate_mod.narrate(_PAYLOAD)
    assert out["narrative"] is None


@pytest.mark.asyncio
async def test_a_chinese_narrative_is_supported(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"narrative": "A 的总包 380000 高于 B 的 360000，差距全在 60000 的年度股权上。"}
    monkeypatch.setattr(narrate_mod, "ask_json", fake_ask_json)
    out = await narrate_mod.narrate(_PAYLOAD, locale="zh")
    assert out["narrative"] is not None
    assert "380000" in out["narrative"]


@pytest.mark.asyncio
async def test_relay_failure_answers_a_null_narrative(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("relay down")
    monkeypatch.setattr(narrate_mod, "ask_json", boom)
    out = await narrate_mod.narrate(_PAYLOAD)
    assert out["narrative"] is None


@pytest.mark.asyncio
async def test_provider_returning_no_object_answers_a_null_narrative(monkeypatch):
    async def fake_ask_json(req, **kw):
        return []
    monkeypatch.setattr(narrate_mod, "ask_json", fake_ask_json)
    out = await narrate_mod.narrate(_PAYLOAD)
    assert out["narrative"] is None
