"""Resume <-> Job matching engine (PRD §10).

Scores are COMPUTED deterministically from comparable skill/years/education facts,
then every criterion is bound to retrieved evidence chunks so the UI can show
"why". The LLM only writes the narrative over the computed numbers.
"""

import logging
import re

from app.agents.stategraph import NodeResult, StateGraph
from app.core import db
from app.core.ai import ask, stable_messages
from app.core.skills import extract_skills, normalize
from app.features.schemas import MatchResult
from app.providers.base import LLMMessage, LLMRequest
from app.rag import store

log = logging.getLogger(__name__)

_DEGREE_RANK = {"high school": 0, "associate": 1, "bachelor": 2, "master": 2.5,
                "phd": 3, "doctor": 3}
_WEIGHT = {"must": 3.0, "should": 2.0, "nice": 1.0}


def _dicts(rows: object) -> list[dict]:
    """The dict rows of a list, tolerating a None list or a non-dict entry.

    Peer payloads, the resume parser's own null sections, and stale cache rows
    hand these builders a list that can be None or carry a None / non-dict entry;
    iterating it raw raises, so every consumer funnels its list through here
    first. Order is preserved, so scoring and ranking are unaffected."""
    return [r for r in (rows or []) if isinstance(r, dict)]


def _skill_set(parsed: dict) -> set[str]:
    parsed = parsed or {}
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
    parsed = parsed or {}
    profile = parsed.get("profile")
    y = (profile or {}).get("yearsExperience") if isinstance(profile, dict) else None
    if isinstance(y, (int, float)):
        return float(y)
    from datetime import date
    total = 0.0
    today = date.today()
    for e in _dicts(parsed.get("experience")):
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


def _technical_denominator(req: list[dict], pref: list[dict]) -> float:
    """What `_technical_score` normalises against: 0 when the JD lists no skill at all.

    Shared with `_preparation` on purpose. The worth of closing a gap is only honest if it is the
    same arithmetic that produced the score the gap is measured against; a second copy would drift
    the first time one of them changed."""
    req = _dicts(req)
    pref = _dicts(pref)
    req_total = sum(_WEIGHT.get(s.get("priority", "must"), 3.0) for s in req)
    pref_total = sum(_WEIGHT.get(s.get("priority", "nice"), 1.0) for s in pref)
    return req_total + 0.3 * pref_total


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
    req = _dicts(req)
    pref = _dicts(pref)
    denom = _technical_denominator(req, pref)
    if not denom:
        return 0.6
    req_got = sum(_WEIGHT.get(s.get("priority", "must"), 3.0) for s in req
                  if normalize(s.get("name", "")) in r_skills)
    pref_got = sum(_WEIGHT.get(s.get("priority", "nice"), 1.0) for s in pref
                   if normalize(s.get("name", "")) in r_skills)
    return min(1.0, (req_got + 0.3 * pref_got) / denom)


def _edu_rank(parsed: dict) -> float:
    parsed = parsed or {}
    best = -1.0
    for e in _dicts(parsed.get("education")):
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
    jd = jd or {}
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
    jd = jd or {}
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
    parsed = parsed or {}
    jd = jd or {}
    projects = _dicts(parsed.get("projects"))
    proj_terms = set(extract_skills(" ".join(
        str((p.get("tech") or [])) + " ".join(
            b for b in (p.get("bullets") or []) if isinstance(b, str))
        for p in projects)))
    jd_terms = {normalize(s.get("name", "")) for s in _dicts(req) + _dicts(pref)}
    jd_terms |= {normalize(k) for k in (jd.get("priorityOrder") or []) if isinstance(k, str)}
    proj_overlap = len(jd_terms & {normalize(x) for x in proj_terms})
    n_proj = len(projects)
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
    req = _dicts(req)
    pref = _dicts(pref)
    matched = sorted({normalize(s.get("name", "")) for s in req + pref
                      if normalize(s.get("name", "")) in r_skills})
    missing = sorted({normalize(s.get("name", "")) for s in req
                      if normalize(s.get("name", "")) not in r_skills})
    return matched, missing


