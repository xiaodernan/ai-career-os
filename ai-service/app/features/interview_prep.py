"""Interview prep plan (forward Epic 10.13).

The live interview coach (``app/features/interview.py``) is adaptive -- it picks each
next question from the candidate's answers. This engine is the *pre-interview*
checklist that complements it: given a target role and the candidate's own material,
it says what to study (the gaps, ordered by importance), what to rehearse (the STAR
stories that already evidence the covered skills, so the candidate reaches for their
strongest concrete work first), and what topics are likely to come up (the role's
responsibilities plus the gaps they should be ready to address). Every line is built
from the evidence-bound gap report and the candidate's own story bank -- nothing
invented, no new claims about the candidate.
"""

from app.core.skills import normalize
from app.features import gap_analysis, stories

_IMPORTANCE_ORDER = {"must": 0, "should": 1, "nice": 2}


def _strongest_story_for(skill: str, story_list: list[dict]) -> dict | None:
    """The strongest story (quantified, then most-evidenced) that evidences ``skill``."""
    key = normalize(skill)
    matches = [s for s in story_list
               if key in {normalize(x) for x in s.get("skills", [])}]
    if not matches:
        return None
    matches.sort(key=lambda s: (not s["quantified"], -len(s["skills"]), -len(s["bullets"])))
    return matches[0]


def build_prep_plan(gap_report: dict, story_bank: dict) -> dict:
    """Pure: assemble the pre-interview checklist from a gap report + story bank."""
    gaps = sorted(
        (g for g in ((gap_report or {}).get("gaps") or []) if isinstance(g, dict)),
        key=lambda g: (_IMPORTANCE_ORDER.get(g.get("importance", "should"), 1),
                       (g.get("skill") or "").lower()))
    weak_areas = [{
        "skill": g.get("skill", "unknown"),
        "importance": g.get("importance", "should"),
        "action": (f"Build evidence for {g.get('skill', 'this skill')}: add a project "
                   f"or a quantified bullet demonstrating it before the interview."),
    } for g in gaps]

    stories_list = (story_bank or {}).get("stories") or []
    strength_stories: list[dict] = []
    for c in (gap_report or {}).get("covered") or []:
        sk = c.get("skill", "")
        st = _strongest_story_for(sk, stories_list)
        strength_stories.append({
            "skill": sk,
            "evidence": c.get("evidence", ""),
            "storyTitle": (st or {}).get("title") if st else None,
            "storyId": (st or {}).get("id") if st else None,
            "quantified": bool((st or {}).get("quantified")) if st else False,
        })

    topics = list((gap_report or {}).get("responsibilities") or [])
    for g in gaps:
        topics.append(f"Be ready to address your gap in {g.get('skill', 'this skill')}")
    topics = topics[:12]

    return {
        "targetRole": ((gap_report or {}).get("targetRole") or "")[:200],
        "coverage": float((gap_report or {}).get("coverage", 0.0) or 0.0),
        "weakAreaCount": len(weak_areas),
        "strengthStoryCount": sum(1 for s in strength_stories if s["storyId"]),
        "weakAreas": weak_areas,
        "strengthStories": strength_stories,
        "likelyTopics": topics,
        "storyBankSize": int((story_bank or {}).get("count", 0) or 0),
    }


async def plan_interview_prep(*, target_role: str, resume_structured, seniority=None,
                              user_id=None, run_id=None) -> dict:
    """Orchestrate the prep plan: evidence-bound gap + the candidate's story bank."""
    gap = await gap_analysis.analyze_gap(
        target_role, seniority, resume_structured, "",
        user_id=user_id, run_id=run_id)
    story_bank = stories.build_story_bank(resume_structured)
    return build_prep_plan(gap, story_bank)
