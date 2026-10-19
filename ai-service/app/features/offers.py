"""Offer Comparison (forward Epic 12.3, extended by 12.5).

Compare several offers against the salary benchmark for one role and pick the one
to lead with. This reuses the negotiation coach's verdict per offer rather than
re-deriving it, so the single-offer and multi-offer views can never disagree.

Ranking is by **total compensation** -- first-year cash (base + bonus) plus the
annualized *intrinsic* equity value from Epic 12.5 (zero when no grant is given, so
a cash-only comparison is unchanged). The market verdict, however, compares **base**
to the benchmark, because the benchmark is base salary: mixing equity into that
comparison would be comparing unlike quantities.
"""

from app.features.equity import annualized_value
from app.features.negotiation import assess, leverage


def _stats(report: dict) -> dict:
    return {"count": (report or {}).get("sampleSize", 0), **(report or {}).get("percentiles", {})}


def compare_offers(offers: list[dict], report: dict, *,
                   match_score: float | None = None) -> dict:
    stats = _stats(report)
    rows: list[dict] = []
    for o in (offers or []):
        if not isinstance(o, dict):
            continue
        base = o.get("base") or 0
        bonus = o.get("bonus") or 0
        cash = base + bonus
        annual_equity = annualized_value(o["equity"])["annualValue"] if o.get("equity") else 0
        rows.append({
            "label": o.get("label", ""),
            "base": base,
            "bonus": bonus,
            "firstYearCash": cash,
            "annualEquity": annual_equity,
            "totalComp": cash + annual_equity,
            "assessment": assess(base, stats),
            "leverage": leverage(base, stats, match_score),
        })

    best = max(rows, key=lambda r: (r["totalComp"], r["firstYearCash"]), default=None)
    notes: list[str] = []
    if not rows:
        notes.append("No offers to compare.")
    else:
        above = [r["label"] for r in rows if r["assessment"]["verdict"] == "above_market"]
        if above:
            notes.append("Above the market band: " + ", ".join(above))
        if best is not None:
            notes.append(f"Highest total comp: {best['label']}.")
    return {
        "currency": report.get("currency", "CNY"),
        "sampleSize": report.get("sampleSize", 0),
        "offers": rows,
        "bestByComp": best["label"] if best else None,
        "notes": notes,
    }
