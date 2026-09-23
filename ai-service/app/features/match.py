"""Resume <-> Job matching engine (PRD §10).

Scores are COMPUTED deterministically from comparable skill/years/education facts,
then every criterion is bound to retrieved evidence chunks so the UI can show
"why". The LLM only writes the narrative over the computed numbers.
"""

from app.core import db
from app.core.ai import ask
from app.core.skills import extract_skills, normalize
from app.features.schemas import MatchResult
from app.providers.base import LLMMessage, LLMRequest
from app.rag import store

_DEGREE_RANK = {"high school": 0, "associate": 1, "bachelor": 2, "master": 2.5,
                "phd": 3, "doctor": 3}
_WEIGHT = {"must": 3.0, "should": 2.0, "nice": 1.0}


def _skill_set(parsed: dict) -> set[str]:
    out = {normalize(s.get("name", "")) for s in (parsed.get("skills") or [])
           if isinstance(s, dict) and s.get("name")}
    blob = " ".join(str(v) for v in ((parsed.get("experience") or []) +
                                     (parsed.get("projects") or [])))
    out |= {normalize(s) for s in extract_skills(blob)}
    return {s for s in out if s}


def _year_month(s: object, default_month: int) -> tuple[int, int] | None:
    """Parse a date string into (year, month).

    The resume parser is instructed to emit ``YYYY-MM`` *when inferable, else keep
    the original string*, so ``_user_years`` also receives bare years ("2019"),
    dotted/space-separated ranges, and prose. A bare year is resolved to
    ``default_month`` (Jan for a start, Dec for an end) so a whole-year span is
    counted instead of silently dropped. Returns None only when no 4-digit year is
    present at all.
    """
    import re
    txt = str(s or "")
    m = re.match(r"\s*(\d{4})\s*[-/.]\s*(\d{1,2})", txt)
    if m:
        return int(m.group(1)), max(1, min(12, int(m.group(2))))
    m = re.match(r"\s*(\d{4})(?!\d)", txt)
    if m:
        return int(m.group(1)), default_month
    return None


def _user_years(parsed: dict) -> float:
    y = (parsed.get("profile") or {}).get("yearsExperience")
    if isinstance(y, (int, float)):
        return float(y)
    from datetime import date
    total = 0.0
    today = date.today()
    for e in parsed.get("experience") or []:
        st = _year_month(e.get("start"), 1)
        if not st:
            continue
        end_txt = str(e.get("end") or "").lower()
        if "present" in end_txt or "now" in end_txt or "至今" in end_txt:
            endy, endm = today.year, today.month
        else:
            en = _year_month(end_txt, 12)
            if not en:
                continue
            endy, endm = en
        months = max(0, (endy - st[0]) * 12 + (endm - st[1]))
        total += min(months, 72) / 12.0
    return round(total, 1)


def _technical_score(req: list[dict], pref: list[dict], r_skills: set[str]) -> float:
    """Weighted required/preferred skill coverage, in 0..1.

    Returns a neutral 0.6 only when the JD lists *no* skills at all, so a thin
    posting is not punished with technical=0. The original inline version summed
    ``req_total`` with ``or 1.0`` (a divide-by-zero guard), which forced a nonzero
    denominator and made that neutral fallback unreachable — so a JD with zero
    required/preferred skills scored technical=0 and dragged the overall down. The
    guard also injected a phantom weight-of-1.0 into the *preferred-only* case,
    under-counting coverage against a denominator that included a required skill
    the JD never listed. Both are fixed by guarding on the real total here.
    """
    req_total = sum(_WEIGHT.get(s.get("priority", "must"), 3.0) for s in req)
    req_got = sum(_WEIGHT.get(s.get("priority", "must"), 3.0) for s in req
                  if normalize(s.get("name", "")) in r_skills)
    pref_total = sum(_WEIGHT.get(s.get("priority", "nice"), 1.0) for s in pref)
    pref_got = sum(_WEIGHT.get(s.get("priority", "nice"), 1.0) for s in pref
                   if normalize(s.get("name", "")) in r_skills)
    denom = req_total + 0.3 * pref_total
    if not denom:
        return 0.6
    return min(1.0, (req_got + 0.3 * pref_got) / denom)


def _edu_rank(parsed: dict) -> float:
    best = -1.0
    for e in parsed.get("education") or []:
        d = (e.get("degree") or "").lower()
        for k, v in _DEGREE_RANK.items():
            if k in d:
                best = max(best, v)
    return best


