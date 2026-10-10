"""Unit tests for the Career Gap & Growth Analysis feature (forward Epic 10.1).

Like the match engine, only the pure, I/O-free helpers are exercised directly,
plus one ``analyze_gap`` driver with the LLM stubbed. The deterministic coverage
verdict is the whole point: a skill is "covered" only if a quote behind it exists
in the candidate's own material, so that contract is what these tests hold.
"""

import json

import pytest

from app.features import gap_analysis as gap_mod
from app.features.gap_analysis import (analyze_gap, build_development_plan,
                                       build_evidence, classify_coverage,
                                       _mentioned, _sanitize_expected)


# ---------------- build_evidence ----------------


def test_build_evidence_collects_declared_skills_and_prose():
    structured = {
        "skills": [{"name": "Java"}, {"name": "kubernetes"}],
        "experience": [{"bullets": ["Built a Spring Boot service", "used Redis"]}],
        "projects": [{"bullets": ["Wrote a Kafka consumer"]}],
    }
    skills, corpus = build_evidence(structured, "plain resume text")
    assert skills == {"Java", "Kubernetes"}
    assert "Spring Boot" in corpus and "Kafka" in corpus and "plain resume text" in corpus


def test_build_evidence_tolerates_null_sections():
    # Java-owned jsonb can carry present-null sections; mirroring the match engine,
    # a None must not take the helper down.
    structured = {"skills": None, "experience": None, "projects": None}
    skills, corpus = build_evidence(structured, "")
    assert skills == set()
    assert corpus == ""


def test_build_evidence_tolerates_a_json_string_structured():
    structured = json.dumps({"skills": [{"name": "Go"}]})
    skills, _ = build_evidence(structured, "")
    assert skills == {"Go"}


# ---------------- _mentioned (word boundary) ----------------


def test_mentioned_is_word_bounded_not_substring():
    # "go" must not match "google"; "java" must not match "javascript".
    assert _mentioned("go", "i will go to the cloud")      # standalone word
    assert not _mentioned("Go", "i used google cloud")     # substring inside 'google'
    assert not _mentioned("Java", "i wrote javascript")    # substring inside 'javascript'
    assert _mentioned("Java", "i wrote Java")
    assert _mentioned("Kubernetes", "ran Kubernetes in prod")


# ---------------- classify_coverage ----------------


def _expected(*names, importance="must"):
    return [{"name": n, "category": "core", "importance": importance} for n in names]


def test_classify_coverage_covered_when_declared():
    cov, par, gaps = classify_coverage(
        _expected("Java", "Go"), {"Java", "Go"}, "plain text")
    assert [c["skill"] for c in cov] == ["Java", "Go"]
    assert par == [] and gaps == []


def test_classify_coverage_partial_when_mentioned_in_prose_only():
    cov, par, gaps = classify_coverage(
        _expected("Redis"), set(), "we used Redis for caching")
    assert cov == []
    assert [p["skill"] for p in par] == ["Redis"]
    assert "Redis" in par[0]["evidence"]
    assert gaps == []


def test_classify_coverage_gap_when_absent():
    cov, par, gaps = classify_coverage(
        _expected("Rust"), set(), "java only here")
    assert cov == [] and par == []
    assert [g["skill"] for g in gaps] == ["Rust"]


def test_classify_coverage_mixes_all_three():
    expected = _expected("Java", "Kubernetes", "Rust")
    cov, par, gaps = classify_coverage(
        expected, {"Java"}, "mentions Kubernetes in a sentence")
    assert [c["skill"] for c in cov] == ["Java"]
    assert [p["skill"] for p in par] == ["Kubernetes"]
    assert [g["skill"] for g in gaps] == ["Rust"]


def test_classify_coverage_preserves_importance_and_category():
    expected = [{"name": "Java", "category": "language", "importance": "must"},
                {"name": "Rust", "category": "language", "importance": "nice"}]
    cov, par, gaps = classify_coverage(expected, {"Java"}, "")
    assert cov[0]["importance"] == "must" and cov[0]["category"] == "language"
    assert gaps[0]["importance"] == "nice"


# ---------------- _sanitize_expected ----------------


def test_sanitize_expected_drops_blanks_dedups_and_normalizes():
    out = _sanitize_expected({
        "expectedSkills": [{"name": "  java "}, {"name": "Java"}, {"name": ""},
                           {"name": "k8s", "category": "devops", "importance": "nice"}]},
        "Backend Engineer")
    names = [s["name"] for s in out["expectedSkills"]]
    assert names == ["Java", "Kubernetes"]
    assert out["expectedSkills"][1]["category"] == "devops"
    assert out["expectedSkills"][1]["importance"] == "nice"


