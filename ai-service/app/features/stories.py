"""STAR story bank (forward Epic 6.5).

Turn the candidate's own experience and projects into a bank of reusable interview
stories. Deterministic and evidence-bound: it reorganises the candidate's material --
one seed per role, one per project -- and does not invent a story. Each seed carries
the bullets, the declared skills those bullets evidence, and whether it is quantified.

This is the raw material an interview answer (or an outreach message) is built from,
surfaced so the candidate can reach for their strongest, most concrete work first
rather than re-reading a whole resume under pressure.
"""

import re

from app.core.skills import normalize


def _mentions(text: str, name: str) -> bool:
    return bool(re.search(rf"(?<![a-z0-9.+#]){re.escape(name.lower())}(?![a-z0-9.+#])",
                          text.lower()))


def _declared_skills(resume: dict) -> list[str]:
    out: list[str] = []
    for s in resume.get("skills") or []:
        if isinstance(s, dict) and s.get("name"):
            out.append(normalize(s["name"]))
    return out


def _bullets(entry: dict) -> list[str]:
    return [b for b in (entry.get("bullets") or []) if isinstance(b, str) and b.strip()]


def _quantified(bullets: list[str]) -> bool:
    return any(any(c.isdigit() for c in b) for b in bullets)


def _title(entry: dict) -> str:
    role = entry.get("title") or ""
    company = entry.get("company") or ""
    if role and company:
        return f"{role} at {company}"
    return role or company or "Role"


def _story(sid: str, kind: str, title: str, bullets: list[str], declared: list[str],
           tech: list[str]) -> dict:
    text = " ".join(bullets)
    skills = [s for s in declared if _mentions(text, s)]
    for t in tech:
        if t not in skills:
            skills.append(t)
    return {
        "id": sid,
        "kind": kind,
        "title": title,
        "bullets": bullets,
        "skills": sorted(skills),
        "quantified": _quantified(bullets),
    }


def build_story_bank(resume_structured, *, max_stories: int = 8) -> dict:
    if not isinstance(resume_structured, dict):
        resume_structured = {}
    declared = _declared_skills(resume_structured)

    stories: list[dict] = []
    for i, e in enumerate(resume_structured.get("experience") or [], 1):
        if not isinstance(e, dict):
            continue
        bullets = _bullets(e)
        if bullets:
            stories.append(_story(f"exp-{i}", "experience", _title(e), bullets, declared, []))
    for i, p in enumerate(resume_structured.get("projects") or [], 1):
        if not isinstance(p, dict):
            continue
        bullets = _bullets(p)
        tech = [normalize(t) for t in (p.get("tech") or []) if isinstance(t, str) and t.strip()]
        if bullets or tech:
            stories.append(_story(f"proj-{i}", "project", p.get("name") or "Project",
                                  bullets, declared, tech))

    # Strongest first: quantified, then more evidenced skills, then more bullets.
    stories.sort(key=lambda s: (not s["quantified"], -len(s["skills"]), -len(s["bullets"])))
    stories = stories[:max(0, max_stories)]
    return {
        "stories": stories,
        "count": len(stories),
        "quantifiedCount": sum(1 for s in stories if s["quantified"]),
        "skillsCovered": sorted({sk for s in stories for sk in s["skills"]}),
    }
