"""Market-weighted gap prioritization (forward Epic 10.12).

The learning plan (10.5) turns a gap report into phased study items, but it treats
every gap the same -- it does not say *which* missing skill to close first. This engine
does: it enriches each gap with how much the market actually asks for that skill (the
10.9 demand engine, over the platform's own postings for the role family) and ranks
gaps by importance and market pull. "You are missing Kubernetes *and* Docker; the
market asks for Kubernetes in 68% of backend postings vs Docker in 31% -- learn
Kubernetes first." Decision-useful and honest: a skill the corpus does not list gets a
market share of zero, not a guessed number.

Deterministic and evidence-bound: the gaps come from the evidence-bound ``gap_analysis``
engine and the demand from the postings the platform holds. Nothing is inferred about a
role the corpus does not contain.
"""

from app.core.skills import normalize
from app.features import gap_analysis
from app.features.demand import load_job_skill_samples, skill_demand

_IMPORTANCE_ORDER = {"must": 0, "should": 1, "nice": 2}


def _priority_label(importance: str, share: float) -> str:
    """Deterministic priority band from importance and market share.

    A hard requirement the market heavily wants is ``critical``; everything else tiers
    down by whether the market wants it at all (>=30% / >=10%) or not.
    """
    if importance == "must" and share >= 0.3:
        return "critical"
    if importance == "must" or share >= 0.3:
        return "high"
    if share >= 0.1:
        return "medium"
    return "low"


def rank_gap_priorities(gaps: list[dict], demand_skills: list[dict],
                        postings: int) -> list[dict]:
    """Pure: attach market demand to each gap and rank by importance then demand.

    ``gaps`` is ``analyze_gap``'s ``gaps`` list (``{skill, importance, category}``);
    ``demand_skills`` is ``skill_demand``'s ``skills`` list (``{skill, count, share}``)
    for the same role family; ``postings`` is the demand's posting count. A gap skill
    absent from ``demand_skills`` is reported with ``marketShare: 0.0`` -- the corpus
    simply does not list it among the family's demanded skills.
    """
    demand_map = {normalize(d["skill"]): d for d in (demand_skills or [])}
    out: list[dict] = []
    for g in gaps or []:
        key = normalize(g["skill"])
        d = demand_map.get(key)
        share = float(d["share"]) if d else 0.0
        out.append({
            "skill": g["skill"],
            "importance": g.get("importance", "should"),
            "category": g.get("category", "other"),
            "marketShare": round(share, 3),
            "marketPostings": int(postings or 0),
            "marketRank": int(d["count"]) if d else 0,
            "priority": _priority_label(g.get("importance", "should"), share),
        })
    out.sort(key=lambda x: (_IMPORTANCE_ORDER.get(x["importance"], 1),
                            -x["marketShare"], x["skill"].lower()))
    return out


async def plan_learning_priority(*, target_role: str, resume_structured,
                                 samples: list[dict] | None = None, seniority=None,
                                 user_id=None, run_id=None) -> dict:
    """Orchestrate the learning-priority plan.

    Computes the evidence-bound gap for the target role, then the market demand for
    that role family, and ranks the gaps. ``samples`` lets callers inject the posting
    corpus (tests); when omitted it is loaded from the database.
    """
    gap = await gap_analysis.analyze_gap(
        target_role, seniority, resume_structured, "",
        user_id=user_id, run_id=run_id)
    if samples is None:
        samples = await load_job_skill_samples()
    demand = skill_demand(samples, role=target_role, top=200)
    ranked = rank_gap_priorities(gap.get("gaps", []), demand.get("skills", []),
                                 demand.get("postings", 0))
    return {
        "targetRole": target_role[:200],
        "seniority": (seniority or gap.get("seniority") or "")[:40],
        "gapCount": len(ranked),
        "coverage": float(gap.get("coverage", 0.0) or 0.0),
        "marketPostings": int(demand.get("postings", 0) or 0),
        "prioritizedGaps": ranked,
        "topPriority": ranked[0] if ranked else None,
    }