def _experience_score(parsed: dict, jd: dict) -> tuple[float, str]:
    """Experience subscore (0..1) plus the human-readable note bound as evidence.

    Neutral 0.75 when the JD states no explicit years; capped credit for meeting
    the bar; a floor of 0.25 (never 0) when under so a junior candidate is not
    zeroed out. Returns (score, note)."""
    need_years = jd.get("experienceYears")
    have_years = _user_years(parsed)
    if not isinstance(need_years, (int, float)) or need_years <= 0:
        return 0.75, "JD does not state explicit years; based on role level."
    if have_years >= need_years:
        return (min(1.0, 0.8 + 0.2 * have_years / max(need_years, 1) / 2),
                f"{have_years}y experience >= required {need_years}y.")
    return max(0.25, have_years / need_years), f"{have_years}y vs required {need_years}y."


def _education_score(parsed: dict, jd: dict) -> float:
    """Education subscore (0..1); neutral 0.8 when the JD sets no minDegree.

    Degree ranks are ordered (associate<bachelor<master<phd); a resume ranked at
    or above the bar scores 1.0, otherwise it decays 0.25 per rank below with a
    0.3 floor."""
    need_edu = (jd.get("education") or {}).get("minDegree") if isinstance(
        jd.get("education"), dict) else None
    if not need_edu:
        return 0.8
    user_edu = _edu_rank(parsed)
    need_rank = next((v for k, v in _DEGREE_RANK.items() if k in need_edu.lower()), 2)
    return 1.0 if user_edu >= need_rank else max(0.3, 0.5 + 0.25 * (user_edu - need_rank + 1))


def _projects_score(parsed: dict, req: list[dict], pref: list[dict], jd: dict) -> float:
    """Projects subscore (0..1): count credit (capped at 3) plus JD-term overlap.

    With no projects it falls back to 0.35 if the candidate has work experience,
    else 0.1, so a project-less resume is not zeroed out entirely."""
    proj_terms = set(extract_skills(" ".join(
        str((p.get("tech") or [])) + " ".join(p.get("bullets") or [])
        for p in (parsed.get("projects") or []))))
    jd_terms = {normalize(s.get("name", "")) for s in req + pref}
    jd_terms |= {normalize(k) for k in jd.get("priorityOrder") or []}
    proj_overlap = len(jd_terms & {normalize(x) for x in proj_terms})
    n_proj = len(parsed.get("projects") or [])
    return min(1.0, 0.25 * min(n_proj, 3) + 0.1 * min(proj_overlap, 5)) \
        if n_proj else (0.35 if parsed.get("experience") else 0.1)


def _matched_missing(req: list[dict], pref: list[dict],
                     r_skills: set[str]) -> tuple[list[str], list[str]]:
    """Skills the resume covers vs the gaps it must close (both sorted, deduped).

    The asymmetry is deliberate and load-bearing for the UI: ``matched`` is drawn
    from required *and* preferred skills (a nice-to-have you hold is still worth
    surfacing), while ``missing`` is only the *required* skills you lack (a gap you
    are not penalised for). Changing either set's source list shifts the user-visible
    skill-gap panel, so this is pinned by tests."""
    matched = sorted({normalize(s.get("name", "")) for s in req + pref
                      if normalize(s.get("name", "")) in r_skills})
    missing = sorted({normalize(s.get("name", "")) for s in req
                      if normalize(s.get("name", "")) not in r_skills})
    return matched, missing


# Weights sum to exactly 1.0 so an all-perfect match scores 1.0 and an all-zero
# one 0.0 — _overall keeps that normalisation invariant testable.
_OVERALL_WEIGHTS = (0.42, 0.25, 0.2, 0.13)  # technical, experience, projects, education


def _overall(technical: float, experience: float, projects: float,
             education: float) -> float:
    wt, we, wp, wE = _OVERALL_WEIGHTS
    return round(wt * technical + we * experience + wp * projects + wE * education, 4)


