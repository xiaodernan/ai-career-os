"""A duration has a direction, and four carriers hand the engine pairs that violate it.

#251 found ``_days_between`` written as ``lo, hi = sorted([s, e]); return max(0.0, hi - lo)``.
That computes the *distance* between two moments, so it cannot tell a reply that took seven
days from a history that says the interview happened before the application was submitted --
and it cannot tell forty days of silence from a submission stamped forty days from now. Both
lies went out through the shipped routes and landed on the analysis page as numbers: a row
whose ``applied_at`` pointed at next month was listed under "Stalled applications" as ``40d``,
complete with the signal "1 application(s) have gone quiet past 14 days".

Nothing upstream could have caught either pair, and that is not an assumption -- cases 3 and 4
read the two carriers that produce them:

* ``ApplicationInput`` declares every timestamp as ``str | None``, so ``/internal/features/*``
  accepts whatever ISO string the caller posted and the engine owns the whole bound.
* ``ImportService.time(row, "applied_at")`` parses the candidate's own bundle with
  ``OffsetDateTime.parse`` and never compares it to a clock, and ``ApplicationDtos`` declares
  no ``@Past``. ``ApplicationService`` sets ``appliedAt`` to ``now()`` when the row is moved to
  applied -- which is exactly why the import path is the reachable one.
* The bridge then serialises the stored value verbatim, while the stage moments come out of
  the status-transition log. Two independent clocks on one row is the product, not an edge case.

So the refusal belongs here, and this file grades it in every language that touches it: the
helper's own syntax, the digest's choice of which moment dates a row, the request model, the
Java import path, a real request through the route, the other metrics that must keep counting
the row whose duration was refused, and the two ``docs/API.md`` rows that promise the numbers.
"""

import ast
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
PY_APP = ROOT / "ai-service" / "app"
ANALYTICS = PY_APP / "features" / "analytics.py"
FEATURES_API = PY_APP / "api" / "features.py"
JAVA = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros"
IMPORT_SERVICE = JAVA / "report" / "service" / "ImportService.java"
ANALYSIS_SERVICE = JAVA / "report" / "service" / "AnalysisService.java"
DTOS = JAVA / "application" / "dto" / "ApplicationDtos.java"
DOC = ROOT / "docs" / "API.md"

# The seven timestamp fields a row can carry, in the spelling the sender uses.
TIMESTAMP_FIELDS = ["applied_at", "oa_at", "interview_at", "final_round_at",
                    "offer_at", "created_at", "last_seen"]


# --------------------------------------------------------------------------- reading helpers


