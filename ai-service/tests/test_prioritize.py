"""Tests for market-weighted gap prioritization (forward Epic 10.12).

The ranking is pure arithmetic over two evidence-bound inputs (the gap report and the
role-family demand), so the core is tested without an LLM. The async orchestrator is
tested with the LLM gap call stubbed and the corpus injected directly.
"""

import pytest

from app.features import prioritize


def test_rank_prioritizes_must_high_demand_first():
    gaps = [{"skill": "Docker", "importance": "nice", "category": "devops"},
            {"skill": "Kubernetes", "importance": "must", "category": "devops"}]
    demand = [{"skill": "Kubernetes", "count": 68, "share": 0.68},
              {"skill": "Docker", "count": 31, "share": 0.31}]
    ranked = prioritize.rank_gap_priorities(gaps, demand, 100)
    assert [r["skill"] for r in ranked] == ["Kubernetes", "Docker"]


def test_rank_labels_priority_bands():
    gaps = [{"skill": "Kubernetes", "importance": "must", "category": "devops"},
            {"skill": "Docker", "importance": "should", "category": "devops"},
            {"skill": "Helm", "importance": "nice", "category": "devops"}]
    # only Kubernetes and Docker appear in demand; Helm is unknown to the corpus
    demand = [{"skill": "Kubernetes", "count": 68, "share": 0.68},
              {"skill": "Docker", "count": 8, "share": 0.08}]
    ranked = prioritize.rank_gap_priorities(gaps, demand, 100)
    by_skill = {r["skill"]: r for r in ranked}
    assert by_skill["Kubernetes"]["priority"] == "critical"   # must + >=0.3
    assert by_skill["Docker"]["priority"] == "low"            # should + <0.1 share
    assert by_skill["Helm"]["priority"] == "low"              # nice + 0 share
    assert by_skill["Helm"]["marketShare"] == 0.0


def test_rank_normalizes_alias_and_case():
    gaps = [{"skill": "kubernetes", "importance": "must", "category": "devops"}]
    demand = [{"skill": "Kubernetes", "count": 10, "share": 0.5}]
    ranked = prioritize.rank_gap_priorities(gaps, demand, 20)
    assert ranked and ranked[0]["marketShare"] == 0.5


def test_rank_empty_gaps():
    assert prioritize.rank_gap_priorities([], [{"skill": "X", "count": 1, "share": 0.1}], 5) == []


def test_rank_missing_demand_yields_zero_share():
    gaps = [{"skill": "Rust", "importance": "should", "category": "language"}]
    ranked = prioritize.rank_gap_priorities(gaps, [], 0)
    assert ranked[0]["marketShare"] == 0.0
    assert ranked[0]["marketPostings"] == 0
    assert ranked[0]["marketRank"] == 0


async def test_plan_learning_priority_orchestrates(monkeypatch):
    async def fake_gap(role, seniority, structured, plaintext, *, user_id=None, run_id=None):
        return {"gaps": [{"skill": "Kubernetes", "importance": "must"},
                         {"skill": "Docker", "importance": "nice"}],
                "coverage": 0.4, "seniority": ""}

    monkeypatch.setattr(prioritize.gap_analysis, "analyze_gap", fake_gap)

    samples = [
        {"title": "Backend Engineer", "location": "", "skills": ["Kubernetes", "Docker"]},
    ]
    plan = await prioritize.plan_learning_priority(
        target_role="Senior Backend Engineer",
        resume_structured={"skills": []}, samples=samples)
    assert plan["targetRole"] == "Senior Backend Engineer"
    assert plan["gapCount"] == 2
    assert plan["coverage"] == 0.4
    assert plan["prioritizedGaps"][0]["skill"] == "Kubernetes"
    assert plan["topPriority"]["skill"] == "Kubernetes"
    assert plan["marketPostings"] >= 1
