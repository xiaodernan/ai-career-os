"""Target-role suggestions (forward Epic 10.10).

"Which roles should I target?" Across the postings the platform holds, group them into
role families and, for each, show how much of that family's most-demanded skills the
candidate already has. Ranked by coverage, so the families the candidate is closest to
are named first -- with the skills still missing, so the answer is actionable.

Deterministic: families come from a keyword map over the titles, demand from the
`skills[]` postings carry, and coverage is a set overlap against the candidate's own
declared skills. Nothing is inferred about a role the corpus does not contain.
"""

from collections import Counter

from app.core.skills import normalize

# Keyword -> role family. Order matters only for readability; the first family whose
# keyword appears in the title wins.
FAMILIES: dict[str, list[str]] = {
    "backend": ["backend", "server-side", "服务端", "后端"],
    "frontend": ["frontend", "front-end", "web ui", "前端"],
    "fullstack": ["full stack", "fullstack", "全栈"],
    "data": ["data engineer", "data platform", "etl", "数仓", "数据"],
    "ml": ["machine learning", "ml engineer", "算法", "人工智能", "ai engineer"],
    "devops": ["devops", "sre", "platform engineer", "infra", "运维"],
    "mobile": ["mobile", "android", "ios", "客户端"],
    "qa": ["qa", "quality engineer", "test engineer", "测试"],
}


def family_of(title: str) -> str:
    low = (title or "").lower()
    for fam, keywords in FAMILIES.items():
        if any(k in low for k in keywords):
            return fam
    return "other"


def declared_skills(resume_structured) -> list[str]:
    out: list[str] = []
    if isinstance(resume_structured, dict):
        for s in resume_structured.get("skills") or []:
            if isinstance(s, dict) and s.get("name"):
                out.append(normalize(s["name"]))
    return out


def suggest_roles(samples: list[dict], resume_skills: list[str], *, top: int = 8,
                  min_postings: int = 1) -> dict:
    have = {normalize(s) for s in resume_skills}
    demand: dict[str, Counter] = {}
    postings: Counter[str] = Counter()
    for s in samples:
        fam = family_of(s.get("title") or "")
        postings[fam] += 1
        bucket = demand.setdefault(fam, Counter())
        for sk in s.get("skills") or []:
            if isinstance(sk, str) and sk.strip():
                bucket[normalize(sk)] += 1

    families: list[dict] = []
    for fam, counter in demand.items():
        if postings[fam] < min_postings:
            continue
        demands = [sk for sk, _ in counter.most_common(10)]
        if not demands:
            continue
        you_have = [sk for sk in demands if sk in have]
        families.append({
            "family": fam,
            "postings": postings[fam],
            "coverage": round(len(you_have) / len(demands), 3),
            "topDemands": demands,
            "youHave": you_have,
            "missing": [sk for sk in demands if sk not in have],
        })

    families.sort(key=lambda r: (-r["coverage"], -r["postings"], r["family"]))
    return {"families": families[:max(0, top)]}
