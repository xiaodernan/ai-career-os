"""Skill-progress tracking (forward Epic 10.6).

Compare two gap reports for the same target role over time and say what moved:
which gaps were closed, which improved from gap to partial, which regressed, and
what is still open. This closes the growth loop the product describes -- "skill
gaps feed back into what to learn and what to target next" -- by making the
*change* visible instead of only the current state.

Deterministic: it is a set diff over the two reports' own verdicts. The verdicts
themselves are evidence-bound (Epic 10.1), so "closed" means a skill that was a gap
is now backed by declared evidence -- not that someone ticked a box.
"""

_STATE_RANK = {"gap": 0, "partial": 1, "covered": 2}


def skill_states(report: dict) -> dict[str, str]:
    """skill -> 'covered' | 'partial' | 'gap', from a gap report's own lists."""
    states: dict[str, str] = {}
    for c in (report or {}).get("covered") or []:
        if c.get("skill"):
            states[c["skill"]] = "covered"
    for p in (report or {}).get("partial") or []:
        if p.get("skill") and p["skill"] not in states:
            states[p["skill"]] = "partial"
    for g in (report or {}).get("gaps") or []:
        if g.get("skill") and g["skill"] not in states:
            states[g["skill"]] = "gap"
    return states


def diff_progress(previous: dict | None, current: dict) -> dict:
    prev = skill_states(previous) if previous else {}
    cur = skill_states(current)
    baseline = not previous

    closed = sorted(s for s in prev
                    if _STATE_RANK[prev[s]] < 2 and cur.get(s) == "covered")
    improved = sorted(s for s in prev
                      if prev[s] == "gap" and cur.get(s) == "partial")
    regressed = sorted(s for s in prev
                       if prev[s] == "covered" and cur.get(s) in ("gap", "partial"))
    # "opened" only means something against a baseline; on a first run nothing is new.
    opened = [] if baseline else sorted(s for s in cur
                                        if s not in prev and cur[s] == "gap")
    still_open = sorted(s for s in cur
                        if cur[s] != "covered" and s not in closed and s not in improved)

    prev_cov = float((previous or {}).get("coverage") or 0.0)
    cur_cov = float((current or {}).get("coverage") or 0.0)
    return {
        "targetRole": (current or {}).get("targetRole") or (previous or {}).get("targetRole", ""),
        "baseline": baseline,
        "closed": closed,
        "improved": improved,
        "opened": opened,
        "regressed": regressed,
        "stillOpen": still_open,
        "previousCoverage": round(prev_cov, 3),
        "currentCoverage": round(cur_cov, 3),
        "delta": round(cur_cov - prev_cov, 3),
        "closedCount": len(closed),
        # stillOpen already contains every currently-open skill (an "opened" gap is a
        # gap, so opened ⊆ stillOpen); adding the two would double-count it.
        "openCount": len(still_open),
    }