def test_sanitize_expected_defaults_importance_to_should():
    out = _sanitize_expected({"expectedSkills": [{"name": "Go"}]}, "Backend Engineer")
    assert out["expectedSkills"][0]["importance"] == "should"


def test_sanitize_expected_backstop_uses_dictionary_extraction():
    # An empty / degenerate LLM reply must not yield an empty report offline.
    out = _sanitize_expected({}, "Senior Backend Engineer with Java, Spring Boot, Kubernetes")
    names = {s["name"] for s in out["expectedSkills"]}
    assert {"Java", "Spring Boot", "Kubernetes"} <= names


# ---------------- build_development_plan ----------------


def test_development_plan_orders_gaps_before_partials_and_by_importance():
    gaps = [{"skill": "Rust", "importance": "nice", "category": "language"},
            {"skill": "Kubernetes", "importance": "must", "category": "devops"}]
    partial = [{"skill": "Go", "importance": "should", "category": "language"}]
    plan = build_development_plan(gaps, partial)
    # must gap first, then should partial, then nice gap
    assert plan[0]["skill"] == "Kubernetes"
    assert plan[1]["skill"] == "Go"
    assert plan[2]["skill"] == "Rust"


def test_development_plan_caps_at_twelve():
    gaps = [{"skill": f"skill{i}", "importance": "must", "category": "core"}
            for i in range(20)]
    plan = build_development_plan(gaps, [])
    assert len(plan) == 12


def test_development_plan_empty_when_nothing_to_close():
    assert build_development_plan([], []) == []


# ---------------- analyze_gap wiring (LLM stubbed) ----------------


def _stub_expected(monkeypatch, payload: dict):
    async def fake_ask_json(req, *, user_id=None, run_id=None, agent="system", kind="chat"):
        return payload
    monkeypatch.setattr(gap_mod, "ask_json", fake_ask_json)


_RESUME = {
    "skills": [{"name": "Java"}, {"name": "Spring Boot"}],
    "experience": [{"company": "X", "title": "Engineer", "start": "2019",
                    "end": "present", "bullets": ["Built services with PostgreSQL"]}],
    "projects": [{"bullets": ["Used Kafka for events"]}],
    "education": [],
}


async def test_analyze_gap_reports_covered_partial_and_gaps(monkeypatch):
    _stub_expected(monkeypatch, {
        "expectedSkills": [
            {"name": "Java", "category": "language", "importance": "must"},
            {"name": "Kubernetes", "category": "devops", "importance": "must"},
            {"name": "Go", "category": "language", "importance": "nice"},
        ],
        "responsibilities": ["design services"],
        "seniorityHint": "senior",
    })
    result = await analyze_gap("Senior Backend Engineer", None, _RESUME, "plain text",
                               user_id="u-1")
    assert result["expectedSkillCount"] == 3
    assert result["coveredCount"] == 1          # Java (declared)
    assert result["partialCount"] == 0          # nothing is merely mentioned, not declared
    assert result["gapCount"] == 2              # Kubernetes and Go are absent from the resume
    assert result["covered"][0]["skill"] == "Java"
    assert {g["skill"] for g in result["gaps"]} == {"Kubernetes", "Go"}
    assert result["coverage"] == pytest.approx(1 / 3, abs=0.001)
    assert result["developmentPlan"]
    assert result["seniority"] == "senior"
    assert result["responsibilities"] == ["design services"]


async def test_analyze_gap_falls_back_to_dict_when_llm_returns_nonsense(monkeypatch):
    # The mock provider returns {"answer": ...} for unknown prompts; the feature
    # must still produce a report from dictionary skill extraction.
    _stub_expected(monkeypatch, {"answer": "mock structured answer", "confidence": 0.8})
    result = await analyze_gap(
        "Senior Backend Engineer with Java, Spring Boot, Kubernetes, PostgreSQL",
        "senior", _RESUME, "plain text", user_id="u-1")
    names = {s["skill"] for s in result["covered"] + result["partial"] + result["gaps"]}
    assert {"Java", "Spring Boot", "Kubernetes", "PostgreSQL"} <= names
    assert result["expectedSkillCount"] >= 4
