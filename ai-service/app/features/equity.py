"""Equity annualization (forward Epic 12.5).

Annualize a stock grant's *intrinsic* value -- what the shares are worth today above
their strike, spread over the vesting period. This is the number offer comparison
was missing (12.3 ranked cash only).

Deliberately excludes any speculative future price. The service can compute what a
grant is worth *now*; it cannot know what the company's stock will do, so it does not
pretend to. An under-water grant (strike above the current price) is worth zero here,
which is the honest answer.
"""

DEFAULT_VEST_YEARS = 4


def annualized_value(grant: dict) -> dict:
    grant = grant or {}
    shares = int(grant.get("shares") or 0)
    strike = float(grant.get("strike_price") or 0)
    price = float(grant.get("current_price") or 0)
    try:
        years = int(grant.get("vest_years") or DEFAULT_VEST_YEARS) or DEFAULT_VEST_YEARS
    except (TypeError, ValueError):
        years = DEFAULT_VEST_YEARS

    intrinsic = max(0.0, price - strike)
    total = shares * intrinsic

    # A caller may hand over an explicit vesting schedule (weights summing to 1);
    # otherwise the grant is spread evenly across the period.
    schedule = [w for w in (grant.get("schedule") or []) if isinstance(w, (int, float))]
    if schedule and len(schedule) == years and abs(sum(schedule) - 1.0) < 0.01:
        per_year = [round(total * w) for w in schedule]
    else:
        per_year = [round(total / years)] * years

    return {
        "shares": shares,
        "intrinsicPerShare": round(intrinsic, 2),
        "totalValue": round(total),
        "vestYears": years,
        "perYear": per_year,
        "annualValue": round(total / years) if years else 0,
    }
