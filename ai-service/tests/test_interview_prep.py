"""Tests for the interview prep plan (forward Epic 10.13).

The checklist is built from two evidence-bound inputs (the gap report and the story
bank), so the core is tested without an LLM. The async orchestrator is tested with the
LLM gap call stubbed.
"""

import pytest

from app.features import interview_prep


def test_weak_areas_sorted_by_importance():
    gap = {"gaps": [{"skill": "Go", "importance": "nice"},
                    {"skill": "Kubernetes", "importance": "must"},
                    {"skill": "gRPC", "importance": "should"}]}
    out = interview_prep.build_prep_plan(gap, {"count": 0, "stories": []})
    assert [w["skill"] for w in out["weakAreas"]] == ["Kubernetes", "gRPC", "Go"]


def test_strength_story_maps_to_strongest_evidencing_story():
    gap = {"covered": [{"skill": "Java", "evidence": "Declared skill: Java"}]}
    bank = {"count": 2, "stories": [
        {"id": "exp-1", "title": "Java service", "skills": ["Java"], "quantified": False,
         "bullets": ["Built a Java service"], "kind": "experience"},
        {"id": "proj-1", "title": "Java platform", "skills": ["Java"], "quantified": True,
         "bullets": ["Scaled Java platform to 1M users"], "kind": "project"},
    ]}
    out = interview_prep.build_prep_plan(gap, bank)
    s = out["strengthStories"][0]
    assert s["storyId"] == "proj-1"   # quantified story preferred over plain
    assert s["quantified"] is True


def test_covered_skill_with_no_story_has_null_story():
    gap = {"covered": [{"skill": "Python", "evidence": "Declared skill: Python"}]}
    out = interview_prep.build_prep_plan(gap, {"count": 0, "stories": []})
    s = out["strengthStories"][0]
    assert s["storyId"] is None
    assert out["strengthStoryCount"] == 0


def test_likely_topics_mix_responsibilities_and_gap_address():
    gap = {"responsibilities": ["Design APIs", "Mentor juniors"],
           "gaps": [{"skill": "Kubernetes", "importance": "must"}]}
    out = interview_prep.build_prep_plan(gap, {"count": 0, "stories": []})
    assert "Design APIs" in out["likelyTopics"]
    assert any("Kubernetes" in t for t in out["likelyTopics"])


def test_empty_inputs():
    out = interview_prep.build_prep_plan({}, {"count": 0, "stories": []})
    assert out["weakAreas"] == []
    assert out["strengthStories"] == []
    assert out["likelyTopics"] == []
    assert out["weakAreaCount"] == 0


async def test_plan_interview_prep_orchestrates(monkeypatch):
    async def fake_gap(role, seniority, structured, plaintext, *, user_id=None, run_id=None):
        return {"targetRole": role, "coverage": 0.5,
                "covered": [{"skill": "Java", "evidence": "Declared skill: Java"}],
                "gaps": [{"skill": "Kubernetes", "importance": "must"}],
                "responsibilities": ["Design APIs"]}

    monkeypatch.setattr(interview_prep.gap_analysis, "analyze_gap", fake_gap)

    resume = {"skills": [{"name": "Java"}],
              "experience": [{"title": "BE", "company": "X",
                              "bullets": ["Built a Java service handling 1M rps"]}]}
    plan = await interview_prep.plan_interview_prep(
        target_role="Senior Backend Engineer", resume_structured=resume)
    assert plan["targetRole"] == "Senior Backend Engineer"
    assert plan["weakAreaCount"] == 1
    assert plan["strengthStoryCount"] == 1
    assert plan["strengthStories"][0]["storyId"] == "exp-1"
    assert plan["storyBankSize"] == 1
    assert plan["likelyTopics"][0] == "Design APIs"
