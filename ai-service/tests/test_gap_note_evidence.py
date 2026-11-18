"""Epic 331-gap-note: the gap analyst reads the reader's resume, not just the ratio.

Enriching the payload with a plaintext snippet keeps grounding discipline (digits
still need to exist in the payload) but lets the analyst cite real evidence the
platform measured — rather than "coverage 0.71" reads in a vacuum.
"""
from __future__ import annotations

import pytest

from app.features import gap_note as note_mod

_PAYLOAD_WITH_EVIDENCE = {
    "targetRole": "Senior Backend Engineer (Java)",
    "seniority": "senior",
    "expectedSkillCount": 12,
    "coveredCount": 6,
    "partialCount": 1,
    "gapCount": 5,
    "coverage": 0.54,
    "gaps": [{"skill": "Kubernetes", "importance": "must"}],
    "evidence": "2019-2026 8 years Java Spring Boot Kafka PostgreSQL QPS 40000",
    "locale": "en",
}


@pytest.mark.asyncio
async def test_evidence_widens_the_vocabulary_the_note_may_cite(monkeypatch):
    async def fake_ask_json(req, **kw):
        # A note citing evidence-only numbers — 2026 and 40000 are only in the
        # snippet, not the gap-analysis counts, so this asserts grounding widens
        # with the evidence block.
        return {"note": "Since 2019 I have shipped 40000 QPS worth of Java services; 5 gaps remain."}
    monkeypatch.setattr(note_mod, "ask_json", fake_ask_json)
    out = await note_mod.gap_note(_PAYLOAD_WITH_EVIDENCE, locale="en")
    assert out["note"] is not None
    assert "40000" in out["note"]


@pytest.mark.asyncio
async def test_foreign_digits_stay_dropped_even_with_evidence(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"note": "I need 99 AWS certifications."}
    monkeypatch.setattr(note_mod, "ask_json", fake_ask_json)
    out = await note_mod.gap_note(_PAYLOAD_WITH_EVIDENCE, locale="en")
    assert out["note"] is None
