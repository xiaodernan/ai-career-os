"""The growth panel must read the field names the growth engines actually answer (#252).

``/growth`` renders two surfaces from the nine granular engines: the aggregate report
(``/growth-report``, which nests each answer under ``gap`` / ``learningPlan``) and the
one-engine-at-a-time panel, which calls each ``/growth/<engine>`` route. Those routes
answer the engine's own dict -- the Java bridge posts the body and returns
``Map`` without renaming a key, and no normalizer sits on these paths -- so the panel's
field names are not a frontend dialect: they are a claim about the engine.

Nine of those claims were wrong at once. ``gaps[].name``, ``priorities``, ``phases``,
``study``/``rehearse``, ``steps``/``missing``, ``roles`` are names no producer has ever
emitted; the engine answers ``gaps[].skill``, ``prioritizedGaps``, ``plan.phases``,
``weakAreas``/``strengthStories``, ``steppingStones``/``aspirationalMustGaps`` and
``families``. Five of the nine engine tabs therefore painted an empty box under a
headline that promised an answer, and two painted rows whose text was blank.

This file grades the claim against the answer, on every reader of these shapes:
the panel, the copilot artifact cards, and ``docs/API.md`` -- the row the panel's
``reachable`` badge was copied from -- plus the declared contract (``types.ts``).

#254 added the fourth reader, the ``/growth`` page itself. Its field names were all
real -- no stale spelling survived the check -- but it read only what it had been
written against, and the aggregate answers more than that: the progress diff returns
five skill lists and the page drew three (``opened``, a gap the previous report never
listed, had no reader anywhere in the frontend), and every plan item carries a
``resource_hint`` the row never showed. So the page is graded in both directions here:
a path it reads has to be an answer, and an answer the row exists to show has to be
read.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
FEATURES = ROOT / "ai-service" / "app" / "features"
ROUTES = ROOT / "ai-service" / "app" / "api" / "features.py"
PANEL = ROOT / "frontend" / "src" / "components" / "growth" / "growth-engines-panel.tsx"
PAGE = ROOT / "frontend" / "src" / "app" / "(app)" / "growth" / "page.tsx"
ARTIFACTS = ROOT / "frontend" / "src" / "components" / "copilot" / "artifacts.tsx"
TYPES = ROOT / "frontend" / "src" / "lib" / "api" / "types.ts"
BRIDGE = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "ai" / "HttpAiServiceClient.java"
DOCS = ROOT / "docs" / "API.md"

ENGINES = ("gap", "demand", "priority", "plan", "prep", "progression",
           "stories", "roles", "progress")

#: The type each engine's answer is read through, so the panel cannot go back to
#: an inline ``as Array<{...}>`` -- that is where the stale names lived.
ENGINE_TYPES = {
    "gap": "GapReport",
    "demand": "SkillDemand",
    "priority": "LearningPriority",
    "plan": "LearningPlan",
    "prep": "InterviewPrep",
    "progression": "ProgressionPlan",
    "stories": "StoryBank",
    "roles": "RoleSuggestions",
    "progress": "SkillProgress",
}

#: Methods a reader may call on a value it already read; never answer keys.
_MEMBERS = frozenset({"map", "length", "join", "filter", "some", "every", "slice", "sort",
                      "trim", "toFixed", "toString", "replace", "split", "includes",
                      "indexOf", "forEach", "push", "flatMap", "reduce", "charAt"})


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def paths(value, prefix: str = "") -> set[str]:
    """Every dotted path an answer carries, list items marked with ``[]``."""
    out: set[str] = set()
    if isinstance(value, dict):
        for key, sub in value.items():
            p = f"{prefix}.{key}" if prefix else str(key)
            out.add(p)
            out |= paths(sub, p)
    elif isinstance(value, list):
        for item in value:
            out |= paths(item, f"{prefix}[]")
    return out


def leaves(answer_paths: set[str]) -> set[str]:
    return {p.rsplit(".", 1)[-1].removesuffix("[]") for p in answer_paths}


def returned_keys(source: str, func: str) -> set[str]:
    """The key names an engine function literally returns.

    Read from the source, never retyped here: an orchestrator that renames a key or
    adds one has to be noticed by this file, not quietly kept out of it.
    """
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func:
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Dict):
                    return {k.value for k in stmt.value.keys
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    raise AssertionError(f"{func} no longer returns a dict literal")


# ---------------------------------------------------------------- fixtures ----

_SAMPLES = [
    {"title": "Senior Backend Engineer", "location": "Shanghai",
     "skills": ["Java", "Kubernetes", "PostgreSQL", "Go"]},
    {"title": "Backend Engineer", "location": "Shenzhen", "skills": ["Java", "Docker", "Go"]},
    {"title": "Data Engineer", "location": "Shanghai", "skills": ["Python", "Airflow"]},
]
_RESUME = {
    "skills": [{"name": "Java"}, {"name": "PostgreSQL"}],
    "experience": [{"title": "Backend Engineer", "company": "Acme",
                    "bullets": ["Cut p99 latency 40% on a Java search service"]}],
    "projects": [{"name": "Ledger", "tech": ["Kafka"], "bullets": ["Replayed 12M events"]}],
}
# One skill per verdict the coverage classifier can reach: declared, named in prose
# only, and absent -- so every row list this gate reads is genuinely populated.
_EXPECTED = [
    {"name": "Java", "importance": "must", "category": "language"},
    {"name": "Kubernetes", "importance": "must", "category": "devops"},
    {"name": "Go", "importance": "nice", "category": "language"},
    {"name": "Rust", "importance": "should", "category": "language"},
]
_CORPUS = ("Owned a Java search service. Ran a Kubernetes rollout for the team and wrote "
           "the runbook. Ship features in a typed language.")


def gap_answer() -> dict:
    """The 10.1 report, with the engine's own key names and the pure parts' values."""
    from app.features import gap_analysis

    # Evidence comes from the engine's own reader: `normalize` keeps a skill's case,
    # so a hand-written lowercase set silently buckets everything as partial.
    skills, corpus = gap_analysis.build_evidence(_RESUME, _CORPUS)
    covered, partial, gaps = gap_analysis.classify_coverage(_EXPECTED, skills, corpus)
    values = {
        "targetRole": "Senior Backend Engineer", "seniority": "senior",
        "expectedSkillCount": len(_EXPECTED), "coveredCount": len(covered),
        "partialCount": len(partial), "gapCount": len(gaps), "coverage": 0.5,
        "covered": covered, "partial": partial, "gaps": gaps,
        "strengths": [c["skill"] for c in covered],
        "responsibilities": ["Design and ship APIs"],
        "developmentPlan": gap_analysis.build_development_plan(gaps, partial),
    }
    keys = returned_keys(read(FEATURES / "gap_analysis.py"), "analyze_gap")
    assert keys == set(values), f"analyze_gap's answer changed shape: {keys ^ set(values)}"
    return {k: values[k] for k in keys}


def emitted() -> dict[str, set[str]]:
    """engine -> every path that engine's route answers, built from the engines."""
    from app.features import (demand, gap_analysis, interview_prep, learning, prioritize,
                              progression, roles, stories)

    gap = gap_answer()
    out: dict[str, set[str]] = {"gap": paths(gap)}

    demand_skills = demand.skill_demand(_SAMPLES, role="backend", top=10)
    out["demand"] = paths(demand_skills)

    ranked = prioritize.rank_gap_priorities(gap["gaps"], demand_skills["skills"],
                                            demand_skills["postings"])
    prior_values = {
        "targetRole": "Senior Backend Engineer", "seniority": "senior",
        "gapCount": len(ranked), "coverage": gap["coverage"],
        "marketPostings": demand_skills["postings"], "prioritizedGaps": ranked,
        "topPriority": ranked[0] if ranked else None,
    }
    prior_keys = returned_keys(read(FEATURES / "prioritize.py"), "plan_learning_priority")
    assert prior_keys == set(prior_values), (
        f"plan_learning_priority's answer changed shape: {prior_keys ^ set(prior_values)}")
    out["priority"] = paths({k: prior_values[k] for k in prior_keys})

    plan = learning.build_learning_plan(gap)
    assert returned_keys(read(FEATURES / "learning.py"), "build_learning_plan") <= set(plan)
    # The route answers {plan, gap}: the phases are NOT at the top level.
    assert returned_keys(read(ROUTES), "learning_plan_ep") == {"plan", "gap"}
    out["plan"] = paths({"plan": plan, "gap": gap})

    prep = interview_prep.build_prep_plan(gap, stories.build_story_bank(_RESUME))
    assert re.search(r"return (?:await )?interview_prep\.build_prep_plan|"
                     r"return build_prep_plan\(", read(FEATURES / "interview_prep.py")), (
        "plan_interview_prep no longer hands build_prep_plan's dict over unchanged, "
        "so the panel's claim about build_prep_plan is no longer the route's answer")
    out["prep"] = paths(prep)

    fams = roles.suggest_roles(_SAMPLES, roles.declared_skills(_RESUME), top=8)["families"]
    ap_gaps = [g["skill"] for g in gap["gaps"]]
    ap_must = [g["skill"] for g in gap["gaps"] if g["importance"] == "must"]
    stones = progression.build_stepping_stones(fams, ap_gaps, ap_must)
    prog_values = {
        "aspirationalRole": "Principal Engineer", "seniority": "senior",
        "aspirationalCoverage": gap["coverage"], "aspirationalGapCount": gap["gapCount"],
        "aspirationalMustGaps": ap_must, "steppingStones": stones,
        "advice": progression.build_advice(gap["coverage"], len(stones), ap_must),
    }
    prog_keys = returned_keys(read(FEATURES / "progression.py"), "plan_progression")
    assert prog_keys == set(prog_values), (
        f"plan_progression's answer changed shape: {prog_keys ^ set(prog_values)}")
    out["progression"] = paths({k: prog_values[k] for k in prog_keys})

    out["stories"] = paths(stories.build_story_bank(_RESUME))
    out["roles"] = paths(roles.suggest_roles(_SAMPLES,
                                             roles.declared_skills(_RESUME), top=8))
    from app.features import progress as progress_mod

    out["progress"] = paths(progress_mod.diff_progress(gap, gap))
    return out


