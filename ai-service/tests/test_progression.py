"""Tests for the career progression planner (forward Epic 10.11).

The ranking is pure arithmetic over two evidence-bound inputs (the aspirational
role's gap report and the role-family demand from the corpus), so the core is tested
without an LLM. The async orchestrator is tested with the LLM gap call and the DB
sample load both stubbed, because both are exercised by the real endpoint.
"""

import pytest

from app.features import progression


def test_stepping_stones_excludes_families_with_no_overlap():
    fams = [
        {"family": "backend", "postings": 5, "coverage": 0.8,
         "topDemands": ["Java", "Kubernetes"], "youHave": ["Java"], "missing": ["Kubernetes"]},
        {"family": "frontend", "postings": 5, "coverage": 0.8,
         "topDemands": ["React", "TypeScript"], "youHave": [], "missing": ["React", "TypeScript"]},
    ]
    # Dream role is missing only Kubernetes; frontend builds none of it.
    stones = progression.build_stepping_stones(fams, ["Kubernetes"], ["Kubernetes"])
    assert [s["family"] for s in stones] == ["backend"]


def test_stepping_stones_ranks_must_gap_closures_first():
    fams = [
        {"family": "a", "postings": 10, "coverage": 0.6,
         "topDemands": ["Kubernetes"], "youHave": ["Java"], "missing": ["Kubernetes"]},
        {"family": "b", "postings": 10, "coverage": 0.9,
         "topDemands": ["React", "Vue"], "youHave": [], "missing": ["React", "Vue"]},
    ]
    # a closes 1 must-gap; b closes 2 should-gaps but none must. a must rank first.
    stones = progression.build_stepping_stones(
        fams, ["Kubernetes", "React", "Vue"], ["Kubernetes"])
    assert stones[0]["family"] == "a"
    assert stones[0]["bridgeScore"] > stones[1]["bridgeScore"]


def test_stepping_stones_normalize_bridges_case_and_alias():
    fams = [{"family": "backend", "postings": 1, "coverage": 0.0,
             "topDemands": ["Kubernetes"], "youHave": [], "missing": ["Kubernetes"]}]
    # Gap passed lowercase; family demand is canonical -- normalization must still match.
    stones = progression.build_stepping_stones(fams, ["kubernetes"], ["kubernetes"])
    assert stones and stones[0]["buildsSkills"] == ["Kubernetes"]


def test_stepping_stones_empty_input():
    assert progression.build_stepping_stones([], ["Kubernetes"], ["Kubernetes"]) == []
    assert progression.build_stepping_stones(
        [{"family": "x", "postings": 1, "coverage": 0.5, "topDemands": ["React"]}],
        ["Kubernetes"], ["Kubernetes"]) == []


def test_advice_reports_must_gaps_and_no_stone_case():
    with_must = progression.build_advice(0.3, 1, ["Kubernetes"])
    assert any("hard-requirement gap" in line for line in with_must)
    assert any("top stepping stone" in line for line in with_must)

    no_stone = progression.build_advice(0.3, 0, [])
    assert any("No role family" in line for line in no_stone)

    ready = progression.build_advice(0.85, 2, [])
    assert any("optional" in line for line in ready)


async def test_plan_progression_orchestrates(monkeypatch):
    async def fake_gap(role, seniority, structured, plaintext, *, user_id=None, run_id=None):
        return {"gaps": [{"skill": "Kubernetes", "importance": "must"},
                         {"skill": "PostgreSQL", "importance": "should"}],
                "coverage": 0.3, "gapCount": 2, "seniority": ""}

    monkeypatch.setattr(progression.gap_analysis, "analyze_gap", fake_gap)

    samples = [
        {"title": "Backend Engineer", "location": "", "skills": ["Java", "Kubernetes", "PostgreSQL"]},
        {"title": "Frontend Engineer", "location": "", "skills": ["React", "TypeScript"]},
    ]
    plan = await progression.plan_progression(
        aspirational_role="Staff Backend Engineer",
        resume_structured={"skills": [{"name": "Java"}]},
        samples=samples)
    assert plan["aspirationalRole"] == "Staff Backend Engineer"
    assert plan["aspirationalCoverage"] == 0.3
    assert plan["aspirationalMustGaps"] == ["Kubernetes"]
    assert len(plan["steppingStones"]) == 1
    assert plan["steppingStones"][0]["family"] == "backend"
    assert plan["steppingStones"][0]["buildsMustCount"] == 1
    assert set(plan["steppingStones"][0]["buildsSkills"]) == {"Kubernetes", "PostgreSQL"}
    assert plan["advice"]
