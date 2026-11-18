"""The copilot's artifact cards read the keys the engines emit (Epic 325).

The growth panel already had this gate: an interactive surface that reads a
name the engine never writes answers with a shrug, and no unit test anywhere
catches it because every side is green in isolation. The artifacts — the cards
the copilot draws inside an answer — had no such gate, and the way it failed
was measured, not hypothetical: two artifacts rendered nothing for months while
green tests pinned the invented keys (`rows` / `best` on offer_comparison
against the engine's `offers` / `bestByComp`).

This test parses the frontend's `artifacts.tsx`, attributes every literal key
it reads to its renderer, and asserts the read against the keys its engine
declares. The declarations are pinned to the producers where the engine is
pure (offers, prioritize), so the two sides cannot drift apart silently.
Normalizer results (`match`, `tailor`, `text`, `page`) are trusted — they are
pinned by the wire gates elsewhere.
"""

import re
from pathlib import Path

from app.features import offers as offers_mod
from app.features import prioritize as prioritize_mod

ARTIFACTS = (Path(__file__).resolve().parents[2]
             / "frontend" / "src" / "components" / "copilot" / "artifacts.tsx")

# Top-level keys each artifact's `payload` carries, per the producer collectors
# in app/agents/orchestrator.py (verified against app/features/* at this rev).
DECLARED = {
    "offer_comparison": {"currency", "sampleSize", "offers", "bestByComp", "notes", "narrative"},
    "gap_report": {"targetRole", "seniority", "expectedSkillCount", "coveredCount",
                   "partialCount", "gapCount", "coverage", "covered", "partial", "gaps",
                   "strengths", "responsibilities", "developmentPlan"},
    "salary_band": {"role", "location", "sampleSize", "percentiles", "currency", "note"},
    "learning_priority": {"targetRole", "seniority", "gapCount", "coverage",
                          "marketPostings", "prioritizedGaps", "topPriority"},
    "job_list": {"jobs"},
    "interview_session": {"session_id", "sessionId", "id", "mode", "status", "job", "session"},
    # Rendered via normalizers; their shapes are pinned by the wire gates, not here.
    "match": None,
    "tailored_resume": None,
    "cover_letter": None,
}

# Keys nested under a container the renderer opens with `list(report, "<container>")`,
# i.e. the row shape inside `offers[]`, `gaps[]` and `prioritizedGaps[]`.
ROW_KEYS = {
    "offers": {"label", "base", "bonus", "firstYearCash", "annualEquity", "totalComp",
               "assessment", "leverage"},
    "gaps": {"skill", "importance", "category"},
    "prioritizedGaps": {"skill", "importance", "category", "marketShare", "marketPostings",
                        "marketRank", "priority"},
}

RENDERERS = {
    "OfferComparisonArtifact": "offer_comparison",
    "GapReportArtifact": "gap_report",
    "SalaryBandArtifact": "salary_band",
    "LearningPriorityArtifact": "learning_priority",
    "JobListArtifact": "job_list",
    "InterviewArtifact": "interview_session",
    "MatchArtifact": "match",
    "TailorArtifact": "tailored_resume",
    "CoverLetterArtifact": "cover_letter",
}

CALL = re.compile(r"\b(str|num|bool|list|pick)\(\s*([A-Za-z_][\w.]*)\s*,([^)]*)\)")
ASSIGN = re.compile(r"(\w+)\s*=\s*list\(\s*([\w.]+)\s*,\s*\"([A-Za-z_][\w]*)\"\s*\)")
LAMBDA_ROW = re.compile(r"(\w+)\.map\(\s*\((\w+)")
FUN = re.compile(r"^function (\w+)\(", re.M)
# Owner names that hold pure-passthrough trust: normalizer results, the backend's
# own wrappers. Everything else is checked against DECLARED / ROW_KEYS.
TRUSTED_OWNERS = {"match", "tailor", "text", "page", "diff", "tailored", "evidence",
                  "session", "j", "e", "g0"}


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _renderer_spans(src: str) -> dict[str, str]:
    spans: dict[str, str] = {}
    starts = [m.start() for m in FUN.finditer(src)]
    names = [m.group(1) for m in FUN.finditer(src)]
    for i, (name, start) in enumerate(zip(names, starts)):
        end = starts[i + 1] if i + 1 < len(starts) else len(src)
        spans[name] = src[start:end]
    return spans


