"""Epic 345: the timeline's second voice is a grounded story, not a pep talk.

The timeline used to be a correct ledger and a poor story. This module writes one
paragraph over the events' own dates/labels and the verifier keeps it only if it
cites an anchor the events actually carry. These tests hold that discipline.
"""

from __future__ import annotations

import pytest

from app.features import career_narrative as cn


_PAYLOAD = {
    "events": [
        {"at": "2026-11-03", "kind": "application", "title": "applied"},
        {"at": "2026-11-10", "kind": "interview", "title": "rehearsal"},
    ],
    "locale": "en",
}


@pytest.mark.asyncio
async def test_grounded_narrative_passes(monkeypatch):
    async def fake(req, **kw):
        return {"narrative": "The search ran from 2026-11-03 to 2026-11-10, moving from applications to rehearsals."}

    monkeypatch.setattr(cn, "ask_json", fake)
    out = await cn.career_narrative(_PAYLOAD)
    assert "2026-11-03" in out["narrative"]
    assert "2026-11-10" in out["narrative"]


@pytest.mark.asyncio
async def test_ungrounded_narrative_is_dropped(monkeypatch):
    async def fake(req, **kw):
        return {"narrative": "A heroic journey of boundless growth and endless promise."}

    monkeypatch.setattr(cn, "ask_json", fake)
    assert await cn.career_narrative(_PAYLOAD) == {"narrative": None}


@pytest.mark.asyncio
async def test_provider_failure_answers_silent(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("down")

    monkeypatch.setattr(cn, "ask_json", boom)
    assert await cn.career_narrative(_PAYLOAD) == {"narrative": None}


@pytest.mark.asyncio
async def test_zh_locale_is_threaded(monkeypatch):
    seen = {}

    async def fake(req, **kw):
        seen["system"] = req.messages[0].content
        return {"narrative": "2026-11-03"}

    monkeypatch.setattr(cn, "ask_json", fake)
    await cn.career_narrative(_PAYLOAD, locale="zh")
    assert "Chinese" in seen["system"]


def test_digit_helpers():
    # digit_runs splits an ISO date into its components; grounding still holds because
    # each component appears in the payload — a date the payload carries anchors a claim.
    assert {"2026", "11", "03"} <= cn._digit_runs("2026-11-03")
    assert cn._grounded("on 2026-11-03", cn._payload_digits(_PAYLOAD)) is True
    assert cn._grounded("on 1999-01-01", cn._payload_digits(_PAYLOAD)) is False
