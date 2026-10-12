"""Market skill demand (forward Epic 10.9).

The gap analysis (10.1) is resume-centric: what *you* are missing for a role. This is
the market-centric half: across the postings the platform holds, which skills does a
role family actually ask for, and how often. Together they answer "the market wants
Kubernetes (68% of backend postings); you have no evidence of it."

Deterministic -- it counts the `skills` array the postings already carry. The share is
over postings that list at least one skill, so a sparse row does not dilute the
denominator.
"""

from collections import Counter

from app.core import db
from app.core.skills import normalize
from app.features.salary import _role_tokens   # one author for role tokenisation


def skill_demand(samples: list[dict], *, role: str = "", location: str | None = None,
                 top: int = 15) -> dict:
    tokens = _role_tokens(role)
    counter: Counter[str] = Counter()
    postings = 0
    for s in samples:
        title = (s.get("title") or "").lower()
        if tokens and not any(t in title for t in tokens):
            continue
        if location and location.lower() not in (s.get("location") or "").lower():
            continue
        skills = [sk for sk in (s.get("skills") or []) if isinstance(sk, str) and sk.strip()]
        if not skills:
            continue
        postings += 1
        for sk in skills:
            counter[normalize(sk)] += 1

    ranked = [{"skill": sk, "count": c, "share": round(c / postings, 3) if postings else 0.0}
              for sk, c in counter.most_common(max(0, top))]
    return {"role": role, "location": location or "", "postings": postings, "skills": ranked}


async def load_job_skill_samples() -> list[dict]:
    rows = await db.fetch(
        "SELECT title, location, skills FROM jobs WHERE status = 'open'")
    return [dict(r) for r in rows]
