"""Job-search analytics (forward Epic 15).

Three deterministic, evidence-bound lenses over the candidate's own application
history -- no model, no invented numbers:

* 15.1 **pipeline funnel** -- how many applications reached each stage
  (applied -> OA -> interview -> final round -> offer), with conversion % at each
  step, so a candidate can see *where* the pipeline leaks.
* 15.2 **response rate & time-in-stage** -- of everything submitted, what fraction
  got any reply (including a rejection), what fraction reached an interview / offer,
  and how long each stage took on average and at the median.
* 15.3 **weekly insight digest** -- the stalled applications (submitted or saved but
  silent past a window), the live stage distribution, the headline rates, and an
  optional composition hook for growth deltas and top matches from the other engines.

The input is a list of application records (dicts). The engine never assumes a
particular DB schema: every field is optional except ``id`` and ``status``. Stage
timestamps are ISO strings (with or without timezone, or date-only); anything
unparseable is simply ignored for the time-in-stage math rather than crashing the
report. This is the same "compute it, don't narrate it" rule the rest of the
product follows, and it keeps the whole suite offline-verifiable.

The stage timestamps -- ``oa_at``, ``interview_at``, ``final_round_at``,
``offer_at`` -- are the moment each stage was first *entered*, which the sender reads
out of the status-transition log, because an application row stores only the status it
is at now. A row that never reached a stage carries no key for it, so that stage's
sample simply does not include the row: the durations are measured from transitions the
candidate's own history records, never from a date the engine guessed.

Note on ``rejected``: the *funnel* still credits a rejected application to ``applied``
only, because its current status is the only stage the row itself can vouch for as a
position. The *durations* are not bound by that: a candidate who reached an interview
and was turned down afterwards has an ``interview_at`` in the log, and the time it took
is a fact about their pipeline whether or not it ended in a no. The two lenses answer
different questions -- where a row stands, and how long each step took -- and are
deliberately not forced to agree.
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import median

# Canonical, ordered pipeline. "reached stage X" means the application's furthest
# stage is X or any stage after it.
PIPELINE = ["applied", "oa", "interview", "final_round", "offer"]

# Progressive status -> pipeline index. "reached stage X" means the application's
# furthest stage is X or any earlier one (you cannot reach interview without first
# reaching applied + OA). ``rejected`` is handled separately: it means the candidate
# *was* submitted (reached applied) but the data carries no stage history, so it is
# credited to ``applied`` only -- never to a later stage it may or may not have hit.
_PROGRESSIVE = {
    "applied": 0,
    "oa": 1,
    "interview": 2,
    "final_round": 3,
    "offer": 4,
}
SUBMITTED_STATUSES = set(_PROGRESSIVE) | {"rejected"}


def _parse_dt(value) -> datetime | None:
    """Best-effort ISO parse; unparseable -> None (not an error)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip().replace("Z", "+00:00")
        dt = None
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            try:
                dt = datetime.fromisoformat(s + "T00:00:00+00:00")
            except ValueError:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _index(status: str | None) -> int | None:
    return _PROGRESSIVE.get((status or "").lower())


def _norm(apps: list[dict]) -> list[dict]:
    return [a for a in (apps or []) if isinstance(a, dict) and a.get("id") is not None]


# ---------------- 15.1 pipeline funnel ----------------


def pipeline_funnel(applications: list[dict]) -> dict:
    """Counts reaching each pipeline stage, plus conversion % at every step.

    ``reached[stage]`` counts applications whose furthest stage is that stage or any
    later one. ``saved`` apps are pre-pipeline interest and reported separately;
    ``rejected`` counts as having reached ``applied`` only (see module docstring).
    """
    apps = _norm(applications)
    total = len(apps)
    saved = sum(1 for a in apps if (a.get("status") or "").lower() == "saved")
    rejected = sum(1 for a in apps if (a.get("status") or "").lower() == "rejected")

    reached: dict[str, int] = {stage: 0 for stage in PIPELINE}
    for a in apps:
        st = (a.get("status") or "").lower()
        if st == "rejected":
            # submitted but no stage history -> credit applied only (see module docstring)
            reached["applied"] += 1
            continue
        idx = _index(st)
        if idx is None:
            continue
        # an application at stage idx reached every stage from applied up to idx
        for i in range(0, idx + 1):
            reached[PIPELINE[i]] += 1

    applied_count = reached["applied"]
    stages: list[dict] = []
    prev = None
    for stage in PIPELINE:
        count = reached[stage]
        conv_from_applied = round(count / applied_count, 4) if applied_count else 0.0
        step_conv = (round(count / prev, 4) if (prev not in (None, 0)) else None)
        stages.append({
            "stage": stage,
            "count": count,
            "conversionFromApplied": conv_from_applied,
            "stepConversion": step_conv,
        })
        prev = count if count else prev  # keep denominator meaningful (skip empty stages)

    return {
        "pipeline": stages,
        "appliedCount": applied_count,
        "savedCount": saved,
        "rejectedCount": rejected,
        "totalApplications": total,
    }


# ---------------- 15.2 response rate & time-in-stage ----------------


def _days_between(start: datetime | None, end: datetime | None, now: datetime) -> float | None:
    if start is None or end is None:
        return None
    s = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
    e = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
    ref = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    lo, hi = sorted([s, e])
    return max(0.0, (hi - lo).total_seconds() / 86400.0)


def _summarize_durations(values: list[float]) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"avgDays": None, "medianDays": None, "n": 0}
    return {
        "avgDays": round(sum(vals) / len(vals), 2),
        "medianDays": round(float(median(vals)), 2),
        "n": len(vals),
    }