#: Postings that carry a salary. ``benchmark`` answers ``percentiles`` as
#: ``{k: v for k in (...) if k in summary}``, so over salary-less samples the key is
#: there but empty and the page's ``salary.percentiles.p50`` would grade nothing.
_PAYING = [
    {"title": "Senior Backend Engineer", "location": "Shanghai", "experience_years": 6,
     "salary_min": 480000, "salary_max": 620000, "salary_currency": "CNY"},
    {"title": "Backend Engineer", "location": "Shanghai", "experience_years": 3,
     "salary_min": 300000, "salary_max": 380000, "salary_currency": "CNY"},
    {"title": "Staff Backend Engineer", "location": "Shanghai", "experience_years": 9,
     "salary_min": 700000, "salary_max": 900000, "salary_currency": "CNY"},
]


def previous_report() -> dict:
    """The prior answer the page hands back, chosen so every state the diff names moves.

    Against ``gap_answer()`` as the current report these four skills land in four
    different lists -- ``Java`` partial to covered (closed), ``Kubernetes`` gap to
    partial (improved), ``Go`` covered to gap (regressed) and ``Rust``, which the
    previous report never mentions, now a gap (opened) -- so no group of the progress
    card is graded against an empty fixture.
    """
    return {"targetRole": "Senior Backend Engineer", "seniority": "senior",
            "coverage": 0.55,
            "covered": [{"skill": "Go", "evidence": "declared"}],
            "partial": [{"skill": "Java", "evidence": "declared"}],
            "gaps": [{"skill": "Kubernetes", "importance": "must", "category": "devops"}]}


