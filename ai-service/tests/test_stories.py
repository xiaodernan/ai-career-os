"""Unit tests for the STAR story bank (forward Epic 6.5).

Deterministic and evidence-bound: it reorganises the candidate's own experience and
projects into ranked story seeds. These tests pin the skill attribution, the ranking
(quantified first), and the honest handling of empty / malformed input.
"""

from app.features.stories import build_story_bank

RESUME = {
    "skills": [{"name": "Java"}, {"name": "Kubernetes"}, {"name": "Redis"}],
    "experience": [
        {"title": "Backend Engineer", "company": "Acme",
         "bullets": ["Built Java services", "Cut p99 latency by 30%"]},
        {"title": "Intern", "company": "Beta", "bullets": ["Wrote documentation"]},
    ],
    "projects": [
        {"name": "Payments Rewrite", "tech": ["Kubernetes", "Redis"],
         "bullets": ["Migrated 12 services"]},
    ],
}


def test_bank_builds_one_seed_per_role_and_project():
    out = build_story_bank(RESUME)
    assert out["count"] == 3
    assert out["quantifiedCount"] == 2
    assert out["skillsCovered"] == ["Java", "Kubernetes", "Redis"]


def test_bank_ranks_quantified_stories_first():
    out = build_story_bank(RESUME)
    assert out["stories"][0]["id"] == "proj-1"          # quantified, 2 skills
    assert out["stories"][1]["id"] == "exp-1"           # quantified, 1 skill
    assert out["stories"][2]["id"] == "exp-2"           # not quantified
    assert out["stories"][2]["quantified"] is False


def test_bank_attributes_declared_skills_mentioned_in_bullets():
    out = build_story_bank(RESUME)
    exp1 = next(s for s in out["stories"] if s["id"] == "exp-1")
    assert exp1["skills"] == ["Java"]                   # only Java is in the bullets
    assert exp1["title"] == "Backend Engineer at Acme"


def test_bank_includes_project_tech():
    out = build_story_bank(RESUME)
    proj = next(s for s in out["stories"] if s["id"] == "proj-1")
    assert proj["kind"] == "project"
    assert proj["skills"] == ["Kubernetes", "Redis"]


def test_bank_caps_the_list():
    resume = {"experience": [{"title": "R", "company": "C", "bullets": ["did 1 thing"]}] * 5}
    assert build_story_bank(resume, max_stories=2)["count"] == 2


def test_bank_skips_malformed_entries():
    resume = {"experience": [{"title": "R", "company": "C", "bullets": ["x"]}, "nope"],
              "projects": [None]}
    assert build_story_bank(resume)["count"] == 1


def test_bank_empty_and_none():
    empty = {"stories": [], "count": 0, "quantifiedCount": 0, "skillsCovered": []}
    assert build_story_bank({}) == empty
    assert build_story_bank(None) == empty
