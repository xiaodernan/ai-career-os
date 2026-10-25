"""Career Progression Planner (forward Epic 10.11).

"Which roles should I target *next* to get to my dream role?" The growth loop already
answers "am I ready for role X?" (10.7 readiness) and "which families fit me now?"
(10.10 role suggestions). This engine closes the gap between those two: given an
*aspirational* target role, it finds the stepping-stone role families that (a) the
candidate can plausibly land today -- they already cover a meaningful share of that
family's most-demanded skills -- and (b) build the exact skills the dream role is
missing. A good next step is reachable *and* closes real gaps, not one or the other.

Deterministic and evidence-bound: the aspirational role's gaps come from the existing
``gap_analysis`` engine (itself evidence-bound), the families and their demand come
from ``roles.suggest_roles`` over the platform's own postings, and the bridge score is
pure arithmetic over those two sets. Nothing is invented about a role the corpus does
not contain, and the dream-role readiness is reported straight from the gap engine so
the "you are X% there" number is the same one the rest of the product shows.
"""

from app.core.skills import normalize
from app.features import gap_analysis, roles
from app.features.demand import load_job_skill_samples


def build_stepping_stones(families: list[dict], aspirational_gaps: list[str],
                          aspirational_must_gaps: list[str]) -> list[dict]:
    """Pure, deterministic ranking of role families as stepping stones.

    ``families`` is the output of ``roles.suggest_roles`` (already normalised). The
    two gap lists are normalised skill names taken from the aspirational role's gap
    report. A family only qualifies as a stepping stone if working in it would build
    at least one skill the dream role is missing; the score rewards building *must*
    gaps, and is biased by how reachable the family is today (current coverage).
    """
    gap_set = {normalize(g) for g in (aspirational_gaps or [])
               if isinstance(g, str)}
    must_set = {normalize(g) for g in (aspirational_must_gaps or [])
                if isinstance(g, str)}
    stones: list[dict] = []
    for fam in families or []:
        if not isinstance(fam, dict):
            continue
        demands = [normalize(d) for d in (fam.get("topDemands") or []) if isinstance(d, str)]
        builds = [d for d in demands if d in gap_set]
        if not builds:
            continue
        builds_must = [d for d in builds if d in must_set]
        coverage = float(fam.get("coverage", 0.0) or 0.0)
        postings = int(fam.get("postings", 0) or 0)
        # Must-gap closures weigh double; reachability (current coverage) scales the
        # score so a family the candidate can land today beats an equal match they
        # cannot. The 0.5 floor keeps an otherwise-perfect bridge from scoring zero
        # when coverage is low, while still ranking a reachable match above it.
        bridge = (len(builds_must) * 1.0 + len(builds) * 0.5) * (0.5 + coverage)
        stones.append({
            "family": fam.get("family", "other"),
            "currentCoverage": round(coverage, 3),
            "postings": postings,
            "buildsSkills": builds,
            "buildsMustCount": len(builds_must),
            "buildsCount": len(builds),
            "bridgeScore": round(bridge, 3),
            "reason": _reason(fam, builds, builds_must, coverage, postings),
        })
    stones.sort(key=lambda s: (-s["bridgeScore"], -s["postings"], s["family"]))
    return stones


def _reason(fam: dict, builds: list[str], builds_must: list[str],
            coverage: float, postings: int) -> str:
    name = fam.get("family", "this")
    pct = int(round(coverage * 100))
    must_phrase = (f"including {len(builds_must)} hard-requirement skill"
                   f"{'s' if len(builds_must) != 1 else ''} " if builds_must else "")
    return (f"You already cover {pct}% of {name} roles and this family builds "
            f"{must_phrase}{len(builds)} of the skills your dream role is missing "
            f"-- a reachable next step that closes real gaps "
            f"({postings} open postings in the corpus).")


def build_advice(aspirational_coverage: float, stone_count: int,
                aspirational_must_gaps: list[str]) -> list[str]:
    """Deterministic, honest advice lines -- no invented timelines or resources."""
    lines: list[str] = []
    must_gaps = list(aspirational_must_gaps or [])
    if must_gaps:
        lines.append(
            "Your dream role still has " + str(len(must_gaps)) +
            " hard-requirement gap(s): " + ", ".join(must_gaps[:6]) +
            ". Target a stepping stone that builds these first.")
    else:
        lines.append("You already cover the hard requirements for your dream role; "
                     "the remaining gaps are should/nice-to-have.")
    if stone_count:
        lines.append("Prioritise the top stepping stone: it is both reachable today "
                     "and builds the most dream-role skills.")
    else:
        lines.append("No role family in the corpus builds your dream-role gaps while "
                     "remaining reachable -- close a few gaps directly, then re-run.")
    try:
        coverage_value = float(aspirational_coverage or 0.0)
    except (TypeError, ValueError):
        coverage_value = 0.0
    if coverage_value >= 0.8:
        lines.append("You are " + str(int(round(coverage_value * 100))) +
                     "% ready for the dream role; a stepping stone may be optional.")
    return lines


async def plan_progression(*, aspirational_role: str, resume_structured,
                           samples: list[dict] | None = None, seniority=None,
                           user_id=None, run_id=None) -> dict:
    """Orchestrate the progression plan.

    Computes the aspirational role's evidence-bound gap, the candidate's current fit
    across role families, then ranks stepping stones. ``samples`` lets callers inject
    the posting corpus (tests); when omitted it is loaded from the database.
    """
    ap_gap = await gap_analysis.analyze_gap(
        aspirational_role, seniority, resume_structured, "",
        user_id=user_id, run_id=run_id)
    skills = roles.declared_skills(resume_structured)
    if samples is None:
        samples = await load_job_skill_samples()
    fams = roles.suggest_roles(samples, skills, top=20).get("families", [])
    ap_gaps = [g["skill"] for g in ap_gap.get("gaps", [])]
    ap_must = [g["skill"] for g in ap_gap.get("gaps", []) if g.get("importance") == "must"]
    stones = build_stepping_stones(fams, ap_gaps, ap_must)
    coverage = float(ap_gap.get("coverage", 0.0) or 0.0)
    return {
        "aspirationalRole": aspirational_role[:200],
        "seniority": (seniority or ap_gap.get("seniority") or "")[:40],
        "aspirationalCoverage": round(coverage, 3),
        "aspirationalGapCount": int(ap_gap.get("gapCount", 0) or 0),
        "aspirationalMustGaps": ap_must,
        "steppingStones": stones,
        "advice": build_advice(coverage, len(stones), ap_must),
    }
