"""Unit tests for Offer Comparison (forward Epic 12.3, extended by 12.5).

Compares several offers against one benchmark and picks the one to lead with.
Ranking is by total comp (cash + annualized intrinsic equity); the market verdict
compares base to the benchmark, because the benchmark is base salary.
"""

from app.features.offers import compare_offers

REPORT = {"sampleSize": 4, "currency": "CNY",
          "percentiles": {"min": 100, "p25": 175, "p50": 250, "p75": 325, "max": 400}}


def test_compare_ranks_by_total_comp_and_names_the_best():
    offers = [{"label": "A", "base": 150},
              {"label": "B", "base": 500},
              {"label": "C", "base": 300, "bonus": 100}]
    out = compare_offers(offers, REPORT)
    rows = {r["label"]: r for r in out["offers"]}
    assert rows["C"]["firstYearCash"] == 400
    assert rows["B"]["firstYearCash"] == 500
    assert out["bestByComp"] == "B"          # 500 > 400 > 150


def test_no_equity_means_total_comp_equals_cash():
    row = compare_offers([{"label": "A", "base": 300, "bonus": 50}], REPORT)["offers"][0]
    assert row["annualEquity"] == 0
    assert row["totalComp"] == row["firstYearCash"] == 350


def test_equity_can_change_the_winner():
    offers = [{"label": "Cash", "base": 500000},
              {"label": "Equity", "base": 400000,
               "equity": {"shares": 100000, "strike_price": 1, "current_price": 11,
                          "vest_years": 4}}]
    out = compare_offers(offers, REPORT)
    rows = {r["label"]: r for r in out["offers"]}
    assert rows["Equity"]["annualEquity"] == 250000
    assert rows["Equity"]["totalComp"] == 650000
    assert rows["Cash"]["totalComp"] == 500000
    assert out["bestByComp"] == "Equity"


def test_market_verdict_compares_base_not_total_comp():
    # A big equity grant must not turn a below-market base into "above market".
    offers = [{"label": "BigEquityLowBase", "base": 100,
               "equity": {"shares": 100000, "strike_price": 1, "current_price": 11}}]
    row = compare_offers(offers, REPORT)["offers"][0]
    assert row["assessment"]["verdict"] == "below_market"
    assert row["totalComp"] > 100000


def test_compare_reuses_the_negotiation_verdict_per_offer():
    offers = [{"label": "Low", "base": 150}, {"label": "High", "base": 500}]
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
    assert any("Highest total comp: B" in n for n in out["notes"])


def test_compare_empty_is_honest():
    out = compare_offers([], REPORT)
    assert out["offers"] == [] and out["bestByComp"] is None
    assert any("No offers" in n for n in out["notes"])