def response_rate(applications: list[dict], now: datetime | None = None) -> dict:
    """Reply / interview / offer rates and per-stage durations.

    ``responseRate`` is the fraction of submitted applications that got *any* reply
    (reaching OA or later, or a rejection) -- a no is still a response. ``offerRate``
    and ``interviewRate`` are the fractions that reached those stages. ``timeInStage``
    reports avg/median days from submission to each reached stage; applications
    missing the relevant timestamps are simply omitted from that stage's ``n``.
    """
    apps = _norm(applications)
    ref = now or datetime.now(timezone.utc)
    submitted = [a for a in apps
                 if (a.get("status") or "").lower() in SUBMITTED_STATUSES]
    applied_count = len(submitted)
    if applied_count == 0:
        return {
            "appliedCount": 0, "respondedCount": 0, "responseRate": 0.0,
            "offerCount": 0, "offerRate": 0.0, "interviewCount": 0,
            "interviewRate": 0.0, "timeInStage": {},
        }

    reached = {stage: 0 for stage in PIPELINE}
    rejected_count = 0
    for a in submitted:
        st = (a.get("status") or "").lower()
        if st == "rejected":
            rejected_count += 1
            continue
        idx = _index(st)
        for i in range(0, idx + 1):
            reached[PIPELINE[i]] += 1

    responded = reached["oa"] + rejected_count  # past screen OR a post-apply no

    stage_durations: dict[str, list[float]] = {
        "oa": [], "interview": [], "final_round": [], "offer": []
    }
    for a in submitted:
        applied_at = _parse_dt(a.get("applied_at"))
        for stage, key in (("oa", "oa_at"), ("interview", "interview_at"),
                           ("final_round", "final_round_at"), ("offer", "offer_at")):
            d = _days_between(applied_at, _parse_dt(a.get(key)), ref)
            if d is not None:
                stage_durations[stage].append(d)

    time_in_stage = {k: _summarize_durations(v) for k, v in stage_durations.items()}

    return {
        "appliedCount": applied_count,
        "respondedCount": responded,
        "responseRate": round(responded / applied_count, 4),
        "offerCount": reached["offer"],
        "offerRate": round(reached["offer"] / applied_count, 4),
        "interviewCount": reached["interview"],
        "interviewRate": round(reached["interview"] / applied_count, 4),
        "timeInStage": time_in_stage,
    }


# ---------------- 15.3 weekly insight digest ----------------


def insight_digest(applications: list[dict], *, now: datetime | None = None,
                   stale_days: int = 14, growth_deltas: list[dict] | None = None,
                   top_matches: list[dict] | None = None) -> dict:
    """A single weekly snapshot: what is stuck, what is live, and the headline rates.

    ``stalled`` = applications still at ``applied`` or ``saved`` with no movement
    past ``stale_days``. Last activity is the most recent of ``applied_at`` /
    ``created_at`` / ``last_seen`` -- the row's own timestamps plus the last moment
    anything was written to it, which is what the number is named for. Without any
    of them the application is treated as staleness-unknown and is excluded from the
    stalled list (we do not fabricate "it's been 200 days").
    ``growthDeltas`` / ``topMatches`` are echoed through when supplied so the digest
    is a composition point for the growth engines, never a source of invented data.
    """
    apps = _norm(applications)
    ref = now or datetime.now(timezone.utc)

    funnel = pipeline_funnel(apps)
    rates = response_rate(apps, now=ref)

    stalled: list[dict] = []
    for a in apps:
        status = (a.get("status") or "").lower()
        if status not in ("applied", "saved"):
            continue
        applied_at = _parse_dt(a.get("applied_at"))
        created_at = _parse_dt(a.get("created_at"))
        last_seen = _parse_dt(a.get("last_seen"))
        last = max([d for d in (applied_at, created_at, last_seen) if d is not None],
                   default=None)
        if last is None:
            continue
        age = _days_between(last, ref, ref)
        if age is None or age <= stale_days:
            continue
        stalled.append({
            "id": a.get("id"),
            "title": a.get("title"),
            "company": a.get("company"),
            "status": status,
            "daysSinceLastActivity": int(round(age)),
        })
    stalled.sort(key=lambda x: x["daysSinceLastActivity"], reverse=True)

    active = sum(1 for a in apps if (a.get("status") or "").lower()
                 not in ("saved", "rejected"))

    signals: list[str] = []
    if funnel["appliedCount"] == 0:
        signals.append("No submitted applications yet -- the funnel is empty.")
    elif rates["responseRate"] == 0.0:
        signals.append("No replies recorded; check that application statuses are kept current.")
    if stalled:
        signals.append(f"{len(stalled)} application(s) have gone quiet past {stale_days} days.")
    if rates["offerRate"] and rates["offerRate"] > 0:
        signals.append(f"Offer rate is {round(rates['offerRate'] * 100)}% of submitted applications.")

    out: dict = {
        "generatedAt": ref.isoformat(),
        "windowDays": stale_days,
        "totalApplications": funnel["totalApplications"],
        "activePipeline": active,
        "stageCounts": {s["stage"]: s["count"] for s in funnel["pipeline"]},
        "responseRate": rates["responseRate"],
        "offerRate": rates["offerRate"],
        "stalledCount": len(stalled),
        "stalled": stalled,
        "signals": signals,
    }
    if growth_deltas is not None:
        out["growthDeltas"] = growth_deltas
    if top_matches is not None:
        out["topMatches"] = top_matches
    return out