def _skill_gaps(req: list[dict], r_skills: set[str]) -> list[dict]:
    """The required skills the resume does not evidence, in the order the JD listed them.

    Two things this refuses to invent. ``importance`` is the requirement's *own* priority word,
    not a blanket "must": the panel renders "must" as a destructive red badge, so labelling a
    nice-to-have that way manufactures an urgency the posting never stated. And ``reason`` is the
    JD's own evidence phrase for asking, which is why this gap card has no advice column at all —
    what to do about a gap is the preparation card's job, and it already prices each one in
    overall-score points.
    """
    req = _dicts(req)
    seen: set[str] = set()
    gaps: list[dict] = []
    for s in req:
        name = normalize(s.get("name", ""))
        if not name or name in r_skills or name in seen:
            continue
        seen.add(name)
        gaps.append({"skill": name,
                     "importance": str(s.get("priority") or "must"),
                     "reason": str(s.get("evidence_phrase") or "")})
    return gaps


# Weights sum to exactly 1.0 so an all-perfect match scores 1.0 and an all-zero
# one 0.0 — _overall keeps that normalisation invariant testable.
_OVERALL_WEIGHTS = (0.42, 0.25, 0.2, 0.13)  # technical, experience, projects, education


def _overall(technical: float, experience: float, projects: float,
             education: float) -> float:
    wt, we, wp, wE = _OVERALL_WEIGHTS
    return round(wt * technical + we * experience + wp * projects + wE * education, 4)


def _min_degree(jd: dict) -> str:
    """The JD's stated minimum degree, or "" when it states none."""
    jd = jd or {}
    edu = jd.get("education")
    return str(edu.get("minDegree") or "") if isinstance(edu, dict) else ""


def _preparation_worths(req: list[dict], pref: list[dict], r_skills: set[str],
                        denom: float) -> list[tuple[dict, float]]:
    """Every open gap with the overall-score points closing it can unlock, best first.

    This is ``_technical_score``'s own arithmetic rather than a guess: a gap is worth its weight
    over the same denominator, scaled by technical's share of the overall (``_OVERALL_WEIGHTS[0]``),
    and a preferred skill carries the same 0.3 multiplier the score already applies to it. That is
    what makes the panel's "Ordered by how much match score each item is worth" defensible, and it
    is why an all-missing resume yields worths summing to exactly technical's 42 points
    (``test_preparation_worths_sum_to_technicals_share_of_overall``).

    Preferred gaps are included because ``_technical_score`` counts them; ``missingSkills`` is
    required-only (the UI's gap panel is about penalties), so the two lists differ on purpose.
    Empty when the JD lists no skill (denom 0): nothing to rank, no points to promise. A gap whose
    name normalises to "" is skipped — it cannot be titled or acted on — while the denominator still
    counts it, which is why that test's JD lists every skill by name.
    """
    req = _dicts(req)
    pref = _dicts(pref)
    if not denom:
        return []
    seen: set[str] = set()
    scored: list[tuple[dict, float]] = []
    for group, is_pref in ((req, False), (pref, True)):
        default_priority, default_weight = ("nice", 1.0) if is_pref else ("must", 3.0)
        for s in group:
            name = normalize(s.get("name", ""))
            if not name or name in seen or name in r_skills:
                continue
            seen.add(name)
            priority = str(s.get("priority", default_priority))
            points = round(100 * _OVERALL_WEIGHTS[0] * (0.3 if is_pref else 1.0)
                           * _WEIGHT.get(priority, default_weight) / denom, 1)
            scored.append(({
                "title": f"Add concrete evidence of {name}",
                "reason": (f"{'Preferred' if is_pref else 'Required'} by this JD and not matched "
                           f"in your resume — closing it is worth up to {points} points of the "
                           f"overall match."),
                "priority": priority,
            }, points))
    scored.sort(key=lambda item_and_points: (-item_and_points[1], item_and_points[0]["title"]))
    return scored


