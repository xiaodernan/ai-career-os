"""Salary & Compensation Intelligence (forward Epic 12.1).

Benchmark a target role against the postings the platform actually holds, and
position a candidate's number inside that distribution. This is deliberately
*deterministic*: salaries are integers the database already stores, so the
percentiles are computed here rather than narrated by a model -- the same rule
the rest of the product follows ("where a score can be computed without an LLM,
it is computed; the model narrates, it does not decide the arithmetic").

Every report carries the postings it drew from (`evidence`) and the sample size,
so a benchmark is auditable back to the rows behind it. Salary units follow the
repo convention: the currency's base unit per year (for CNY, 元/年).
"""

import math
import re

from app.core import db

# Role words that carry no signal on their own -- stripping them keeps "Senior
# Backend Engineer" from matching every posting whose title contains "engineer".
GENERIC_ROLE_TOKENS = {
    "engineer", "engineers", "developer", "developers", "programmer",
    "senior", "junior", "staff", "lead", "principal", "head", "manager",
    "岗位", "工程师", "开发", "开发工程师", "高级", "资深", "初级", "中级",
}

# Seniority word -> inclusive years-of-experience band. Absent/unknown seniority
# applies no band at all (an unknown must not silently exclude a posting).
SENIORITY_YEARS: dict[str, tuple[int, int]] = {
    "junior": (0, 2), "entry": (0, 2), "初级": (0, 2),
    "mid": (2, 5), "middle": (2, 5), "中级": (2, 5),
    "senior": (5, 9), "高级": (5, 9), "资深": (5, 9),
    "staff": (8, 99), "lead": (8, 99), "principal": (8, 99),
}


def percentile(values: list[float], p: float) -> float | None:
    """Linear-interpolation percentile (the numpy/tukey convention).

    Sorts internally and clamps ``p`` to [0, 1], so a caller that hands over an
    unsorted list or a stray ``p`` gets the right answer instead of a silently wrong
    one or an ``IndexError``. The internal callers already pass sorted values and a
    p in range, so this only closes the footgun for the next caller.
    """
    vals = sorted(v for v in values if v is not None)
    n = len(vals)
    if n == 0:
        return None
    if n == 1:
        return float(vals[0])
    p = min(1.0, max(0.0, p))
    rank = (n - 1) * p
    lo, hi = math.floor(rank), math.ceil(rank)
    if lo == hi:
        return float(vals[lo])
    return vals[lo] + (vals[hi] - vals[lo]) * (rank - lo)


def representative(row: dict) -> float | None:
    """A posting's single comparable number: the midpoint of its range, or the one
    bound it has. None when the posting carries no salary at all."""
    lo, hi = row.get("salary_min"), row.get("salary_max")
    if lo and hi:
        return (lo + hi) / 2
    if lo:
        return float(lo)
    if hi:
        return float(hi)
    return None


def summarize(values: list[float]) -> dict:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return {"count": 0}
    return {
        "count": len(vals),
        "min": round(vals[0]),
        "p25": round(percentile(vals, 0.25)),
        "p50": round(percentile(vals, 0.5)),
        "p75": round(percentile(vals, 0.75)),
        "max": round(vals[-1]),
    }


def _role_tokens(role: str) -> list[str]:
    """Significant role words. Falls back to *all* tokens (then the raw string) so a
    role made only of generic words still filters by something rather than nothing."""
    tokens = [t for t in re.split(r"[^0-9A-Za-z\u4e00-\u9fff]+", (role or "").lower()) if t]
    significant = [t for t in tokens if len(t) >= 3 and t not in GENERIC_ROLE_TOKENS]
    if significant:
        return significant
    return [t for t in tokens if len(t) >= 2] or tokens


def filter_samples(samples: list[dict], *, role: str = "", location: str | None = None,
                   seniority: str | None = None, currency: str | None = None) -> list[dict]:
    tokens = _role_tokens(role)
    ymin, ymax = SENIORITY_YEARS.get((seniority or "").lower(), (None, None))
    out: list[dict] = []
    for s in samples:
        if representative(s) is None:
            continue
        title = (s.get("title") or "").lower()
        if tokens and not any(t in title for t in tokens):
            continue
        if location and location.lower() not in (s.get("location") or "").lower():
            continue
        if currency and (s.get("salary_currency") or "CNY").upper() != currency.upper():
            continue
        years = s.get("experience_years")
        if ymin is not None and years is not None and not (ymin <= years <= ymax):
            continue
        out.append(s)
    return out


def position(target: float, values: list[float]) -> dict:
    """Where `target` sits inside the sample: percentile rank + a plain verdict."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return {"percentile": None, "verdict": "unknown"}
    below = sum(1 for v in vals if v < target)
    pct = round(100 * below / len(vals), 1)
    if target < percentile(vals, 0.25):
        verdict = "below_market"
    elif target > percentile(vals, 0.75):
        verdict = "above_market"
    else:
        verdict = "within_market"
    return {"percentile": pct, "verdict": verdict}


def benchmark(samples: list[dict], *, role: str, location: str | None = None,
              seniority: str | None = None, target_salary: int | None = None,
              currency: str = "CNY", max_evidence: int = 10) -> dict:
    matched = filter_samples(samples, role=role, location=location,
                             seniority=seniority, currency=currency)
    vals = [representative(s) for s in matched]
    summary = summarize(vals)
    result: dict = {
        "role": role,
        "location": location or "",
        "seniority": seniority or "",
        "currency": currency,
        "sampleSize": summary.get("count", 0),
        "percentiles": {k: summary[k] for k in ("min", "p25", "p50", "p75", "max")
                        if k in summary},
        "evidence": [{"title": s.get("title"), "location": s.get("location"),
                      "salaryMin": s.get("salary_min"), "salaryMax": s.get("salary_max"),
                      "currency": s.get("salary_currency") or currency}
                     for s in matched[:max_evidence]],
    }
    if target_salary:
        result["position"] = position(float(target_salary), vals)
    if not summary.get("count"):
        result["note"] = ("No comparable open postings carry a salary in this currency. "
                          "Broaden the role or location; the benchmark needs at least one.")
    return result


async def load_job_samples() -> list[dict]:
    """Open postings that carry any salary. ai-service reads domain tables (it does
    not own them); the backend owns the writes."""
    rows = await db.fetch(
        "SELECT title, location, remote_type, employment_type, experience_years, "
        "salary_min, salary_max, salary_currency FROM jobs "
        "WHERE status = 'open' AND (salary_min IS NOT NULL OR salary_max IS NOT NULL)")
    return [dict(r) for r in rows]
