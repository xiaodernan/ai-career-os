"""Unit tests for the Offer Negotiation Coach (forward Epic 12.2).

The coach is deterministic: it reads a benchmark (Epic 12.1) and computes where an
offer sits and what to say. These tests pin the arithmetic and the honesty rules --
an empty benchmark must produce advice to gather data, not a fabricated verdict.
"""

import pytest

from app.features.negotiation import (assess, leverage, negotiation_plan,
                                      talking_points)
from app.features.salary import benchmark

# A hand-built benchmark matching percentile([100,200,300,400]) with count 4.
STATS = {"count": 4, "min": 100, "p25": 175, "p50": 250, "p75": 325, "max": 400}
EMPTY = {"count": 0}


# ---------------- assess ----------------


def test_assess_unknown_without_a_sample():
    assert assess(250, EMPTY) == {"verdict": "unknown", "vsP50Pct": None,
                                  "toP50": None, "toP75": None}


def test_assess_below_market():
    a = assess(100, STATS)
    assert a["verdict"] == "below_market"
    assert a["vsP50Pct"] == pytest.approx(-60.0)
    assert a["toP50"] == 150 and a["toP75"] == 225


def test_assess_within_market():
    a = assess(250, STATS)
    assert a["verdict"] == "within_market"
    assert a["vsP50Pct"] == 0.0
    assert a["toP50"] == 0 and a["toP75"] == 75


def test_assess_above_market():
    a = assess(400, STATS)
    assert a["verdict"] == "above_market"
    assert a["toP50"] == 0 and a["toP75"] == 0


# ---------------- leverage ----------------


def test_leverage_unknown_without_a_sample():
    assert leverage(250, EMPTY) == "unknown"


def test_leverage_strong_below_lower_quartile():
    assert leverage(100, STATS) == "strong"


def test_leverage_strong_when_match_is_strong_and_offer_below_median():
    assert leverage(200, STATS, match_score=0.8) == "strong"


def test_leverage_moderate_below_median_without_a_strong_match():
    assert leverage(200, STATS, match_score=0.4) == "moderate"


def test_leverage_moderate_inside_the_upper_half():
    assert leverage(250, STATS) == "moderate"


def test_leverage_weak_above_upper_quartile():
    assert leverage(400, STATS) == "weak"


# ---------------- talking_points ----------------


def test_talking_points_unknown_asks_for_data():
    pts = talking_points(250, EMPTY)
    assert len(pts) == 1 and "not enough comparable postings" in pts[0].lower()


def test_talking_points_below_market_states_the_gap():
    pts = talking_points(100, STATS)
    assert "below the lower quartile" in pts[0]
    assert any("about 150 more per year" in p for p in pts)


def test_talking_points_within_market_aims_at_upper_quartile():
    pts = talking_points(250, STATS)
    assert "inside the market band" in pts[0]


def test_talking_points_above_market_redirects_leverage():
    pts = talking_points(400, STATS)
    assert "exceeds the upper quartile" in pts[0]


def test_talking_points_cite_a_strong_match():
    pts = talking_points(100, STATS, match_score=0.8)
    assert any("80%" in p for p in pts)


def test_talking_points_soften_on_a_weak_match():
    pts = talking_points(100, STATS, match_score=0.3)
    assert any("30%" in p for p in pts)


# ---------------- negotiation_plan ----------------


def test_negotiation_plan_composes_and_carries_the_benchmark():
    report = {"sampleSize": 4, "percentiles": {"min": 100, "p25": 175, "p50": 250,
                                               "p75": 325, "max": 400}}
    plan = negotiation_plan(100, report, match_score=0.8, currency="CNY")
    assert plan["offer"] == 100 and plan["currency"] == "CNY"
    assert plan["assessment"]["verdict"] == "below_market"
    assert plan["leverage"] == "strong"
    assert plan["benchmark"]["sampleSize"] == 4
    assert plan["benchmark"]["percentiles"]["p50"] == 250
    assert plan["talkingPoints"]


def test_negotiation_plan_on_an_empty_benchmark_is_honest():
    plan = negotiation_plan(100, {"sampleSize": 0, "percentiles": {}})
    assert plan["assessment"]["verdict"] == "unknown"
    assert plan["leverage"] == "unknown"
    assert plan["benchmark"]["sampleSize"] == 0
    assert "not enough" in plan["talkingPoints"][0].lower()


# ---------------- integration with the salary benchmark ----------------


def test_negotiation_plan_reads_a_real_benchmark():
    samples = [
        {"title": "Backend Engineer", "location": "Beijing", "experience_years": 3,
         "salary_min": 300000, "salary_max": 400000, "salary_currency": "CNY"},
        {"title": "Senior Backend Engineer", "location": "Shanghai", "experience_years": 6,
         "salary_min": 500000, "salary_max": 700000, "salary_currency": "CNY"},
        {"title": "Backend Engineer", "location": "Shenzhen", "experience_years": 4,
         "salary_min": 400000, "salary_max": 500000, "salary_currency": "CNY"},
    ]
    report = benchmark(samples, role="Backend Engineer", currency="CNY")
    plan = negotiation_plan(350000, report)
    assert plan["benchmark"]["sampleSize"] == report["sampleSize"] == 3
    # 350k sits between the 350k-low midpoint and the 600k-high midpoint -> not above market
    assert plan["assessment"]["verdict"] in ("within_market", "below_market")
    assert plan["leverage"] in ("strong", "moderate")