def aggregate(monkeypatch) -> dict:
    """The growth report as the shipped route answers it.

    The seam, not the pure function: the page's claims are about what
    ``POST /internal/features/growth-report`` puts on the wire, and the route is the
    only place that decides the nesting. ``analyze_gap`` is the LLM call and
    ``load_job_samples`` the database read; both are replaced by the fixtures the pure
    builders are graded against, so what is exercised is the composition and the wrapper.
    """
    from app.api import features as features_api
    from app.core.config import get_settings
    from app.db import observability
    from app.features import gap_analysis, salary as salary_mod
    from app.main import app
    from fastapi.testclient import TestClient

    answer = gap_answer()

    async def _gap(*args, **kwargs):
        return answer

    async def _resume(_user_id, _version):
        return {}, ""

    async def _samples():
        return list(_PAYING)

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(gap_analysis, "analyze_gap", _gap)
    monkeypatch.setattr(salary_mod, "load_job_samples", _samples)
    monkeypatch.setattr(features_api, "_resume_payload", _resume)
    monkeypatch.setattr(observability, "finish_run", _noop)
    monkeypatch.setattr(observability, "create_run", _noop)

    client = TestClient(app)                   # never a context manager: no lifespan, no pool
    headers = {"X-Internal-Token": get_settings().internal_api_token,
               "X-User-Id": "00000000-0000-0000-0000-000000aa",
               "X-Run-Id": "00000000-0000-0000-0000-000000bb"}
    r = client.post("/internal/features/growth-report",
                    json={"target_role": "Senior Backend Engineer", "seniority": "senior",
                          "location": "Shanghai", "currency": "CNY",
                          "previous": previous_report()},
                    headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"readiness", "gap", "salary", "learningPlan", "progress"}, sorted(body)
    return body


# ---------------------------------------------------------------- readers ----

