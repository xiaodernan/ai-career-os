"""Unit tests for Salary & Compensation Intelligence (forward Epic 12.1).

The whole feature is deterministic -- salaries are integers the DB already holds,
so the percentiles and the market verdict are computed here, not narrated by a
model. These tests pin that arithmetic and the filtering that feeds it.
"""

import pytest

from app.features import salary as salary_mod
from app.features.salary import (benchmark, filter_samples, load_job_samples,
                                 percentile, position, representative, summarize,
                                 _role_tokens)


# ---------------- percentile ----------------


def test_percentile_empty_is_none():
    assert percentile([], 0.5) is None


def test_percentile_single_value():
    assert percentile([42], 0.9) == 42.0


def test_percentile_linear_interpolation():
    vals = [100.0, 200.0, 300.0, 400.0]
    assert percentile(vals, 0.25) == pytest.approx(175.0)
    assert percentile(vals, 0.50) == pytest.approx(250.0)
    assert percentile(vals, 0.75) == pytest.approx(325.0)
    assert percentile(vals, 0.0) == 100.0
    assert percentile(vals, 1.0) == 400.0


# ---------------- summarize ----------------


def test_summarize_empty():
    assert summarize([]) == {"count": 0}


def test_summarize_known_quartiles():
    assert summarize([400, 100, 300, 200]) == {
        "count": 4, "min": 100, "p25": 175, "p50": 250, "p75": 325, "max": 400}


def test_summarize_ignores_nones():
    assert summarize([100.0, None, 300.0])["count"] == 2


# ---------------- representative ----------------


def test_representative_midpoint():
    assert representative({"salary_min": 300000, "salary_max": 500000}) == 400000


def test_representative_single_bound():
    assert representative({"salary_min": 300000}) == 300000
    assert representative({"salary_max": 500000}) == 500000


def test_representative_none_when_no_salary():
    assert representative({}) is None
    assert representative({"salary_min": None, "salary_max": None}) is None


# ---------------- _role_tokens ----------------


def test_role_tokens_strip_generic_words():
    assert _role_tokens("Senior Backend Engineer") == ["backend"]


def test_role_tokens_fallback_when_all_generic():
    # "Engineer" alone has no significant token, so it falls back rather than matching nothing.
    assert _role_tokens("Engineer") == ["engineer"]


def test_role_tokens_keep_cjk_segment():
    assert _role_tokens("算法工程师") == ["算法工程师"]


# ---------------- filter_samples ----------------

SAMPLES = [
    {"title": "Senior Backend Engineer", "location": "Shanghai", "experience_years": 6,
     "salary_min": 400000, "salary_max": 600000, "salary_currency": "CNY"},
    {"title": "Backend Engineer", "location": "Beijing", "experience_years": 3,
     "salary_min": 300000, "salary_max": 400000, "salary_currency": "CNY"},
    {"title": "Frontend Engineer", "location": "Shanghai", "experience_years": 4,
     "salary_min": 250000, "salary_max": 350000, "salary_currency": "CNY"},
    {"title": "Data Engineer", "location": "Shenzhen", "experience_years": 5,
     "salary_min": None, "salary_max": None, "salary_currency": "CNY"},          # no salary
    {"title": "Backend Engineer", "location": "Shanghai", "experience_years": 2,
     "salary_min": 200000, "salary_max": 280000, "salary_currency": "USD"},       # other currency
]


def test_filter_by_role_and_currency_excludes_unpriced_and_foreign():
    got = filter_samples(SAMPLES, role="Backend Engineer", currency="CNY")
    assert [s["title"] for s in got] == ["Senior Backend Engineer", "Backend Engineer"]
    assert all(s["salary_currency"] == "CNY" for s in got)


def test_filter_by_location():
    got = filter_samples(SAMPLES, role="Backend Engineer", location="Shanghai", currency="CNY")
    assert [s["title"] for s in got] == ["Senior Backend Engineer"]


def test_filter_by_seniority_band():
    got = filter_samples(SAMPLES, role="Backend Engineer", seniority="senior", currency="CNY")
    # senior band is 5..9 years: the 6-year role stays, the 3-year role drops.
    assert [s["title"] for s in got] == ["Senior Backend Engineer"]


def test_filter_includes_unknown_experience_under_a_band():
    samples = [{"title": "Backend Engineer", "experience_years": None,
                "salary_min": 300000, "salary_max": 400000, "salary_currency": "CNY"}]
    assert len(filter_samples(samples, role="Backend", seniority="senior")) == 1


def test_filter_unknown_seniority_applies_no_band():
    got = filter_samples(SAMPLES, role="Backend Engineer", currency="CNY")
    assert len(got) == 2  # both years (6 and 3) survive when no band is requested


# ---------------- position ----------------


def test_position_verdicts():
    vals = [100.0, 200.0, 300.0, 400.0]
    assert position(100, vals)["verdict"] == "below_market"
    assert position(250, vals)["verdict"] == "within_market"
    assert position(400, vals)["verdict"] == "above_market"


def test_position_percentile_rank():
    vals = [100.0, 200.0, 300.0, 400.0]
    assert position(250, vals)["percentile"] == 50.0


def test_position_empty_is_unknown():
    assert position(250, []) == {"percentile": None, "verdict": "unknown"}


# ---------------- benchmark ----------------


def test_benchmark_reports_percentiles_and_evidence():
    report = benchmark(SAMPLES, role="Backend Engineer", currency="CNY")
    assert report["sampleSize"] == 2
    assert report["percentiles"]["min"] == 350000     # (300k+400k)/2
    assert report["percentiles"]["max"] == 500000     # (400k+600k)/2
    assert [e["title"] for e in report["evidence"]] == ["Senior Backend Engineer",
                                                        "Backend Engineer"]


def test_benchmark_positions_a_target():
    report = benchmark(SAMPLES, role="Backend Engineer", currency="CNY", target_salary=500000)
    assert report["position"]["verdict"] in ("within_market", "above_market")
    assert report["position"]["percentile"] is not None


def test_benchmark_without_target_has_no_position():
    report = benchmark(SAMPLES, role="Backend Engineer", currency="CNY")
    assert "position" not in report


def test_benchmark_empty_match_explains_itself():
    report = benchmark(SAMPLES, role="Quantum Wizard", currency="CNY")
    assert report["sampleSize"] == 0
    assert report["percentiles"] == {}
    assert "note" in report and "no comparable" in report["note"].lower()


def test_benchmark_caps_evidence_but_not_sample_size():
    samples = [{"title": "Backend Engineer", "location": "X", "experience_years": 3,
                "salary_min": 300000 + i, "salary_max": 400000 + i,
                "salary_currency": "CNY"} for i in range(20)]
    report = benchmark(samples, role="Backend", currency="CNY", max_evidence=5)
    assert report["sampleSize"] == 20
    assert len(report["evidence"]) == 5


# ---------------- load_job_samples wiring ----------------


async def test_load_job_samples_converts_records(monkeypatch):
    record = {"title": "Backend Engineer", "location": "Beijing", "remote_type": "hybrid",
              "employment_type": "full_time", "experience_years": 3,
              "salary_min": 300000, "salary_max": 400000, "salary_currency": "CNY"}

    async def fake_fetch(query, *args):
        assert "FROM jobs" in query and "salary_min IS NOT NULL" in query
        return [record]

    monkeypatch.setattr(salary_mod.db, "fetch", fake_fetch)
    rows = await load_job_samples()
    assert rows == [record]