def _preparation(req: list[dict], pref: list[dict], r_skills: set[str], denom: float,
                 cap: int = 6) -> list[dict]:
    """The capped list the UI shows; ranking and worth come from ``_preparation_worths``."""
    return [item for item, _ in _preparation_worths(req, pref, r_skills, denom)[:cap]]


def _why_match(matched: list[str], req: list[dict], pref: list[dict], experience: float,
               exp_note: str, education: float, jd: dict) -> list[str]:
    """Bullets the computed facts actually support, for the match panel's headline list.

    Each bullet is gated on its dimension clearing the bar rather than merely existing, because a
    neutral score is not an achievement: experience must be >= 0.8 (the 0.75 "JD states no explicit
    years" fallback must not read as a strength) and education >= 1.0 *and* only when the JD states
    a minimum degree (0.8 is the no-requirement neutral). The skill bullet reports coverage of the
    skills the JD itself listed, so it cannot invent a transferable strength. At most three bullets
    can clear their bars, which is inside the panel's slice of four."""
    out: list[str] = []
    total = len(req) + len(pref)
    if matched and total:
        shown = ", ".join(matched[:3])
        extra = f" (+{len(matched) - 3} more)" if len(matched) > 3 else ""
        out.append(f"Your resume covers {len(matched)} of the {total} skills this JD lists"
                   f": {shown}{extra}.")
    if experience >= 0.8:
        out.append(f"Experience: {exp_note}")
    if education >= 1.0 and _min_degree(jd):
        out.append(f"Education meets the stated minimum ({_min_degree(jd)}).")
    return out


_EN_WORD_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
_CN_NUM = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "百": 100}


def _word_number(raw: str) -> float | None:
    """Parse a single-token written numeral: English ("six", "twenty-one") or
    Chinese ("九", "十二", "二十"). Anything unparseable returns None and the
    auditor skips it rather than rejecting prose it cannot understand."""
    token = raw.strip().lower().replace("-", " ")
    if token in _EN_WORD_NUM:
        return float(_EN_WORD_NUM[token])
    parts = [p for p in token.split() if p]
    if len(parts) > 1 and all(p in _EN_WORD_NUM for p in parts):
        return float(sum(_EN_WORD_NUM[p] for p in parts))
    cn = [_CN_NUM.get(c) for c in token]
    if token and all(v is not None for v in cn):
        if len(cn) == 1:
            return float(cn[0])
        if len(cn) == 2 and cn[0] == 1:          # 十X
            return float(10 + cn[1])
        if len(cn) == 2 and cn[1] == 10:         # X十
            return float(cn[0] * 10)
    return None


def _audit_narrative_numbers(text: str, allowed_percents: set[int],
                             years_reference: list[float]) -> list[str]:
    """Every number the narrative states that the computed facts did not.

    Two shapes are audited. Percentages: the five computed scores are the only
    ones the model was given, so any percentage whose round(value) is not one of
    them is an invention the UI must not render as if it were arithmetic. Years:
    the model was given the candidate's computed years and the JD's bar; a year
    count in prose is checked against those two (with 0.5 of float slack), never
    against nothing at all. Bare counts ("3 of 9 skills") are audited loosely —
    any integer below the number of JD-listed skills is accepted as a count the
    model read off the facts, anything above is not.

    Returns the offending substrings; empty means the prose stayed inside the
    numbers the wire computed.
    """
    out: list[str] = []

    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", text):
        try:
            v = float(m.group(1))
        except ValueError:
            continue
        r = round(v)
        if r not in allowed_percents:
            out.append(m.group(0))

    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?|y\b|年)", text, re.IGNORECASE):
        try:
            v = float(m.group(1))
        except ValueError:
            continue
        if not any(abs(v - ref) <= 0.5 for ref in years_reference):
            out.append(m.group(0))

    # Single-token numerals written as words, English and Chinese ("six years",
    # "年" with 九/十二/二十): the commonest slipping variant. Compound Chinese
    # numerals beyond two characters ("三十二") stay out of scope deliberately;
    # an unparseable word is skipped, never flagged — the gate must not
    # hallucinate its own rejections.
    for m in re.finditer(r"([零一二三四五六七八九十百两])\s*年", text):
        v = _word_number(m.group(1))
        if v is None:
            continue
        if not any(abs(v - ref) <= 0.5 for ref in years_reference):
            out.append(m.group(0))

    for m in re.finditer(r"([A-Za-z]{1,24})\s*(?:years?|yrs?|y\b|percent)", text,
                         re.IGNORECASE):
        v = _word_number(m.group(1))
        if v is None:
            continue
        trailing = m.group(0)
        if re.search(r"percent\s*$", trailing, re.IGNORECASE):
            # a word-percent: check against the allowed percentage set instead
            r = round(v)
            if r not in allowed_percents:
                out.append(m.group(0))
            continue
        if not any(abs(v - ref) <= 0.5 for ref in years_reference):
            out.append(m.group(0))

    return out


