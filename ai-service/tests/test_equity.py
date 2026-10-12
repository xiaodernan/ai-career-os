"""Unit tests for equity annualization (forward Epic 12.5).

Annualize a grant's intrinsic value. The tests pin the arithmetic, the under-water
case (worth zero), the default spread, and the schedule handling.
"""

from app.features.equity import annualized_value


def test_intrinsic_and_annual_value():
    out = annualized_value({"shares": 10000, "strike_price": 1, "current_price": 11,
                            "vest_years": 4})
    assert out["intrinsicPerShare"] == 10.0
    assert out["totalValue"] == 100000
    assert out["annualValue"] == 25000
    assert out["perYear"] == [25000, 25000, 25000, 25000]


def test_under_water_grant_is_worth_zero():
    out = annualized_value({"shares": 10000, "strike_price": 20, "current_price": 11})
    assert out["intrinsicPerShare"] == 0.0
    assert out["totalValue"] == 0 and out["annualValue"] == 0


def test_default_vest_years_is_four():
    out = annualized_value({"shares": 8000, "strike_price": 0, "current_price": 5})
    assert out["vestYears"] == 4
    assert out["totalValue"] == 40000 and out["annualValue"] == 10000


def test_explicit_schedule_is_used():
    out = annualized_value({"shares": 10000, "strike_price": 0, "current_price": 10,
                            "vest_years": 4, "schedule": [0.1, 0.2, 0.3, 0.4]})
    assert out["perYear"] == [10000, 20000, 30000, 40000]
    assert out["annualValue"] == 25000          # still total / years


def test_a_bad_schedule_falls_back_to_even_split():
    out = annualized_value({"shares": 10000, "strike_price": 0, "current_price": 10,
                            "vest_years": 4, "schedule": [0.5, 0.5]})   # wrong length
    assert out["perYear"] == [25000, 25000, 25000, 25000]


def test_no_shares_is_zero():
    assert annualized_value({})["totalValue"] == 0
    assert annualized_value({})["annualValue"] == 0
