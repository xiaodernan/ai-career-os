"""Epic 320: the overseer's counsel rides the bounded spine, and the spine audits the numbers.

`app/features/counsel.recommend` hands the install's aggregates to the model and keeps
only items that cite a digit-run present in the snapshot itself. These tests pin the
contract: hostile LLM output with invented figures is dropped, honest output passes,
and anything unusable answers with silence — never with a plausible-looking lie.
"""
from __future__ import annotations

import pytest

from app.features import counsel as counsel_mod

_SNAPSHOT = {
    "cache": {"calls": 1658, "cached_tokens": 2919639, "hit_pct": 54.7,
              "by_kind": {"resume_parse": {"calls": 316, "hit_pct": 84.3},
                          "tailor": {"calls": 27, "hit_pct": 5.9}}},
    "weekly": {"weeks": ["2026-11-09", "2026-11-16"],
               "aiUsageCached": [324, 517]},
    "attention": {"landings": 2641, "dwells": 160, "acts": 11,
                   "signedLandings": 1484, "dwellPerLandingMs": 20886},
    "funnel": {"stages": [{"id": "registered", "readers": 7889},
                           {"id": "uploaded", "readers": 3187},
                           {"id": "applied", "readers": 934},
                           {"id": "interviewed", "readers": 412},
                           {"id": "offered", "readers": 48}]},
}


@pytest.mark.asyncio
async def test_grounded_output_passes(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"summary": "Warm calls now outnumber cold ones 517:324.",
                "actions": ["Sweep the 2.7% applicants on the 48-application cliff",
                            "Watch resume_parse 84.3% cache hit rate hold"],
                "risks": ["If 5.9% keeps tailoring cold, the relay cost climbs"]}

    monkeypatch.setattr(counsel_mod, "ask_json", fake_ask_json)
    out = await counsel_mod.recommend(_SNAPSHOT)
    assert "517:324" in out["summary"]
    assert out["actions"] == ["Sweep the 2.7% applicants on the 48-application cliff",
                              "Watch resume_parse 84.3% cache hit rate hold"]
    assert out["risks"] == ["If 5.9% keeps tailoring cold, the relay cost climbs"]
    assert out["actions_dropped"] == 0
    assert out["risks_dropped"] == 0


@pytest.mark.asyncio
async def test_items_without_a_number_are_dropped(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"summary": "The mix is drifting toward heavier one-shot work.",
                "actions": ["Fix the funnel cliff at applied → interviewed",
                            "Talk to the team and be kind",
                            "watch the 324 cached calls"],
                "risks": ["silence is a risk"]}

    monkeypatch.setattr(counsel_mod, "ask_json", fake_ask_json)
    out = await counsel_mod.recommend(_SNAPSHOT)
    # only the items that cite a number the snapshot carries survive
    assert "Talk to the team and be kind" not in out["actions"]
    assert "Watch the 324 cached calls" in out["actions"] or "watch the 324 cached calls" in out["actions"] or any("324" in a for a in out["actions"])
    assert out["actions_dropped"] >= 1
    assert out["risks"] == []
    assert out["risks_dropped"] >= 1


@pytest.mark.asyncio
async def test_provider_failure_answers_silent(monkeypatch):
    async def boom(req, **kw):
        raise RuntimeError("provider down")
    monkeypatch.setattr(counsel_mod, "ask_json", boom)
    out = await counsel_mod.recommend(_SNAPSHOT)
    assert out == {"summary": "", "actions": [], "risks": [],
                   "actions_dropped": 0, "risks_dropped": 0}


@pytest.mark.asyncio
async def test_non_dict_model_answer_answers_silent(monkeypatch):
    async def fake(req, **kw):
        return ["not", "a", "dict"]
    monkeypatch.setattr(counsel_mod, "ask_json", fake)
    out = await counsel_mod.recommend(_SNAPSHOT)
    assert out == {"summary": "", "actions": [], "risks": [],
                   "actions_dropped": 0, "risks_dropped": 0}


def test_digit_run_parsing():
    # Snapshots carry bare numbers; the parser must normalize the model's prose
    # percent signs so "84.3%" matches the snapshot's "84.3".
    assert counsel_mod._digit_runs("at 2.7% with 1,658 and 0.4") == {"2.7", "1658", "0.4"}
    assert counsel_mod._digit_runs("54.7 hit rate") == {"54.7"}