def panel_cases(text: str) -> dict[str, str]:
    """engine -> the source of its ``case`` block inside ``EngineAnswer``."""
    body = text[text.index("function EngineAnswer"):]
    marks = [(m.group(1), m.start()) for m in re.finditer(r'\n\s*case "(\w+)":', body)]
    assert [name for name, _ in marks] == list(ENGINES), (
        f"the panel no longer answers the nine engines in the order this file grades: "
        f"{[name for name, _ in marks]}")
    out = {}
    for i, (name, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(body)
        out[name] = body[start:end]
    return out


def read_paths(case: str) -> set[str]:
    """The answer paths a ``case`` block reads, following each local alias.

    A name read off ``data`` after ``const x = data as T`` is a top-level path; one
    read off a ``.map`` parameter is a path under that list -- which is exactly the
    distinction that let ``phases`` (nested under ``plan``) read as missing.
    """
    binds: dict[str, str] = {}
    for m in re.finditer(r"const (\w+) = data as \w+;", case):
        binds[m.group(1)] = ""
    for m in re.finditer(r"const (\w+) = \(data as \w+\)\.(\w+);", case):
        binds[m.group(1)] = m.group(2)

    reads: set[str] = set()
    changed = True
    while changed:                          # a row may itself hold the next list
        changed = False
        for m in re.finditer(r"\((\w+)(?:\?)?\.(\w+)[^()]*\)\s*\.map\(\(\s*(\w+)", case):
            alias, field, param = m.group(1), m.group(2), m.group(3)
            if alias in binds:
                base = f"{binds[alias]}.{field}" if binds[alias] else field
                if binds.get(param) != f"{base}[]":
                    binds[param] = f"{base}[]"
                    changed = True
        for m in re.finditer(r"\b([A-Za-z_$]\w*)(?:\?)?\.([A-Za-z_$]\w*)", case):
            qual, field = m.group(1), m.group(2)
            if qual in binds and field not in _MEMBERS:
                reads.add(f"{binds[qual]}.{field}" if binds[qual] else field)
    return reads


def page_reads(text: str) -> set[str]:
    """Every answer path the ``/growth`` page reads, following each alias it binds.

    The page reaches the same block three ways: by name once (``const plan =
    report?.learningPlan``), as a prop type (``progress?: GrowthReport["progress"]``),
    and straight off the state variable (``report?.gap?.targetRole``). A plain scan ends
    its match at the first link of a chain, so the tail -- which is exactly the claim
    that goes stale -- would be invisible; every position is re-scanned from instead.
    """
    bound = re.search(r"const \[(\w+), set\w+\] = React\.useState<GrowthReport \| null>", text)
    assert bound, (
        "the page no longer keeps the report in one ``useState<GrowthReport | null>``, "
        "so the name this function reads the whole answer through has to be re-found")
    binds = {bound.group(1): ""}
    for m in re.finditer(r"const (\w+) = " + bound.group(1) + r"\??\.(\w+);", text):
        binds[m.group(1)] = m.group(2)
    for m in re.finditer(r"\b(\w+)[?]{0,2}\s*:\s*GrowthReport\[\"(\w+)\"\]", text):
        binds[m.group(1)] = m.group(2)
    assert len(binds) > 2, (
        f"the page names only {sorted(binds)} of the report's blocks; the five aliases this "
        "file grades the page on are no longer all bound the same way")

    reads: set[str] = set()
    changed = True
    while changed:                          # a phase row holds the item list, and so on
        changed = False
        for m in re.finditer(r"\((\w+)(?:\?)?\.(\w+)[^()]*\)\s*\.map\(\(\s*(\w+)", text):
            alias, field, param = m.group(1), m.group(2), m.group(3)
            if alias in binds:
                base = f"{binds[alias]}.{field}" if binds[alias] else field
                if binds.get(param) != f"{base}[]":
                    binds[param] = f"{base}[]"
                    changed = True
        for m in re.finditer(r"(?=\b([A-Za-z_$]\w*)(?:\?)?\.([A-Za-z_$]\w*))", text):
            qual, field = m.group(1), m.group(2)
            if qual in binds and field not in _MEMBERS:
                reads.add(f"{binds[qual]}.{field}" if binds[qual] else field)
    return reads


def declared_fields(name: str) -> set[str]:
    """Field names a ``types.ts`` interface declares, nested literals included."""
    text = read(TYPES)
    for _ in range(4):
        alias = re.search(r"export type " + name + r" = (\w+);", text)
        if alias:
            name = alias.group(1)
            continue
        body = re.search(r"export interface " + name + r" \{(.*?)\n\}", text, re.S)
        assert body, f"types.ts declares no {name}"
        return {m.group(1) for m in re.finditer(r"^\s{2,}([A-Za-z_$]\w*)(\??):", body.group(1), re.M)}
    raise AssertionError(f"{name} is an alias cycle in types.ts")


def answer_leaves(emit: dict[str, set[str]]) -> dict[str, set[str]]:
    return {engine: leaves(p) for engine, p in emit.items()}


# ------------------------------------------------------------------ cases ----

def test_the_engines_answer_every_path_the_panel_reads():
    """Case 1: every path the panel reads exists in the engine's answer, at that depth."""
    emit = emitted()
    cases = panel_cases(read(PANEL))
    offenders = {}
    for engine in ENGINES:
        unmet = {p for p in read_paths(cases[engine]) if p not in emit[engine]}
        if unmet:
            offenders[engine] = sorted(unmet)
    assert not offenders, (
        "the panel reads paths no engine answers (an empty box on screen): "
        f"{offenders}\nanswers: "
        f"{ {e: sorted(emit[e])[:6] for e in offenders} }")


def test_every_engine_tab_renders_a_row_and_a_value():
    """Case 2: no engine is graded on an empty read set -- the vacuity this bug hid behind."""
    cases = panel_cases(read(PANEL))
    for engine in ENGINES:
        got = read_paths(cases[engine])
        assert len(got) >= 2, f"the {engine} case reads {sorted(got)}; nothing to grade here"
        assert re.search(r"data as " + ENGINE_TYPES[engine] + r"\b", cases[engine]), (
            f"the {engine} case no longer reads through {ENGINE_TYPES[engine]}: an inline "
            f"`as Array<{{...}}>` is where a stale field name hides")


def test_the_panel_names_the_row_fields_the_engines_put():
    """Case 3: the specific names this unit fixed, asserted as required paths.

    Case 1 refuses a name the engine lacks; this refuses the engine's name going
    unread. Both directions matter: a reader that stops rendering a row is as silent
    as one that renders it blank.
    """
    emit = emitted()
    cases = panel_cases(read(PANEL))
    required = {
        "gap": {"gaps", "gaps[].skill", "gaps[].importance", "coverage", "expectedSkillCount"},
        "demand": {"skills", "skills[].skill", "skills[].count"},
        "priority": {"prioritizedGaps", "prioritizedGaps[].skill", "prioritizedGaps[].priority",
                     "prioritizedGaps[].marketShare"},
        "plan": {"plan.phases", "plan.phases[].label", "plan.phases[].items[].topic"},
        "prep": {"weakAreas", "weakAreas[].skill", "strengthStories",
                 "strengthStories[].storyTitle"},
        "progression": {"steppingStones", "steppingStones[].family", "steppingStones[].reason",
                        "aspirationalMustGaps"},
        "stories": {"stories", "stories[].title", "stories[].bullets"},
        "roles": {"families", "families[].family", "families[].coverage"},
        "progress": {"previousCoverage", "currentCoverage", "closed", "improved", "regressed"},
    }
    for engine, want in required.items():
        got = read_paths(cases[engine])
        assert want <= got, f"the {engine} case stopped reading {sorted(want - got)}"
        assert want <= emit[engine], f"the {engine} engine no longer answers {sorted(want - emit[engine])}"


def test_no_engine_answer_is_read_as_a_fact_no_engine_states():
    """Case 4: the panel cannot claim a verdict the engines never emit.

    ``steps[].reachable`` is the shape this refuses: the progression engine scores a
    family's bridge and its current coverage, it never rules a step reachable or not.
    """
    panel = read(PANEL)
    for stale in ("reachable", "gated", "marketDemand", "sampleSize", ".evidence"):
        assert stale not in panel, f"the panel is back to stating {stale!r}"
    emit = emitted()
    assert not any(p.endswith(".reachable") for e in emit.values() for p in e), (
        "an engine now answers `reachable`, so case 4's refusal needs re-reading")


def test_types_ts_declares_the_names_the_engines_use():
    """Case 5: the declared contract is the engines' vocabulary, not a dialect of its own.

    Both levels are graded: the answer's own fields and the row types nested inside
    them, because ``gaps[].name`` and ``roles[].role`` were row-level lies.
    """
    emit = emitted()
    loose = answer_leaves(emit)
    row_types = [
        ("gap", "SkillRow"), ("demand", "DemandSkill"), ("priority", "LearningPriorityItem"),
        ("plan", "LearningItem"), ("prep", "PrepWeakArea"), ("prep", "PrepStrengthStory"),
        ("progression", "ProgressionStep"), ("stories", "Story"), ("roles", "SuggestedRole"),
    ]
    offenders = {}
    for engine, iface in list(ENGINE_TYPES.items()) + row_types:
        nesting_free = {"plan", "gap"} if iface == "LearningPlan" else set()
        unclaimed = {f for f in declared_fields(iface)
                     if f not in loose[engine] and f not in nesting_free}
        if unclaimed:
            offenders[f"{engine}:{iface}"] = sorted(unclaimed)
    assert not offenders, (
        f"types.ts declares fields no engine answers: {offenders}")


def test_types_ts_declares_every_shape_once():
    """Case 6: one author per wire name.

    ``LearningItem`` was declared twice with different fields, and the stale copy is
    the one the panel's neighbours kept reading -- so a duplicate is a rename that
    only half happened.
    """
    text = read(TYPES)
    names = [m.group(2) for m in re.finditer(r"export (interface|type) (\w+)", text)]
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, f"types.ts declares {dupes} twice"


def test_the_copilot_artifacts_read_the_same_two_answers():
    """Case 7: the second reader of the gap and priority engines.

    A card that stringifies a row dict says ``[object Object]`` on screen, which is
    worse than saying nothing: it is what the artifact surface did for every gap.
    """
    emit = emitted()
    text = read(ARTIFACTS)
    gap_block = text[text.index("function GapReportArtifact"):text.index("function SalaryBandArtifact")]
    prio_block = text[text.index("function LearningPriorityArtifact"):]
    assert re.search(r'list\(report, "gaps"\)', gap_block), "the gap card left `gaps`"
    assert re.search(r'str\(g, "skill"\)', gap_block), (
        "the gap card is back to a name the engine never puts on a row")
    assert not re.search(r"String\(g\)", gap_block), (
        "the gap card stringifies a row dict again, which paints [object Object]")
    assert re.search(r'list\(report, "prioritizedGaps"\)', prio_block), (
        "the priority card reads a key the ranking engine never answers")
    assert not re.search(r"String\(row\)", prio_block), (
        "the priority card is back to falling back to a stringified row dict, which paints "
        "[object Object] on the copilot")
    assert "priorities" not in text, f"`priorities` is back in the artifact surface"
    for engine, want in (("gap", "gaps[].skill"), ("priority", "prioritizedGaps")):
        assert want in emit[engine] or want.rstrip("[].skill") in emit[engine]


def test_the_bridge_hands_the_engines_dict_over_unchanged():
    """Case 8: the walk from panel to engine renames nothing.

    If the bridge ever re-keys an answer, the honest fix moves to the bridge and this
    file's premise (read the engine's names) is the wrong instruction -- so it is a
    claim worth refusing, not an assumption.
    """
    bridge = read(BRIDGE)
    post = bridge[bridge.index("private Map<String, Object> post("):]
    post = post[:post.index("\n    }") + 1]
    assert ".body(Map.class)" in post, (
        "post() no longer returns the engine's body as-is; re-read which layer renames keys")
    assert not re.search(r'put\("[a-zA-Z]+",', post), (
        "post() is rebuilding the answer under new keys")
    controller = read(ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "ai"
                      / "web" / "GrowthEngineController.java")
    assert "Map<String, Object>" in controller, (
        "the growth controller no longer passes the engines' maps through")


def test_the_refusal_works_on_a_reader_that_names_the_wrong_keys():
    """Case 9: this file's own judge is behavioral, not decorative.

    The fixture below is the panel as it shipped before #252 -- ``priorities``, a
    top-level ``phases``, a ``name`` on a gap row. Running the real checker over it
    must report exactly those paths, and must report the nesting one separately:
    ``phases`` is a true key of the plan engine, just not at the level the route answers.
    """
    emit = emitted()
    stale = '''
    case "gap": {
      const report = data as GapReport;
      {(report.gaps ?? []).map((g, i) => (<li key={i}>{g.name}</li>))}
    }
    case "priority": {
      const p = data as LearningPriority;
      {(p.priorities ?? []).map((row, i) => (<li key={i}>{row.skill} {row.marketDemand}</li>))}
    }
    case "plan": {
      const plan = data as LearningPlan;
      {(plan.phases ?? []).map((phase) => (<li key={phase.label}>{phase.phase}</li>))}
    }
    '''
    gap = read_paths(stale[stale.index('case "gap"'):stale.index('case "priority"')])
    prio = read_paths(stale[stale.index('case "priority"'):stale.index('case "plan"')])
    plan = read_paths(stale[stale.index('case "plan"'):])
    assert "gaps[].name" in gap and "gaps[].skill" not in gap
    assert "priorities" in prio and "priorities[].marketDemand" in prio
    assert "phases" in plan and "phases.label" not in emit["plan"]
    assert "phases.label" not in emit["plan"] and "plan.phases[].label" in emit["plan"]
    for engine, got in (("gap", gap), ("priority", prio), ("plan", plan)):
        assert {p for p in got if p not in emit[engine]}, (
            f"the stale {engine} reader passes the check: the judge is blind")


def test_the_learning_plan_route_answers_the_nesting_the_panel_reads(monkeypatch):
    """Case 10: the shipped seam, over HTTP, for the engine whose answer is wrapped.

    The panel's ``plan`` tab is the one claim here that is about a *route*, not an
    engine function, so it is measured through ``TestClient`` rather than trusted from
    the route's source text. ``analyze_gap`` is the LLM call: it is replaced by the
    same fixture the pure builders are graded against, so only the wrapper is exercised.
    """
    from app.api import features as features_api
    from app.core.config import get_settings
    from app.db import observability
    from app.features import gap_analysis
    from app.main import app
    from fastapi.testclient import TestClient

    answer = gap_answer()

    async def _gap(*args, **kwargs):
        return answer

    async def _resume(_user_id, _version):
        return {}, ""

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(gap_analysis, "analyze_gap", _gap)
    monkeypatch.setattr(features_api, "_resume_payload", _resume)
    monkeypatch.setattr(observability, "finish_run", _noop)
    monkeypatch.setattr(observability, "create_run", _noop)

    client = TestClient(app)                   # never a context manager: no lifespan, no pool
    headers = {"X-Internal-Token": get_settings().internal_api_token,
               "X-User-Id": "00000000-0000-0000-0000-0000000000aa",
               "X-Run-Id": "00000000-0000-0000-0000-000000bb"}
    r = client.post("/internal/features/learning-plan",
                    json={"target_role": "Senior Backend Engineer"}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"plan", "gap"}, (
        f"the route answers {sorted(body)}; the panel reads the phases under `plan`")
    assert isinstance(body["plan"]["phases"], list) and body["plan"]["phases"], (
        "the plan the route wrapped carries no phases to read")
    first = body["plan"]["phases"][0]
    assert {"phase", "label", "items"} <= set(first), sorted(first)
    assert "topic" in first["items"][0], sorted(first["items"][0])


def test_the_contract_doc_promises_no_verdict_the_engine_never_states():
    """Case 11: the third reader of the progression answer -- the doc the panel was written from.

    The panel rendered ``steps[].reachable`` and a ``gated`` badge because the two
    ``/progression`` rows in ``docs/API.md`` promised families "reachable today" and
    "reachable and gated". The engine scores a bridge and reports current coverage; it
    never rules a step reachable or gated. A reader follows the doc, so the doc is the
    site that has to refuse.
    """
    rows = [line for line in read(DOCS).splitlines()
            if "`/growth/progression`" in line or "`/internal/features/progression`" in line]
    assert len(rows) == 2, (
        f"the doc answers {len(rows)} progression rows; this case grades the public and "
        f"the internal one together: {rows}")
    for row in rows:
        for verdict in ("reachable", "gated"):
            assert verdict not in row, (
                f"the doc row is back to promising a {verdict!r} verdict the engine never "
                f"answers: {row}")
        assert "bridge" in row.lower(), (
            f"the row stopped naming the score the engine does answer: {row}")
    emit = emitted()["progression"]
    assert not [p for p in emit if p.endswith((".reachable", ".gated"))], (
        "the progression engine now answers a reachable/gated verdict, so this refusal "
        "and the doc row both need re-reading")


def test_the_growth_page_reads_only_paths_the_growth_report_answers(monkeypatch):
    """Case 12: the page's field names, graded against the route that feeds it.

    ``/growth`` is written against ``build_growth_report``'s nesting, not the engines':
    the phases live under ``learningPlan``, the progress lists under ``progress``, and
    ``readiness`` re-states two of the gap report's counts under its own names. The hook
    casts the response straight to ``GrowthReport`` and the bridge hands the ai-service
    dict over as a ``Map``, so every one of those reads is a claim about this answer.
    """
    answer = paths(aggregate(monkeypatch))
    reads = page_reads(read(PAGE))
    assert len(reads) >= 20, (
        f"the page reader found only {len(reads)} paths; it stopped binding aliases, and a "
        f"check over almost nothing is not a check: {sorted(reads)}")
    unmet = {p for p in reads if p not in answer}
    assert not unmet, (
        f"the growth page reads paths the report does not answer: {sorted(unmet)}\n"
        f"the answer carries: {sorted(p for p in answer if p.count('.') < 3)[:12]}")


def test_the_growth_page_shows_every_skill_list_the_progress_diff_answers(monkeypatch):
    """Case 13: a state the diff can name is a state the card has to draw.

    ``diff_progress`` returns five skill lists; the page drew three -- ``closed``,
    ``improved``, ``regressed`` -- and ``opened`` (a gap the previous report never
    listed at all, because the expected set moved under the user) had no reader anywhere
    in the frontend. The exemption is structural: a count or a role name is derived
    arithmetic, but a list of skills is a verdict about a skill the user can act on.
    """
    progress = aggregate(monkeypatch)["progress"]
    lists = {k for k, v in progress.items() if isinstance(v, list)}
    assert lists, "the progress diff answers no skill list at all"
    empty = {k for k in lists if not progress[k]}
    assert not empty, (
        f"{sorted(empty)} is an empty list in this fixture, so the page could stop reading "
        f"it and nothing here would notice; rebuild previous_report() so every state moves "
        f"(it is graded to make exactly that impossible)")
    shown = {p.rsplit(".", 1)[-1] for p in page_reads(read(PAGE)) if p.startswith("progress.")}
    missing = lists - shown
    assert not missing, (
        f"the diff answers {sorted(missing)} and the progress card never draws it: a skill "
        f"state the engine names is a state the user is not shown (lists: {sorted(lists)})")


#: Item keys the learning engine consumes itself: ``phase_of(category)`` files the row,
#: ``PHASES[i["phase"]]["order"]`` and ``_PRIORITY_ORDER[i["priority"]]`` sort it. They
#: are the row's filing slip, not its text, so the page owes them no reader.
_ROW_GROUPING = {"category", "phase"}
#: The row's own face: what to study and how urgent it is. Neither is prose-shaped, so
#: case 14's derived rule cannot see them and they are pinned by name instead.
_ROW_SUBJECT = {"topic", "priority"}


def test_the_growth_plan_row_shows_the_text_the_learning_engine_writes(monkeypatch):
    """Case 14: the plan row shows what the engine wrote for it, not only part of it.

    Every item carries ``resource_hint`` -- "the official docs and a small hands-on
    exercise", "write a project bullet that quantifies this skill" -- and the page showed
    ``note`` (which only the half-covered rows carry) beside the topic. So the plan said
    *what* and never *with what*, on every row of it.

    Which fields are row text is derived, not decided here: a field whose filled value is
    a string with a space in it is something the engine wrote to be read. That leaves
    ``category`` and ``phase`` as the filing slip, and the two exemptions are asserted
    equal to the named set above -- so a new field that is neither prose nor a pinned
    subject reds this case instead of going unread.
    """
    items = [item for phase in aggregate(monkeypatch)["learningPlan"]["phases"]
             for item in phase["items"]]
    assert items, "the plan the aggregate nests has no rows, so nothing here is graded"
    fields = set().union(*(item for item in items))
    prose = {f for f in fields
             if any(isinstance(i.get(f), str) and " " in i[f] for i in items)}
    assert prose == {"resource_hint", "note"}, (
        f"the engine now fills {sorted(prose)} as row text; the exemption set below is "
        f"argued against exactly resource_hint and note")
    shown = {p.rsplit(".", 1)[-1] for p in page_reads(read(PAGE))
             if p.startswith("learningPlan.phases[].items[].")}
    unshown = prose - shown
    assert not unshown, (
        f"the plan row drops {sorted(unshown)}: text the engine fills for the row and no "
        f"reader answers (the row reads {sorted(shown)})")
    assert _ROW_SUBJECT <= shown, (
        f"the row reads {sorted(shown)}; topic and priority are its subject and its badge")
    assert _ROW_SUBJECT <= fields, (
        "the learning engine stopped filling topic/priority, so the page's row is reading "
        "names no item carries")
    assert fields - prose - _ROW_SUBJECT == _ROW_GROUPING, (
        f"item fields outside the row text and the row subject are "
        f"{sorted(fields - prose - _ROW_SUBJECT)}, not the filing slip {sorted(_ROW_GROUPING)}: "
        "a field has appeared that this case has no argument for leaving unread")


def test_the_growth_page_branches_only_on_values_the_engines_answer(monkeypatch):
    """Case 15: the page's string comparisons are claims as much as its field names.

    ``VERDICT_VARIANT`` colours a verdict, the priority badge asks for ``"must"``, and the
    salary chart names ``p25/p50/p75``. A renamed value is invisible to a path check: the
    read succeeds, the branch never fires, and the UI silently stops meaning anything.
    """
    text = read(PAGE)
    block = text[text.index("const VERDICT_VARIANT"):]
    variants = set(re.findall(r'^\s+(\w+):', block[:block.index("};")], re.M))
    assert variants, "the page no longer keeps a verdict->variant table to grade"

    verdict_src = read(FEATURES / "readiness.py")
    fn = verdict_src[verdict_src.index("def skill_verdict"):]
    spellings = set(re.findall(r'return "(\w+)"', fn[:fn.index("\n\n")]))
    assert spellings, "skill_verdict no longer returns verdict names this case can read"
    assert variants == spellings, (
        f"the page colours {sorted(variants)} and the readiness engine answers "
        f"{sorted(spellings)}: a verdict in the second list renders no badge, and one in "
        "the first is a spelling no producer emits")

    compared = set(re.findall(r"\.priority === \"(\w+)\"", text))
    assert compared, "the page no longer branches on a plan item's priority"
    order = re.search(r"_PRIORITY_ORDER = \{([^}]*)\}", read(FEATURES / "learning.py"))
    assert order, "learning.py no longer declares the priority order the badge is keyed on"
    priorities = set(re.findall(r'"(\w+)":', order.group(1)))
    assert compared <= priorities, (
        f"the badge asks for {sorted(compared - priorities)}, which the learning engine's "
        f"own order ({sorted(priorities)}) never assigns: the must-row renders as secondary")

    band = set(re.findall(r'"(p\d+)"', text))
    assert band, "the page no longer names the percentiles it draws"
    answered = set(aggregate(monkeypatch)["salary"]["percentiles"])
    assert answered, "the salary answer carries no percentile to draw, so this is blind"
    assert band <= answered, (
        f"the chart draws {sorted(band - answered)}, which the benchmark does not answer "
        f"(it answers {sorted(answered)})")


#: The word each block of the answer is called by in the doc row that promises it.
_DOC_BLOCK_WORDS = {"readiness": "readiness", "gap": "gap", "salary": "salary",
                    "learningPlan": "plan", "progress": "progress"}


def test_the_contract_doc_names_every_block_the_growth_report_answers(monkeypatch):
    """Case 16: the row a caller reads has to list all five parts, not the three it began with.

    ``docs/API.md`` answered the internal route with ``readiness + gap + salary``, while
    ``build_growth_report`` has composed five blocks since Epic 10.8 and the page draws
    every one of them. A caller that trusts the row keeps calling the seven granular
    routes for a learning plan and a progress diff it was already being handed.
    """
    rows = [line for line in read(DOCS).splitlines()
            if "`/internal/features/growth-report`" in line]
    assert len(rows) == 1, f"the doc answers {len(rows)} internal growth-report rows: {rows}"
    answered = set(aggregate(monkeypatch))
    named = {block for block, word in _DOC_BLOCK_WORDS.items() if word in rows[0]}
    assert named == answered, (
        f"the row names {sorted(named)} but the report answers {sorted(answered)} -- the "
        f"gap between the two is a caller paying for the granular routes it does not need "
        f"(words: {sorted(_DOC_BLOCK_WORDS.items())})")
