"""Epic 302: the interview report rides the bounded StateGraph.

`finalize` is no longer a single blind LLM call wearing setdefaults: the model
drafts, the graph bounds the draft into what the prompt promised, and the
renderer ships it. The verify node is deterministic on purpose — every reader
of this answer (the panel, the trace, the trajectory fold) sees a map whose
promises are enforced, not hoped for. These tests pin exactly that: hostile
model output is clamped, never dropped into the UI; absent output keeps the
documented floor; nothing in the pipeline invents a score from thin air.
"""

import math

import pytest

from app.features import interview
from app.features.interview import finalize


@pytest.mark.asyncio
async def test_hostile_dimensions_are_clamped_not_trusted(monkeypatch):
    async def fake(*a, **k):
        return {"dims": {
            "technical_accuracy": 88.0,          # the classic "percent-style" hallucination
            "communication": "-3",               # negative bound, coerced as string
            "clarity": "high",                  # not a number — must drop out entirely
            "evidence": True,                   # bool coerces to 1.0 and stays honest
            "reasoning": math.nan,              # NaN is not a report — must drop out
            "follow_through": 0.75,             # already true — kept as-is
        }, "overall": 9.9}
    monkeypatch.setattr("app.features.interview.ask_json", fake)
    out = await finalize(mode="mixed", turns=[], resume_ctx="ctx")
    assert out["dims"] == {
        "technical_accuracy": 1.0,
        "communication": 0.0,
        "evidence": 1.0,
        "follow_through": 0.75,
    }, f"every hostile dimension must clamp, drop or pass — never ship raw: {out['dims']}"
    assert "reasoning" not in out["dims"]
    assert "clarity" not in out["dims"]
    assert out["overall"] == 1.0                # clamped into the band, not re-invented


@pytest.mark.asyncio
async def test_nan_and_inf_dimensions_never_reach_the_reader(monkeypatch):
    async def fake(*a, **k):
        return {"dims": {"clarity": math.nan, "evidence": float("inf"), "depth": 0.5}, "overall": None}
    monkeypatch.setattr("app.features.interview.ask_json", fake)
    out = await finalize(mode="mixed", turns=[], resume_ctx="")
    assert out["dims"] == {"depth": 0.5}
    assert out["overall"] == 0.5            # absent/"unusable" overall keeps the documented floor


@pytest.mark.asyncio
async def test_non_dict_model_answer_keeps_the_floor(monkeypatch):
    async def fake(*a, **k):
        return ["not", "a", "dict"]
    monkeypatch.setattr("app.features.interview.ask_json", fake)
    out = await finalize(mode="mixed", turns=[], resume_ctx="")
    assert out["dims"] == {}
    assert out["overall"] == 0.5
    assert out["trajectory_detail"] == []


@pytest.mark.asyncio
async def test_overall_in_the_band_passes_through_untouched(monkeypatch):
    async def fake(*a, **k):
        return {"dims": {"technical_accuracy": 0.7}, "overall": 0.65}
    monkeypatch.setattr("app.features.interview.ask_json", fake)
    out = await finalize(mode="mixed", turns=[], resume_ctx="")
    assert out["dims"] == {"technical_accuracy": 0.7}
    assert out["overall"] == 0.65           # the existing contract holds, byte for byte


@pytest.mark.asyncio
async def test_failed_llm_keeps_dims_floor_and_builds_trajectory(monkeypatch):
    async def fake(*a, **k):
        raise RuntimeError("provider down")
    monkeypatch.setattr("app.features.interview.ask_json", fake)
    turns = [{"seq": 0, "role": "interviewer", "content": "q"},
             {"seq": 1, "role": "candidate", "content": "a"}]
    out = await finalize(mode="mixed", turns=turns, resume_ctx="ctx")
    assert out["dims"] == {}
    assert out["overall"] == 0.5
    assert out["trajectory_detail"] == interview._trajectory_detail(turns)
