"""Unit tests for target-role suggestions (forward Epic 10.10).

Groups the corpus into role families and reports the candidate's coverage of each
family's most-demanded skills, ranked by coverage. Deterministic.
"""

from app.features.roles import declared_skills, family_of, suggest_roles

SAMPLES = [
    {"title": "Backend Engineer", "skills": ["Java", "Kubernetes"]},
    {"title": "Senior Backend Engineer", "skills": ["Java", "Kafka"]},
    {"title": "Frontend Engineer", "skills": ["React", "TypeScript"]},
    {"title": "Data Engineer", "skills": ["SQL", "Spark"]},
]


# ---------------- family_of ----------------


def test_family_of_maps_titles():
    assert family_of("Backend Engineer") == "backend"
    assert family_of("Frontend Developer") == "frontend"
    assert family_of("Full Stack Engineer") == "fullstack"
    assert family_of("Data Engineer") == "data"
    assert family_of("Machine Learning Engineer") == "ml"
    assert family_of("DevOps Engineer") == "devops"
    assert family_of("Android Engineer") == "mobile"
    assert family_of("QA Engineer") == "qa"


def test_family_of_unknown_is_other():
    assert family_of("Growth Hacker") == "other"
    assert family_of("") == "other"


# ---------------- suggest_roles ----------------


def test_suggest_roles_ranks_by_coverage():
    out = suggest_roles(SAMPLES, ["Java", "Kubernetes"])
    assert [f["family"] for f in out["families"]] == ["backend", "data", "frontend"]
    backend = out["families"][0]
    assert backend["postings"] == 2
    assert backend["coverage"] == round(2 / 3, 3)
    assert backend["youHave"] == ["Java", "Kubernetes"]
    assert backend["missing"] == ["Kafka"]


def test_suggest_roles_min_postings_filters_thin_families():
    out = suggest_roles(SAMPLES, [], min_postings=2)
    assert [f["family"] for f in out["families"]] == ["backend"]


def test_suggest_roles_caps_the_list():
    assert len(suggest_roles(SAMPLES, [], top=1)["families"]) == 1


def test_suggest_roles_empty():
    assert suggest_roles([], ["Java"]) == {"families": []}


# ---------------- declared_skills ----------------


def test_declared_skills_normalizes():
    assert declared_skills({"skills": [{"name": "java"}, {"name": "k8s"}]}) == [
        "Java", "Kubernetes"]


def test_declared_skills_empty_and_none():
    assert declared_skills({}) == []
    assert declared_skills(None) == []
