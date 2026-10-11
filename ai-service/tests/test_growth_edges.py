"""Edge-case hardening for the growth & market features (Epics 10.x / 12.x).

These lock the behaviours that are easy to get subtly wrong and that the happy-path
tests in the sibling files do not reach: the "C" vs "C++" mention boundary, the
percentile's tolerance of unsorted input and out-of-range p, a zero salary bound,
and the assess/leverage agreement at exactly the upper quartile.
"""

import pytest

from app.features.gap_analysis import _mentioned, classify_coverage
from app.features.negotiation import assess, leverage
from app.features.salary import filter_samples, percentile, representative

STATS = {"count": 4, "min": 100, "p25": 175, "p50": 250, "p75": 325, "max": 400}


# ---------------- percentile: robustness ----------------


def test_percentile_sorts_unsorted_input():
    assert percentile([400, 100, 300, 200], 0.5) == pytest.approx(250.0)
    assert percentile([400, 100, 300, 200], 0.25) == pytest.approx(175.0)


def test_percentile_clamps_p_into_range():
    vals = [100, 200, 300, 400]
    assert percentile(vals, 1.5) == 400.0
    assert percentile(vals, -0.5) == 100.0


def test_percentile_handles_duplicates():
    assert percentile([5, 5, 5, 5], 0.5) == 5.0
    assert percentile([5, 5, 5, 5], 0.9) == 5.0


def test_percentile_ignores_none():
    assert percentile([100, None, 300], 0.5) == pytest.approx(200.0)


# ---------------- representative: zero is not a value ----------------


def test_representative_treats_a_zero_bound_as_absent():
    # A 0 salary is not a real posting value; it must not drag a midpoint to half.
    assert representative({"salary_min": 0, "salary_max": 100}) == 100.0
    assert representative({"salary_min": 0, "salary_max": 0}) is None


# ---------------- mention boundary: "C" vs "C++" ----------------


def test_mentioned_distinguishes_c_from_cpp():
    assert _mentioned("C++", "i write C++ daily")
    assert not _mentioned("C", "i write C++ daily")
    assert _mentioned("C", "i write C daily")
    assert not _mentioned("C++", "i write C daily")


def test_classify_coverage_cpp_is_not_reported_as_c():
    expected = [{"name": "C", "category": "language", "importance": "must"},
                {"name": "C++", "category": "language", "importance": "must"}]
    cov, par, gaps = classify_coverage(expected, set(), "i write c++ daily")
    assert [p["skill"] for p in par] == ["C++"]
    assert [g["skill"] for g in gaps] == ["C"]


# ---------------- filter_samples: currency + location ----------------


def test_filter_treats_a_missing_currency_as_cny():
    samples = [{"title": "Backend Engineer", "salary_min": 1, "salary_max": 2}]
    assert len(filter_samples(samples, role="Backend", currency="CNY")) == 1


def test_filter_location_is_case_insensitive():
    samples = [{"title": "Backend Engineer", "location": "Shanghai",
                "salary_min": 1, "salary_max": 2, "salary_currency": "CNY"}]
    assert len(filter_samples(samples, role="Backend", location="shanghai")) == 1


def test_filter_empty_input_is_empty():
    assert filter_samples([], role="Backend") == []


# ---------------- assess / leverage agreement at the quartile ----------------


def test_negotiation_boundaries_agree():
    # Exactly p75 is "within market" in assess, so leverage must not call it weak.
    assert assess(250, STATS)["verdict"] == "within_market"     # exactly p50
    assert assess(325, STATS)["verdict"] == "within_market"     # exactly p75
    assert leverage(325, STATS) == "moderate"                   # at p75: not yet weak
    assert leverage(326, STATS) == "weak"                       # one unit over
    assert leverage(400, STATS) == "weak"