async def compute_match(resume_parsed: dict, jd: dict, *, user_id: str,
                        job_id: str | None = None, run_id: str | None = None) -> dict:
    resume_parsed = resume_parsed or {}
    jd = jd or {}
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

    # ---- LLM narrative, riding the bounded spine (Epic 316) ----
    # The narrative is the only part of this engine that needs a provider; every number
    # above is deterministic. The draft is prose written over the computed facts, the
    # verify node fingerprints every percentage and year the model states against the
    # set the wire computed (±0.5 of float slack), one bounded revision is offered when
    # the first draft invents one, and the fallback is the computed facts — never the
    # invented prose on the UI.
    facts = (f"Computed scores — overall:{overall:.0%}, technical:{technical:.0%} "
             f"({len(matched)} of {len(req) + len(pref)} listed skills matched), "
             f"experience:{experience:.0%} ({exp_note}) projects:{projects:.0%} education:{education:.0%}.\n"
             f"Matched: {', '.join(matched[:12])}\nMissing: {', '.join(missing[:12])}")
    have_years = _user_years(resume_parsed)
    need_years = jd.get("experienceYears")
    years_reference = [have_years]
    if isinstance(need_years, (int, float)):
        years_reference.append(float(need_years))
    allowed_percents = {round(v * 100) for v in (overall, technical, experience, projects, education)}

    async def _draft(state: dict) -> NodeResult:
        feedback = state.get("verifier_feedback") or ""
        user_prompt = f"JD: {jd.get('title','')} at {jd.get('company','')}\n{facts}"
        if feedback:
            user_prompt += ("\n\nVERIFIER REJECTION (rewrite completely; none of these "
                            f"may remain or be rephrased as-is): {feedback}")
        draft = None
        try:
            llm = await ask(LLMRequest(
                messages=stable_messages(
                    "You are a hiring analyst. Using ONLY the computed facts, "
                    "write 2 short paragraphs: (1) overall assessment, (2) the "
                    "top 2-3 concrete actions to improve chances. Do not change "
                    "or restate numbers beyond those given; do not invent "
                    "experience. Plain text.",
                    LLMMessage("user", user_prompt),
                ), temperature=0.4, max_tokens=500),
                user_id=user_id, run_id=run_id, agent="jd_analyst",
                kind="match_narrative")
            draft = {"text": llm.text, "model": llm.model}
        except Exception as e:
            # The narrative is the only part of this engine that needs a provider; every
            # number above is deterministic. Failing the whole match because the prose could
            # not be written would discard a score the user can act on -- `calculate_match`
            # would answer with a tool error instead of "72%, missing Kafka".
            log.warning("match narrative provider failed; answering with the computed facts: %s", e)
        return NodeResult({"draft": draft, "attempts": state["attempts"] + 1},
                          "verify", trace={"providerOk": draft is not None})

    async def _verify(state: dict) -> NodeResult:
        draft = state.get("draft")
        if not draft:
            return NodeResult({"verdict": "fallback", "rejected": ["provider"]},
                              "render", trace={"verdict": "fallback", "reason": "provider"})
        violations = _audit_narrative_numbers(draft["text"], allowed_percents,
                                              years_reference)
        if not violations:
            return NodeResult(
                {"verdict": "accept", "narrative": draft["text"], "model": draft["model"]},
                "render", trace={"verdict": "accept"})
        if state["attempts"] < 2:
            feedback = "; ".join(violations[:10])
            return NodeResult(
                {"verdict": "retry", "verifier_feedback": feedback,
                 "rejected": violations},
                "draft", trace={"verdict": "retry", "inventedNumbers": len(violations)})
        return NodeResult(
            {"verdict": "fallback", "rejected": violations},
            "render", trace={"verdict": "fallback", "inventedNumbers": len(violations)})

    async def _render(state: dict) -> NodeResult:
        if state.get("narrative"):
            return NodeResult({"narrative": state["narrative"],
                               "model": state.get("model") or ""},
                              None, trace={"outcome": "accepted"})
        # The model invented a number the wire never computed; the user sees the
        # computed facts, not the invention with extra flourish.
        return NodeResult({"narrative": facts, "model": ""},
                          None, trace={"outcome": "fallback_facts"})

    graph = StateGraph("draft",
                       {"draft": _draft, "verify": _verify, "render": _render},
                       max_steps=6)
    final = await graph.run({"attempts": 0}, run_id=run_id, agent="jd_analyst")
    narrative = final["narrative"]
    model = final.get("model", "")

    result = MatchResult(
        overall=overall, technical=round(technical, 4), experience=round(experience, 4),
        projects=round(projects, 4), education=round(education, 4),
        matchedSkills=matched, missingSkills=missing,
        skillGaps=_skill_gaps(req, r_skills),
        evidence=evidence,
        whyMatch=_why_match(matched, req, pref, experience, exp_note, education, jd),
        preparation=_preparation(req, pref, r_skills, _technical_denominator(req, pref)),
        narrative=narrative,
        interviewTopics=(jd.get("interviewTopics") or [])[:8], model=model)
    return result.model_dump()


