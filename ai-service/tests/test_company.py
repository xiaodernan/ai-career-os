"""Unit tests for company intelligence (forward Epic 4.8).

Summarise a company's open roles, top-demanded skills and advertised salary band from
the corpus. Deterministic and evidence-bound.
"""

from app.features.company import company_brief

SAMPLES = [
    {"company": "Acme", "title": "Backend Engineer", "skills": ["Java", "Kubernetes"],
     "salary_min": 300000, "salary_max": 400000, "salary_currency": "CNY"},
    {"company": "Acme", "title": "Senior Backend Engineer", "skills": ["Java", "Kafka"],
     "salary_min": 500000, "salary_max": 700000, "salary_currency": "CNY"},
    {"company": "Beta Corp", "title": "Frontend Engineer", "skills": ["React"],
     "salary_min": 200000, "salary_max": 300000, "salary_currency": "CNY"},
]


def test_brief_matches_case_insensitively():
    out = company_brief(SAMPLES, "acme")
    assert out["postings"] == 2
    assert out["roles"] == ["Backend Engineer", "Senior Backend Engineer"]
    assert out["topSkills"][0] == {"skill": "Java", "count": 2}


def test_brief_salary_band():
    out = company_brief(SAMPLES, "Acme")
    assert out["salaryBand"] == {"min": 350000, "p50": 475000, "max": 600000,
                                 "currency": "CNY"}


def test_brief_falls_back_to_substring():
    out = company_brief(SAMPLES, "Beta")
    assert out["postings"] == 1
    assert out["roles"] == ["Frontend Engineer"]


def test_brief_caps_roles_and_skills():
    out = company_brief(SAMPLES, "Acme", top=1)
    assert len(out["roles"]) == 1 and len(out["topSkills"]) == 1


def test_brief_no_salary_is_none_not_zero():
    out = company_brief([{"company": "X", "title": "Dev", "skills": ["Go"]}], "X")
    assert out["salaryBand"] is None


def test_brief_unknown_company_is_empty():
    assert company_brief(SAMPLES, "Nope") == {
        "company": "Nope", "postings": 0, "roles": [], "topSkills": [], "salaryBand": None}
