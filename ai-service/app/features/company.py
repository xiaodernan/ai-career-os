"""Company intelligence (forward Epic 4.8).

Given a company name, summarise what the platform actually holds: its open roles, the
skills those roles ask for most, and the salary band they advertise. Deterministic and
evidence-bound -- it reports the corpus, it does not scrape a company page or invent a
profile. Every number is a count or a percentile over rows the database already has.
"""

from collections import Counter

from app.core import db
from app.core.skills import normalize
from app.features.salary import percentile, representative


def company_brief(samples: list[dict], company: str, *, top: int = 10) -> dict:
    name = (company or "").strip().lower()
    matched = [s for s in samples
               if (s.get("company") or "").strip().lower() == name]
    if not matched and name:
        # fall back to a substring so "Acme" still finds "Acme Corp"
        matched = [s for s in samples if name in (s.get("company") or "").lower()]

    roles = sorted({(s.get("title") or "").strip() for s in matched
                    if (s.get("title") or "").strip()})
    counter: Counter[str] = Counter()
    for s in matched:
        for sk in s.get("skills") or []:
            if isinstance(sk, str) and sk.strip():
                counter[normalize(sk)] += 1

    salaries = sorted(v for v in (representative(s) for s in matched) if v is not None)
    band = None
    if salaries:
        band = {
            "min": round(salaries[0]),
            "p50": round(percentile(salaries, 0.5)),
            "max": round(salaries[-1]),
            "currency": matched[0].get("salary_currency") or "CNY",
        }

    return {
        "company": company,
        "postings": len(matched),
        "roles": roles[:max(0, top)],
        "topSkills": [{"skill": sk, "count": c} for sk, c in counter.most_common(max(0, top))],
        "salaryBand": band,
    }


async def load_company_samples() -> list[dict]:
    rows = await db.fetch(
        "SELECT j.title, j.location, j.skills, j.salary_min, j.salary_max, "
        "j.salary_currency, c.name AS company FROM jobs j "
        "JOIN companies c ON c.id = j.company_id WHERE j.status = 'open'")
    return [dict(r) for r in rows]