async def compute_match(resume_parsed: dict, jd: dict, *, user_id: str,
                        job_id: str | None = None, run_id: str | None = None) -> dict:
    r_skills = _skill_set(resume_parsed)
    evidence: list[dict] = []

    req = [s for s in jd.get("requiredSkills") or [] if isinstance(s, dict)]
    pref = [s for s in jd.get("preferredSkills") or [] if isinstance(s, dict)]

    # ---- technical: weighted skill coverage ----
    technical = _technical_score(req, pref, r_skills)

    matched, missing = _matched_missing(req, pref, r_skills)

    # ---- experience ----
    experience, exp_note = _experience_score(resume_parsed, jd)

    # ---- projects ----
    projects = _projects_score(resume_parsed, req, pref, jd)

    # ---- education ----
    education = _education_score(resume_parsed, jd)

    overall = _overall(technical, experience, projects, education)

    # ---- evidence binding: find resume chunks supporting each matched skill ----
    for sk in matched[:8]:
        hits = await store.keyword_search(user_id, sk, k=1, kinds=["resume"])
        if hits:
            h = hits[0]
            evidence.append({"criterion": f"skill:{sk}", "score": round(technical, 3),
                             "chunk_ids": [str(h["id"])], "quote": h["text"][:280],
                             "source": h.get("doc_title") or "Resume",
                             "section": h.get("section_path") or "",
                             "reasoning": f"'{sk}' appears in your resume and is "
                                          f"listed by this JD."})
    for sk in missing[:5]:
        s_item = next((s for s in req if normalize(s.get("name", "")) == sk), None)
        evidence.append({"criterion": f"gap:{sk}", "score": 0.0, "chunk_ids": [],
                         "quote": (s_item or {}).get("evidence_phrase", "")[:280],
                         "source": "Job Description", "section": "requirements",
                         "reasoning": f"JD requirement '{sk}' not found in resume evidence."})
    evidence.append({"criterion": "experience", "score": round(experience, 3),
                     "chunk_ids": [], "quote": exp_note, "source": "Resume",
                     "section": "experience", "reasoning": exp_note})

    # ---- LLM narrative constrained to computed numbers ----
    facts = (f"Computed scores — overall:{overall:.0%}, technical:{technical:.0%} "
             f"({len(matched)} of {len(req) + len(pref)} listed skills matched), "
             f"experience:{experience:.0%} ({exp_note}) projects:{projects:.0%} education:{education:.0%}.\n"
             f"Matched: {', '.join(matched[:12])}\nMissing: {', '.join(missing[:12])}")
    llm = await ask(LLMRequest(
        messages=[
            LLMMessage("system", "You are a hiring analyst. Using ONLY the computed facts, "
                                 "write 2 short paragraphs: (1) overall assessment, (2) the "
                                 "top 2-3 concrete actions to improve chances. Do not change "
                                 "or restate numbers beyond those given; do not invent "
                                 "experience. Plain text."),
            LLMMessage("user", f"JD: {jd.get('title','')} at {jd.get('company','')}\n{facts}"),
        ], temperature=0.4, max_tokens=500),
        user_id=user_id, run_id=run_id, agent="jd_analyst", kind="match_narrative")

    result = MatchResult(
        overall=overall, technical=round(technical, 4), experience=round(experience, 4),
        projects=round(projects, 4), education=round(education, 4),
        matchedSkills=matched, missingSkills=missing,
        skillGaps=[{"skill": m, "importance": "must",
                    "advice": ""} for m in missing],
        evidence=evidence, narrative=llm.text,
        interviewTopics=(jd.get("interviewTopics") or [])[:8], model=llm.model)
    return result.model_dump()


async def persist_match(user_id: str, job_id: str, resume_version_id: str,
                        result: dict) -> str:
    row = await db.fetchrow(
        """INSERT INTO job_matches(user_id, job_id, resume_version_id, overall, technical,
               experience, projects, education, matched_skills, missing_skills, evidence,
               narrative, model)
           VALUES ($1::uuid,$2::uuid,$3::uuid,$4,$5,$6,$7,$8,$9::jsonb,$10::jsonb,
                   $11::jsonb,$12,$13)
           ON CONFLICT (user_id, job_id, resume_version_id) DO UPDATE SET
             overall=EXCLUDED.overall, technical=EXCLUDED.technical,
             experience=EXCLUDED.experience, projects=EXCLUDED.projects,
             education=EXCLUDED.education, matched_skills=EXCLUDED.matched_skills,
             missing_skills=EXCLUDED.missing_skills, evidence=EXCLUDED.evidence,
             narrative=EXCLUDED.narrative, model=EXCLUDED.model, created_at=now()
           RETURNING id""",
        user_id, job_id, resume_version_id, result["overall"], result["technical"],
        result["experience"], result["projects"], result["education"],
        db.jsonb(result["matchedSkills"]), db.jsonb(result["missingSkills"]),
        db.jsonb(result["evidence"]), result["narrative"], result.get("model"))
    return str(row["id"])