def _read_keys(body: str):
    """Yield (owner, [key alternatives per read]) for literal reads.

    `pick` is skipped outright: it is null-tolerant by construction (`pick(x, "k") ?? x`
    only succeeds when the key exists, and the renderer falls back to the payload
    itself), so no declaration can ever be broken by it. `list` is the one that must
    be strict — a wrong key there draws nothing, silently, which is the bug this gate
    exists because of.
    """
    for match in CALL.finditer(body):
        if match.group(1) == "pick":
            continue
        owner, rest = match.group(2), match.group(3)
        keys = re.findall(r"\"([A-Za-z_][\w]*)\"", rest)
        if keys:
            yield owner, keys


def test_every_literal_key_the_cards_read_is_one_the_engines_emit():
    src = _strip_comments(ARTIFACTS.read_text(encoding="utf-8"))
    spans = _renderer_spans(src)
    checked = 0
    problems = []
    unparseable = []
    for renderer, kind in RENDERERS.items():
        if renderer not in spans:
            unparseable.append(f"{renderer}: not found in artifacts.tsx")
            continue
        body = spans[renderer]
        row_owners: dict[str, str] = {}   # var -> container key (gaps|offers|prioritizedGaps)
        for m in ASSIGN.finditer(body):
            var, container = m.group(1), m.group(3)
            if container in ROW_KEYS:
                row_owners[var] = container
        for m in LAMBDA_ROW.finditer(body):
            container = row_owners.get(m.group(1))
            if container:
                row_owners[m.group(2)] = container
        for owner, alternatives in _read_keys(body):
            base = owner.split(".")[0]
            checked += 1
            if base in TRUSTED_OWNERS:
                continue
            container = row_owners.get(base)
            if container is not None:
                allowed = ROW_KEYS[container]
            elif DECLARED[kind] is None:
                continue
            else:
                allowed = DECLARED[kind]
            if not any(k in allowed for k in alternatives):
                problems.append(f"{renderer}: reads {{{', '.join(alternatives)}}} — "
                                f"engine emits {{{', '.join(sorted(allowed))}}}")
    assert not unparseable, "renderer spans lost: " + "; ".join(unparseable)
    # 14 non-pick literal reads at this rev (pick is exempt by construction above);
    # the floor exists so a census that goes blind cannot pass vacuously.
    assert checked >= 10, (
        f"only {checked} key reads found — the census lost the cards rather than "
        f"keeping them honest")
    assert not problems, "artifact cards read keys the engines do not emit:\n" + "\n".join(problems)


def test_the_offer_comparison_engine_answers_the_keys_the_cards_read():
    # The declared offer_comparison keys are pinned by calling the pure engine.
    out = offers_mod.compare_offers(
        [{"label": "A", "base": 300000, "bonus": 20000}],
        {"sampleSize": 4, "percentiles": {"p25": 250000, "p50": 350000, "p75": 450000}})
    # `narrative` joins the engine's answer only inside the route, never in the pure
    # function — the artifact sees the route's answer, so DECLARED carries it too.
    assert set(out) == DECLARED["offer_comparison"] - {"narrative"}


def test_the_priority_engine_answers_the_keys_the_cards_read():
    out = prioritize_mod.rank_gap_priorities(
        [{"skill": "Kubernetes", "importance": "should", "category": "devops"}],
        [{"skill": "Kubernetes", "count": 12, "share": 0.31}], 40)
    assert set(out[0]) == ROW_KEYS["prioritizedGaps"]
