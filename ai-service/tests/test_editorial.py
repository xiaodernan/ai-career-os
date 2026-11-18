"""Epic 322: the weekly letter's editor's note.

Same shape as counsel: one call to the relay, the Graph's verify node keeps only
sentences that cite a digit-run already in the digest payload, silence is the
failure mode. These tests pin the contract that can never ship an invented narrative.
"""
from __future__ import annotations

import pytest

from app.features import editorial as editorial_mod


_PAYLOAD = {
    "signals": ["2 recent applications need a follow-up nudge"],
    "totalApplications": 1,
    "activePipeline": 1,
    "stalledCount": 0,
    "responseRate": 1.0,
    "offerRate": 0.0,
    "windowDays": 7,
}


@pytest.mark.asyncio
async def test_editor_note_grounded_in_snapshot_digits_passes(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"note": "The board holds 1 application, response rate 1.0, stalled 0. Two nudges earn their keep."}
    monkeypatch.setattr(editorial_mod, "ask_json", fake_ask_json)
    out = await editorial_mod.editorial(_PAYLOAD)
    assert out["note"].startswith("The board holds 1 application")


@pytest.mark.asyncio
async def test_invention_with_only_foreign_numbers_is_rejected(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"note": "Your offers rocketed to 85% this week as the recruiter hugged you."}
    monkeypatch.setattr(editorial_mod, "ask_json", fake_ask_json)
    out = await editorial_mod.editorial(_PAYLOAD)
    assert out["note"] is None       # 85% isn't in the payload; the sentence is dropped


@pytest.mark.asyncio
async def test_provider_failure_answers_a_null_note(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("provider down")
    monkeypatch.setattr(editorial_mod, "ask_json", boom)
    out = await editorial_mod.editorial(_PAYLOAD)
    assert out["note"] is None


@pytest.mark.asyncio
async def test_empty_model_output_answers_a_null_note(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {}
    monkeypatch.setattr(editorial_mod, "ask_json", fake_ask_json)
    out = await editorial_mod.editorial(_PAYLOAD)
    assert out["note"] is None


def test_digit_run_parsing_drops_the_percent_sign():
    assert editorial_mod._digit_runs("at 4.2% with 17 and 0.5") == {"4.2", "17", "0.5"}
    assert editorial_mod._digit_runs("event 7") == {"7"}