def read(path: Path) -> str:
    """Shipped text with LF endings; a frozen plane on this host hands out CRLF."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=None)
def _tree(path: Path) -> ast.Module:
    return ast.parse(read(path))


def func(name: str, path: Path = ANALYTICS) -> ast.FunctionDef:
    for node in _tree(path).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{path.name} declares no function named {name}")


def _loads(node: ast.AST) -> set[str]:
    """Names this subtree reads (not binds)."""
    return {n.id for n in ast.walk(node)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def _calls(node: ast.AST) -> set[str]:
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                out.add(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                out.add(n.func.attr)
    return out


def java_method(path: Path, name: str) -> str:
    """One Java method *declaration*, read by counting braces from its own body.

    A regex over ``[^)]*`` cannot delimit a body that contains calls, and a scan that finds
    nothing here would make every absence claim below free. The opening brace directly after
    the parameter list is what separates a declaration from a call site: matching on the bare
    name reads ``time(row, "applied_at")`` -- the call -- and hands back the rest of the file.
    """
    src = read(path)
    m = re.search(rf"\b{name}\s*\(([^()]|\([^()]*\))*\)\s*\{{", src)
    assert m, f"{path.name} declares no method named {name}"
    open_at = src.index("{", m.end() - 1)
    depth = 0
    for i in range(open_at, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():i + 1]
    raise AssertionError(f"unbalanced braces reading {name} in {path.name}")


def importer_verbatim_fields() -> set[str]:
    """Bundle fields ``ImportService`` reads with ``time(row, "…")`` -- no clock in sight.

    This is the list the digest row's origin claim is graded against: a field the importer does
    not copy has no route from a caller's bundle into the stored row, so a row that blames one
    for a next-month stamp explains nothing. Derived from the sender rather than retyped here,
    so the day the importer gains or drops a timestamp field the doc has to move with it.
    """
    fields = set(re.findall(r'time\(row, "(\w+)"\)', read(IMPORT_SERVICE)))
    assert fields, f"{IMPORT_SERVICE.name} copies no bundle timestamp through time(row, …)"
    return fields


def doc_row(route: str) -> str:
    """The API.md table row whose *route cell* is ``route``, verbatim.

    Matched on the cell, not on a substring: the digest row cross-references the funnel row,
    and a search by name would grade the referencing row for the referenced one.
    """
    for line in read(DOC).splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.split("|")]
        if len(cells) >= 4 and cells[2] == route:
            return collapse(line)
    raise AssertionError(f"docs/API.md has no table row whose route cell is {route}")


# --------------------------------------------------------------------------- 1. the helper


def test_the_duration_helper_reads_the_clock_it_asks_for():
    """``now`` was a parameter the function took, normalised and never looked at.

    The ruff F841 that the dead ``ref`` assignment produced was the visible half. The invisible
    half is that a caller could hand this helper a clock and the answer would not change -- so
    the digest's "measured from the moment the answer was generated" was a comment, not a bound.
    """
    f = func("_days_between")
    params = [a.arg for a in f.args.args]
    assert params == ["start", "end", "now"], (
        f"_days_between now takes {params}; the clock is the only reason a pair can be refused "
        "for lying in the future, and a helper that takes it must read it")

    statements = f.body[1:] if (f.body and isinstance(f.body[0], ast.Expr)
                                and isinstance(f.body[0].value, ast.Constant)) else f.body
    read_names: set[str] = set()
    for stmt in statements:
        read_names |= _loads(stmt)
    for p in params:
        assert p in read_names, (
            f"_days_between binds {p} and never reads it -- a parameter the answer does not "
            "depend on is the seam where the future stamp was ignored")

    # The dead value was a local, not a parameter: the shipped helper normalised ``now`` into
    # ``ref`` and then subtracted the sorted pair without it. Ruff called that F841; the claim
    # is bigger than the lint, because the normalised clock was the bound nobody applied.
    for stmt in statements:
        for t in (ast.walk(stmt) if isinstance(stmt, ast.Assign) else []):
            if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store):
                assert t.id in read_names, (
                    f"_days_between computes {t.id} and never reads it: a value this function "
                    "discards is a bound the caller was told it had")


def test_the_helper_no_longer_measures_the_distance_between_two_moments():
    """The charged spellings are the ones that made an impossible history look healthy.

    ``sorted([s, e])`` destroyed the sign and ``max(0.0, ...)`` destroyed the remainder; both
    are forbidden by name here and refused by behaviour in ``test_analytics.py``, so neither can
    come back as a "defensive" clamp.
    """
    f = func("_days_between")
    calls = _calls(f)
    assert "sorted" not in calls, (
        "_days_between sorts its pair again: an application submitted after its own interview "
        "is two clocks disagreeing, and sorting them reports the disagreement as a reply time")
    assert "max" not in calls, (
        "_days_between clamps a negative again, which is how a future stamp became an age")
    returns = [n for n in ast.walk(f) if isinstance(n, ast.Return)]
    asserts_none = any(isinstance(r.value, ast.Constant) and r.value.value is None
                       for r in returns)
    assert asserts_none, "_days_between has no path that refuses a pair; it only ever subtracts"


# --------------------------------------------------------------------------- 2. the digest


def test_the_digest_dates_a_row_only_from_moments_that_have_arrived():
    """Which of the row's three timestamps is "last activity" is itself the defect's seat.

    ``max`` over the stamps let a future ``applied_at`` win, and then the age came out of a
    moment that has not happened. The fix drops the unarrived moments before the max, so a row
    imported with a next-month date and an April ``created_at`` is still honestly stalled at 45
    days -- the row stays, the lie goes. ``default=None`` is what keeps an all-future row out of
    the list instead of crashing it in, and the case pins that too.
    """
    f = func("insight_digest")
    assign = [n for n in ast.walk(f)
              if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == "last" for t in n.targets)]
    assert len(assign) == 1, f"the digest dates a row through {len(assign)} 'last' bindings"
    stmt = assign[0]

    assert "max" in _calls(stmt), "the digest no longer picks the row's latest moment at all"
    compares = [n for n in ast.walk(stmt) if isinstance(n, ast.Compare)]
    bounded = [n for n in compares
               if any(isinstance(op, (ast.LtE, ast.Lt)) for op in n.ops)
               and "ref" in _loads(n)]
    assert bounded, (
        "the row's candidate moments are not compared against the digest clock, so a stamp from "
        "next month wins the max again and the row is aged from time that has not passed")
    max_call = next(n for n in ast.walk(stmt)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "max")
    kw = {k.arg for k in max_call.keywords}
    assert "default" in kw, (
        "max() over the row's moments lost its default: a row of nothing but future stamps "
        "would raise instead of being reported as staleness-unknown")


# --------------------------------------------------------------------------- 3. the request model


def test_nothing_between_the_posted_row_and_the_engine_bounds_a_timestamp():
    """The engine owns this bound because the boundary deliberately holds no opinion.

    Every timestamp ``ApplicationInput`` declares is ``str | None``: no ``datetime`` coercion,
    no validator, no ``@Past``. That is what lets an imported bundle's future date reach
    ``insight_digest`` as a string the engine itself parses, and it is why a refusal inside
    ``_days_between`` is load-bearing rather than belt-and-braces. If a later change bounds the
    model, this case goes red and the claim has to be re-argued, not silently orphaned.
    """
    tree = _tree(FEATURES_API)
    cls = next((n for n in tree.body
                if isinstance(n, ast.ClassDef) and n.name == "ApplicationInput"), None)
    assert cls, "app/api/features.py no longer declares ApplicationInput"

    declared = {t.id: ast.unparse(a) for n in cls.body if isinstance(n, ast.AnnAssign)
                for t in [n.target] if isinstance(t, ast.Name)
                for a in [n.annotation]}
    for field in TIMESTAMP_FIELDS:
        assert field in declared, f"ApplicationInput lost {field}, which the bridge sends"
        assert declared[field] == "str | None", (
            f"ApplicationInput.{field} is now {declared[field]!r}: if the boundary coerces or "
            "bounds timestamps, re-check who refuses an impossible pair -- this file's claim is "
            "that the engine is the only one")

    src = ast.unparse(cls)
    for banned in ("field_validator", "model_validator", "Past", "le="):
        assert banned not in src, (
            f"ApplicationInput now mentions {banned!r}; the request model was the plane where no "
            "bound existed, which is what made the engine's refusal necessary")


# --------------------------------------------------------------------------- 4. the Java import


def test_the_import_path_stores_the_applied_at_it_was_given():
    """The reachable source of a future ``applied_at``, read off the sender, not assumed.

    ``ApplicationService`` sets ``appliedAt = OffsetDateTime.now()`` when a row is moved to
    applied, so the API cannot forge one -- but ``ImportService`` writes the value out of the
    candidate's own bundle, and the bridge then serialises it verbatim while the stage moments
    come from the status-transition log. The test also pins the two things that are *not* there
    (a clock comparison in the parser, a past-ness annotation on the DTO), because a guard that
    no entry point arms is the same lie as a doc that claims one.
    """
    src = read(IMPORT_SERVICE)
    assert 'setAppliedAt(time(row, "applied_at"))' in src, (
        "ImportService no longer writes the bundle's applied_at, so this case's premise expired")

    time_method = java_method(IMPORT_SERVICE, "time")
    assert "OffsetDateTime.parse" in time_method, (
        f"time(...) no longer parses the bundle's string ({collapse(time_method)[:160]!r})")
    for bound in ("isBefore", "isAfter", "now(", "Clock"):
        assert bound not in time_method, (
            f"time(...) now mentions {bound!r}: the import bounded the stamp upstream, so the "
            "engine's refusal needs re-reading (and this claim needs re-aiming)")

    dtos = read(DTOS)
    assert "@Past" not in dtos and "@PastOrPresent" not in dtos, (
        "ApplicationDtos bounds a timestamp upstream; who refuses an impossible pair changes")

    bridge = read(ANALYSIS_SERVICE)
    assert 'row.put("applied_at", a.getAppliedAt().toString())' in bridge, (
        "AnalysisService stopped sending the stored applied_at verbatim -- the value the engine "
        "reads is no longer the value the bundle carried, so re-check what this case proves")


# --------------------------------------------------------------------------- 5. the shipped route


def test_the_route_answers_a_future_row_without_an_age():
    """The engine's unit tests could be green while the HTTP surface still lies.

    ``/internal/features/insight-digest`` builds ``ref`` from the server clock, so a row posted
    with a ``applied_at`` forty days ahead is exactly what the product would age wrongly. This
    drives the real request: no age is emitted, and the honest row beside it still is.
    """
    from app.core.config import get_settings
    from app.db import observability
    from app.main import app
    from fastapi.testclient import TestClient

    async def _noop(*args, **kwargs):
        return None

    observability.finish_run = _noop            # patched, not mocked: no run row is created
    observability.create_run = _noop
    client = TestClient(app)                     # never a context manager: no lifespan, no pool
    headers = {"X-Internal-Token": get_settings().internal_api_token,
               "X-User-Id": "00000000-0000-0000-0000-0000000000aa",
               "X-Run-Id": "00000000-0000-0000-0000-0000000000bb"}
    wall = datetime.now(timezone.utc)

    def post(path, applications, **extra):
        r = client.post(f"/internal/features/{path}",
                        json={"applications": applications, **extra}, headers=headers)
        assert r.status_code == 200, r.text
        return r.json()

    future = (wall + timedelta(days=40)).isoformat()
    quiet = (wall - timedelta(days=40)).isoformat()

    d = post("insight-digest", [{"id": "a1", "status": "applied", "applied_at": future}],
             stale_days=14)
    assert d["stalled"] == [] and d["stalledCount"] == 0, (
        f"the route aged a submission that has not happened yet: {d['stalled']}")
    assert not any("没有动静" in s for s in d["signals"]), d["signals"]
    # the row is still an application; only its age is refused
    assert d["totalApplications"] == 1 and d["stageCounts"].get("applied") == 1

    mixed = post("insight-digest", [{"id": "a2", "status": "applied", "applied_at": future,
                                     "created_at": (wall - timedelta(days=45)).isoformat()}],
                 stale_days=14)
    assert [s["daysSinceLastActivity"] for s in mixed["stalled"]] == [45], (
        f"a row quiet since April vanished because one of its stamps was a typo: {mixed['stalled']}")

    honest = post("insight-digest", [{"id": "a3", "status": "applied", "applied_at": quiet}],
                  stale_days=14)
    assert [s["daysSinceLastActivity"] for s in honest["stalled"]] == [40], (
        f"the exclusion swallowed a real stall: {honest['stalled']}")

    r = post("response-rate", [{"id": "a4", "status": "interview",
                                "applied_at": (wall + timedelta(days=2)).isoformat(),
                                "interview_at": quiet}])
    assert r["timeInStage"]["interview"]["n"] == 0, (
        f"the route timed an interview that predates its own application: {r['timeInStage']}")
    assert r["interviewCount"] == 1 and r["appliedCount"] == 1


# --------------------------------------------------------------------------- 6. the over-fix guard


def test_a_refused_duration_never_deletes_the_application():
    """Refusing to age a row is not licence to drop it from the numbers that do not need a clock.

    The funnel counts positions, the rates count replies, the mix counts rows -- none of them
    reads a timestamp. A "fix" that filters impossible rows out of ``_norm`` would empty the
    digest for anyone with one mistyped date, and every count here would still add up.
    """
    from app.features import analytics as A

    now = datetime(2026, 10, 14, tzinfo=timezone.utc)
    rows = [
        {"id": "f1", "status": "applied",
         "applied_at": (now + timedelta(days=40)).isoformat()},
        {"id": "f2", "status": "interview", "applied_at": (now + timedelta(days=3)).isoformat(),
         "interview_at": (now - timedelta(days=40)).isoformat()},
    ]
    d = A.insight_digest(rows, now=now, stale_days=14)
    f = A.pipeline_funnel(rows)
    r = A.response_rate(rows, now=now)

    assert d["stalled"] == [] and d["stalledCount"] == 0
    assert d["totalApplications"] == 2 and sum(d["stageCounts"].values()) == 2
    assert d["stageCounts"] == {"applied": 1, "interview": 1}
    # the funnel credits the interview row to every stage it passed, timestamp or not
    assert f["totalApplications"] == 2 and f["appliedCount"] == 2
    assert {s["stage"]: s["count"] for s in f["pipeline"]}["interview"] == 1
    assert r["appliedCount"] == 2 and r["interviewCount"] == 1 and r["respondedCount"] == 1
    assert r["timeInStage"]["interview"]["n"] == 0
    assert all(s["daysSinceLastActivity"] >= 0 for s in A.insight_digest(
        rows + [{"id": "f3", "status": "applied",
                 "applied_at": (now - timedelta(days=90)).isoformat()}],
        now=now, stale_days=14)["stalled"])


# --------------------------------------------------------------------------- 7. the docs


def test_the_two_doc_rows_each_promise_the_refusal_they_own():
    """The page's copy and the API's rows are what a reader grades the number against.

    The digest row has to say which of the row's timestamps dates it and what happens when none
    qualifies; the response-rate row already promised that a missing timestamp is skipped rather
    than counted as zero, and has to promise the same for a pair that cannot be a duration. Each
    half is graded in its own row: the digest row may not borrow the rate row's sentence, and
    neither may claim the numbers are clamped.

    The digest row also has to say *where* a next-month stamp comes from, because a reader who
    cannot picture the input does not know the exclusion is deliberate -- and that sentence is a
    claim about the sender, so it is graded as one: the field it names, inside the sentence that
    refuses the stamp, has to be one ``ImportService`` copies out of the bundle through a parser
    with no clock in it (case 4). A row that only says "a bundle" or blames a field the import
    never writes keeps the reader holding a story the code does not tell.
    """
    digest = doc_row("/analysis/insight-digest")
    rate = doc_row("/analysis/response-rate")

    assert re.search(r"latest of its timestamps that has already passed", digest), (
        f"the digest row no longer says which moment dates a stalled row: {digest[:220]!r}")
    assert "left out" in digest, (
        f"the digest row promises an age for a row with nothing but future stamps: {digest[:220]!r}")
    origin = re.search(r"a stamp from next month(?P<why>.*?)is not evidence of silence", digest)
    assert origin, (
        "the digest row no longer frames where the stamp comes from inside the sentence that "
        f"refuses it, so the two claims are unbound: {digest[:220]!r}")
    assert "bundle" in origin["why"], (
        "the digest row does not name where a next-month stamp comes from, so a reader cannot "
        f"tell the exclusion is deliberate: {origin[0]!r}")
    blamed = set(re.findall(r"`(\w+)`", origin["why"]))
    assert blamed, (
        f"{origin[0]!r}: the row points at a bundle without naming the field, and there is no "
        "claim for a reader to check against the sender")
    verbatim = importer_verbatim_fields()
    assert blamed <= verbatim, (
        f"{sorted(blamed - verbatim)} is not a field the importer copies with an unbounded clock "
        f"({sorted(verbatim)}): the next-month stamp the row explains away has no route from the "
        "caller's bundle into the stored row, so the sentence promises a reachability the "
        "sender does not have")

    assert "before the submission" in rate, (
        f"the response-rate row still counts an impossible history as a reply: {rate[:220]!r}")
    assert "skipped" in rate and "counted as zero" in rate, (
        f"the response-rate row lost the skip promise it already made: {rate[:220]!r}")
    assert re.search(r"later than the generated-at stamp|than the generated-at", rate), (
        f"the response-rate row does not name the clock the pair is bounded by: {rate[:220]!r}")

    for row, name in ((digest, "digest"), (rate, "response-rate")):
        assert "clamp" not in row, (
            f"the {name} row promises a clamped number, which is the spelling that hid the defect")
