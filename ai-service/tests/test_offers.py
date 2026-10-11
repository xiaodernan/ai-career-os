"""Unit tests for Offer Comparison (forward Epic 12.3).

Compares several offers against one benchmark and picks the one to lead with. The
verdict per offer must be the negotiation coach's own, and the ranking must be
first-year cash only -- equity and non-cash terms are deliberately out of scope.
"""

from app.features.offers import compare_offers

REPORT = {"sampleSize": 4, "currency": "CNY",
          "percentiles": {"min": 100, "p25": 175, "p50": 250, "p75": 325, "max": 400}}


def test_compare_ranks_by_first_year_cash_and_names_the_best():
    offers = [{"label": "A", "base": 150},
              {"label": "B", "base": 500},
              {"label": "C", "base": 300, "bonus": 100}]
    out = compare_offers(offers, REPORT)
    rows = {r["label"]: r for r in out["offers"]}
    assert rows["C"]["firstYearCash"] == 400
    assert rows["B"]["firstYearCash"] == 500
    assert out["bestByCash"] == "B"          # 500 > 400 > 150


def test_compare_reuses_the_negotiation_verdict_per_offer():
    offers = [{"label": "Low", "base": 150},
              {"label": "High", "base": 500}]
    rows = {r["label"]: r for r in compare_offers(offers, REPORT)["offers"]}
    assert rows["Low"]["assessment"]["verdict"] == "below_market"
    assert rows["Low"]["leverage"] == "strong"
    assert rows["High"]["assessment"]["verdict"] == "above_market"
    assert rows["High"]["leverage"] == "weak"


def test_compare_carries_currency_and_sample_size():
    out = compare_offers([{"label": "A", "base": 200}], REPORT)
    assert out["currency"] == "CNY" and out["sampleSize"] == 4


def test_compare_notes_above_market_and_the_best():
    offers = [{"label": "A", "base": 150}, {"label": "B", "base": 500}]
    out = compare_offers(offers, REPORT)
    assert any("Above the market band" in n and "B" in n for n in out["notes"])
    assert any("Highest first-year cash: B" in n for n in out["notes"])


def test_compare_ignores_non_cash_terms():
    # Equity must not enter the ranking: its value depends on vesting and the
    # company's future, which this service cannot see.
    out = compare_offers([{"label": "A", "base": 100, "bonus": 0, "equity": 9_999_999}],
                         REPORT)
    assert out["offers"][0]["firstYearCash"] == 100


def test_compare_empty_is_honest():
    out = compare_offers([], REPORT)
    assert out["offers"] == [] and out["bestByCash"] is None
    assert any("No offers" in n for n in out["notes"])
