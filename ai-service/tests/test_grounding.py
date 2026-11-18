"""The shared digit-run verifier (Epic 323) — one rule for every grounded node."""

from app.features import grounding


def test_full_width_digits_fold_to_their_ascii_forms():
    assert grounding.digit_runs("１个申请沉寂２６天") == {"1", "26"}
    assert grounding.digit_runs("回复率０．０％") == {"0.0"}


def test_thousands_separators_match_the_bare_number_the_snapshot_carries():
    # The snapshot serialises money as 300000 — the verifier must see 300,000 as the same number.
    assert grounding.digit_runs("$300,000 total") == {"300000"}
    assert grounding.digit_runs("1,234,567") == {"1234567"}


def test_percent_sign_is_stripped():
    assert grounding.digit_runs("at 54.7% with 7") == {"54.7", "7"}


def test_grounded_needs_at_least_one_snapshot_digit():
    digits = grounding.snapshot_digits({"responseRate": 0.0, "totalApplications": 3})
    assert grounding.grounded("3 applications, 0.0% response", digits)
    assert not grounding.grounded("everything is amazing", digits)
    assert not grounding.grounded("92.5% of readers order hotpot", digits)