async def persist_match(user_id: str, job_id: str, resume_version_id: str,
                        result: dict) -> str:
    row = await db.fetchrow(
        """INSERT INTO job_matches(user_id, job_id, resume_version_id, overall, technical,
               experience, projects, education, matched_skills, missing_skills, evidence,
               why_match, preparation, skill_gaps, narrative, model)
           VALUES ($1::uuid,$2::uuid,$3::uuid,$4,$5,$6,$7,$8,$9::jsonb,$10::jsonb,
                   $11::jsonb,$12::jsonb,$13::jsonb,$14::jsonb,$15,$16)
           ON CONFLICT (user_id, job_id, resume_version_id) DO UPDATE SET
             overall=EXCLUDED.overall, technical=EXCLUDED.technical,
             experience=EXCLUDED.experience, projects=EXCLUDED.projects,
             education=EXCLUDED.education, matched_skills=EXCLUDED.matched_skills,
             missing_skills=EXCLUDED.missing_skills, evidence=EXCLUDED.evidence,
             why_match=EXCLUDED.why_match, preparation=EXCLUDED.preparation,
             skill_gaps=EXCLUDED.skill_gaps,
             narrative=EXCLUDED.narrative, model=EXCLUDED.model, created_at=now()
           RETURNING id""",
        user_id, job_id, resume_version_id, result["overall"], result["technical"],
        result["experience"], result["projects"], result["education"],
        db.jsonb(result["matchedSkills"]), db.jsonb(result["missingSkills"]),
        db.jsonb(result["evidence"]), db.jsonb(result["whyMatch"]),
        db.jsonb(result["preparation"]), db.jsonb(result["skillGaps"]),
        result["narrative"], result.get("model"))
    return str(row["id"])
