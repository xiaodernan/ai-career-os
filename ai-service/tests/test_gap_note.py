"""Epic 329: the gap analyst's voice.

Same discipline as the editors: the model may cite only digits already in the
payload, silence on any failure, locale-aware. The engine's ranking is untouched.
"""
from __future__ import annotations

import pytest

from app.features import gap_note as note_mod


_PAYLOAD = {
    "targetRole": "Backend Engineer",
    "seniority": "senior",
    "expectedSkillCount": 12,
    "coveredCount": 6,
    "partialCount": 1,
    "gapCount": 5,
    "coverage": 0.54,
    "gaps": [
        {"skill": "Kubernetes", "importance": "must"},
        {"skill": "Kafka", "importance": "must"},
        {"skill": "RBAC", "importance": "should"},
        {"skill": "Terraform", "importance": "nice"},
        {"skill": "Observability", "importance": "should"},
    ],
}


@pytest.mark.asyncio
async def test_a_grounded_note_is_kept(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"note": "You've covered 6 of 12, 1 partial; the 5 gaps are real. Kubernetes and Kafka must close first — 54% is fine but senior backend without those two is the ceiling."}
    monkeypatch.setattr(note_mod, "ask_json", fake_ask_json)
    out = await note_mod.gap_note(_PAYLOAD, locale="en")
    assert out["note"].startswith("You've covered")


@pytest.mark.asyncio
async def test_a_note_citing_only_foreign_digits_is_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"note": "You need 3 more AWS certs and Python 4.0 features."}
    monkeypatch.setattr(note_mod, "ask_json", fake_ask_json)
    out = await note_mod.gap_note(_PAYLOAD, locale="en")
    assert out["note"] is None


@pytest.mark.asyncio
async def test_the_chinese_note_survives_to_the_client(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"note": "6/12 已盖，1 个部分，缺 Kubernetes 和 Kafka 这两个必须项，覆盖 0.54——这是要先补的。"}
    monkeypatch.setattr(note_mod, "ask_json", fake_ask_json)
    out = await note_mod.gap_note(_PAYLOAD, locale="zh")
    assert out["note"] is not None


@pytest.mark.asyncio
async def test_relay_failure_answers_a_null_note(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("relay down")
    monkeypatch.setattr(note_mod, "ask_json", boom)
    out = await note_mod.gap_note(_PAYLOAD, locale="en")
    assert out["note"] is None
