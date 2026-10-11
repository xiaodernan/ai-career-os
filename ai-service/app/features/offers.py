"""Offer Comparison (forward Epic 12.3).

Compare several offers against the salary benchmark for one role and pick the one
to lead with. This reuses the negotiation coach's verdict per offer rather than
re-deriving it, so the single-offer and multi-offer views can never disagree.

Deterministic, and scoped to what the service can actually see: first-year *cash*
(base + bonus). Equity and non-cash terms are deliberately out of the ranking --
their value depends on vesting, strike price and the company's future, none of
which this service knows, and a confident "total comp" number would be a guess.
"""

from app.features.negotiation import assess, leverage


def _stats(report: dict) -> dict:
    return {"count": report.get("sampleSize", 0), **report.get("percentiles", {})}


def compare_offers(offers: list[dict], report: dict, *,
                   match_score: float | None = None) -> dict:
    stats = _stats(report)
    rows: list[dict] = []
    for o in offers:
        base = o.get("base") or 0
        bonus = o.get("bonus") or 0
        rows.append({
            "label": o.get("label", ""),
            "base": base,
            "bonus": bonus,
            "firstYearCash": base + bonus,
            "assessment": assess(base, stats),
            "leverage": leverage(base, stats, match_score),
        })

    best = max(rows, key=lambda r: (r["firstYearCash"], r["base"]), default=None)
    notes: list[str] = []
    if not rows:
        notes.append("No offers to compare.")
    else:
        above = [r["label"] for r in rows if r["assessment"]["verdict"] == "above_market"]
        if above:
            notes.append("Above the market band: " + ", ".join(above))
        if best is not None:
            notes.append(f"Highest first-year cash: {best['label']}.")
    return {
        "currency": report.get("currency", "CNY"),
        "sampleSize": report.get("sampleSize", 0),
        "offers": rows,
        "bestByCash": best["label"] if best else None,
        "notes": notes,
    }
