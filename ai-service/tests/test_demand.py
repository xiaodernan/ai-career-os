"""Unit tests for market skill demand (forward Epic 10.9).

Counts the `skills` the postings already carry, over postings that list at least one
skill (a sparse row must not dilute the denominator). Deterministic.
"""

from app.features.demand import skill_demand

SAMPLES = [
    {"title": "Senior Backend Engineer", "location": "Shanghai",
     "skills": ["Java", "Kubernetes", "PostgreSQL"]},
    {"title": "Backend Engineer", "location": "Beijing", "skills": ["Java", "Kafka"]},
    {"title": "Backend Engineer", "location": "Shenzhen", "skills": ["Java", "Kubernetes"]},
    {"title": "Frontend Engineer", "location": "Shanghai", "skills": ["React", "TypeScript"]},
    {"title": "Data Engineer", "location": "Beijing", "skills": []},
]


def test_demand_ranks_by_frequency_with_share():
    out = skill_demand(SAMPLES, role="Backend Engineer")
    assert out["postings"] == 3                       # the three backend roles
    assert out["skills"][0] == {"skill": "Java", "count": 3, "share": 1.0}
    assert out["skills"][1]["skill"] == "Kubernetes"
    assert out["skills"][1]["count"] == 2
    assert out["skills"][1]["share"] == round(2 / 3, 3)


def test_demand_filters_by_location_case_insensitively():
    out = skill_demand(SAMPLES, role="Backend", location="beijing")
    assert out["postings"] == 1
    assert {s["skill"] for s in out["skills"]} == {"Java", "Kafka"}


def test_rows_without_skills_are_not_in_the_denominator():
    samples = [{"title": "Backend Engineer", "skills": ["Java"]},
               {"title": "Backend Engineer", "skills": []}]
    out = skill_demand(samples, role="Backend")
    assert out["postings"] == 1
    assert out["skills"][0]["share"] == 1.0


def test_demand_caps_the_list():
    out = skill_demand(SAMPLES, role="Backend", top=1)
    assert len(out["skills"]) == 1 and out["skills"][0]["skill"] == "Java"


def test_demand_without_a_role_scans_all_postings():
    out = skill_demand(SAMPLES, role="")
    assert out["postings"] == 4                       # all rows that list any skill


def test_demand_empty():
    assert skill_demand([], role="Backend") == {
        "role": "Backend", "location": "", "postings": 0, "skills": []}
