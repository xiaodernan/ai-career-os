"""Epic 344: the resume first-impression is a grounded second voice, not a pep talk.

The reader's first value page used to be a bare score and five bars. This module
writes one paragraph over the resume's own facts, and the verifier keeps it only if
it cites a number the payload actually carries. These tests hold that discipline.
"""

from __future__ import annotations

import pytest

from app.features import resume_impression as ri


_PAYLOAD = {
    "profile": {"years_experience": 5, "skills_count": 12},
    "experience": [{"count": 3}],
    "projects": [{"count": 2}],
    "score": {"total": 78},
    "locale": "en",
}


@pytest.mark.asyncio
async def test_grounded_impression_passes(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"impression": "Five years across three roles and two projects, with twelve skills and a 78 rubric score."}

    monkeypatch.setattr(ri, "ask_json", fake_ask_json)
    out = await ri.resume_impression(_PAYLOAD)
    assert "Five years" in out["impression"]
    assert "78" in out["impression"]


@pytest.mark.asyncio
async def test_ungrounded_impression_is_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"impression": "A truly exceptional engineer with boundless potential and a brilliant future ahead."}

    monkeypatch.setattr(ri, "ask_json", fake_ask_json)
    out = await ri.resume_impression(_PAYLOAD)
    assert out["impression"] is None


@pytest.mark.asyncio
async def test_provider_failure_answers_silent(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("down")

    monkeypatch.setattr(ri, "ask_json", boom)
    assert await ri.resume_impression(_PAYLOAD) == {"impression": None}


@pytest.mark.asyncio
async def test_zh_locale_is_threaded(monkeypatch):
    seen = {}

    async def fake_ask_json(req, **kw):
        seen["system"] = req.messages[0].content
        return {"impression": "5"}

    monkeypatch.setattr(ri, "ask_json", fake_ask_json)
    await ri.resume_impression(_PAYLOAD, locale="zh")
    assert "Chinese" in seen["system"]


def test_digit_runs_helpers():
    assert "5" in ri._digit_runs("5 years")
    assert ri._grounded("score 78", ri._payload_digits(_PAYLOAD)) is True
    assert ri._grounded("score 999", ri._payload_digits(_PAYLOAD)) is False
