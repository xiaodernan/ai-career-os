"""Small domain scorers the rest of the features borrow.

`skill_gap` answers "what does the resume lack for this job, and by how much";
`rank_jobs` orders roles for a profile by coverage of the required skills,
with evidence-bearing stable ties (earlier in the input wins). Both are pure
functions over plain dicts/lists so they are trivially testable.
"""

from __future__ import annotations

from typing import Iterable


def skill_gap(have: Iterable[str], need: Iterable[str]) -> dict:
    """The set difference plus the coverage ratio, in the product's own words.

    `coverage` is matched / required (0.0 when nothing is required); the two
    name lists are lowercased, deduplicated and order-preserving.
    """
    def _norm(items: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for raw in items:
            term = str(raw).strip().lower()
            if term and term not in seen:
                seen.add(term)
                out.append(term)
        return out

    have_list = _norm(have)
    need_list = _norm(need)
    have_set = set(have_list)
    matched = [skill for skill in need_list if skill in have_set]
    missing = [skill for skill in need_list if skill not in have_set]
    return {
        "have": have_list,
        "need": need_list,
        "matched": matched,
        "missing": missing,
        "coverage": (len(matched) / len(need_list)) if need_list else 0.0,
    }


def rank_jobs(
    jobs: Iterable[dict],
    profile_skills: Iterable[str],
    k: int | None = None,
) -> list[tuple[dict, float]]:
    """Rank roles by coverage of the required skills.

    Each job must carry ``skills`` (a list of strings). The score is the
    fraction of required skills the profile holds; ties keep input order.
    ``k`` truncates, best first.
    """
    have = {str(s).strip().lower() for s in profile_skills if str(s).strip()}

    def _score(job: dict) -> float:
        required = {str(s).strip().lower() for s in job.get("skills", []) if str(s).strip()}
        if not required:
            return 0.0
        return len(required & have) / len(required)

    scored = [(job, _score(job)) for job in jobs]
    scored.sort(key=lambda item: -item[1])
    return scored if k is None else scored[:k]
