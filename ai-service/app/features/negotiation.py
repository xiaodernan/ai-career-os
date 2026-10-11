"""Offer Negotiation Coach (forward Epic 12.2).

Given an offer and the salary benchmark for the role (Epic 12.1), assess where
the offer sits, how much leverage it leaves, and what to actually say. The
arithmetic is deterministic -- an offer is an integer and the benchmark is a set
of percentiles, so the verdict is computed, never narrated. This keeps the coach
honest: it never invents a number, and when the benchmark is too thin to support
a claim it says so instead of bluffing.
"""


def _stats(report: dict) -> dict:
    """Flatten a salary-benchmark report into {count, min, p25, p50, p75, max}."""
    return {"count": report.get("sampleSize", 0), **report.get("percentiles", {})}


def assess(offer: float, stats: dict) -> dict:
    """Where the offer sits inside the benchmark, and the distance to the medians."""
    if not stats.get("count"):
        return {"verdict": "unknown", "vsP50Pct": None, "toP50": None, "toP75": None}
    p25, p50, p75 = stats.get("p25"), stats.get("p50"), stats.get("p75")
    if offer < p25:
        verdict = "below_market"
    elif offer > p75:
        verdict = "above_market"
    else:
        verdict = "within_market"
    return {
        "verdict": verdict,
        "vsP50Pct": round((offer / p50 - 1) * 100, 1) if p50 else None,
        "toP50": max(0, round(p50 - offer)) if p50 else 0,
        "toP75": max(0, round(p75 - offer)) if p75 else 0,
    }


def leverage(offer: float, stats: dict, match_score: float | None = None) -> str:
    """How much room the offer leaves: strong / moderate / weak / unknown."""
    if not stats.get("count"):
        return "unknown"
    p25, p50, p75 = stats.get("p25"), stats.get("p50"), stats.get("p75")
    # Strictly above p75 is weak: exactly p75 is still "within market" in assess(),
    # and the two functions must agree on that boundary.
    if p75 is not None and offer > p75:
        return "weak"                      # already above market; base-salary asks are weak
    if p50 is not None and offer >= p50:
        return "moderate"                  # room up to the upper quartile
    strong_match = match_score is not None and match_score >= 0.75
    return "strong" if (strong_match or (p25 is not None and offer < p25)) else "moderate"


def talking_points(offer: float, stats: dict, match_score: float | None = None) -> list[str]:
    """Deterministic, evidence-grounded points to raise -- no invented numbers."""
    if not stats.get("count"):
        return ["Not enough comparable postings to benchmark this offer. Collect two or "
                "three comparable postings (or the recruiter's stated range) before "
                "negotiating."]
    a = assess(offer, stats)
    p50, p75 = stats.get("p50"), stats.get("p75")
    pts: list[str] = []
    if a["verdict"] == "below_market":
        pts.append(f"Your offer is below the lower quartile of comparable postings "
                   f"(median {p50}). Anchor your ask at or above the median.")
    elif a["verdict"] == "within_market":
        pts.append(f"Your offer is inside the market band (median {p50}, upper quartile "
                   f"{p75}). Aim at the upper quartile, not the median.")
    else:
        pts.append(f"Your offer already exceeds the upper quartile ({p75}); more base "
                   f"salary is weak leverage — negotiate scope, equity or start date instead.")
    if a.get("toP50"):
        pts.append(f"Closing to the median is worth about {a['toP50']} more per year.")
    if match_score is not None:
        pct = round(match_score * 100)
        if match_score >= 0.75:
            pts.append(f"Your evidence-based match is {pct}% — cite the specific matched "
                       f"skills when you ask for the upper band.")
        elif match_score < 0.5:
            pts.append(f"Your evidence-based match is {pct}% — lead with the gaps you can "
                       f"close rather than pushing hard on base salary.")
    return pts


def negotiation_plan(offer: int, report: dict, *, match_score: float | None = None,
                     currency: str = "CNY") -> dict:
    stats = _stats(report)
    return {
        "offer": offer,
        "currency": currency,
        "assessment": assess(offer, stats),
        "leverage": leverage(offer, stats, match_score),
        "talkingPoints": talking_points(offer, stats, match_score),
        "benchmark": {"sampleSize": stats["count"],
                      "percentiles": report.get("percentiles", {})},
    }
