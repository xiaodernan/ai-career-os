"""Every count a share chart divides by its own total is a distribution, in all three languages.

#250 found the analysis page's stage-mix card drawing shares of a total no account has. The
engine built ``stageCounts`` from ``pipeline_funnel``, whose ``reached`` counts credit one
application to *every* stage it passed: five applications sitting at five positions came back
as seven counts, and ``ShareChart`` (``components/common/bar-chart.tsx``) normalises each value
by ``data.reduce((sum, d) => sum + d.value, 0)``. So "applied" was drawn as 1 of 7 while three
quarters of the pipeline sat there, ``saved`` never appeared at all, and the card's own copy --
"Applications at each pipeline stage." -- described a number the engine had never produced.

Two shapes share a column and must not share a function:

* **a distribution** -- where each application is right now. Adds up to the number of rows. This
  is what a share, a stack or a pie may be drawn from.
* **a funnel** -- how many applications reached each stage. Deliberately does not add up, because
  reaching the offer means passing the four stages before it.

The engine unit tests could not have found this: they asserted the funnel's reached-counts and
the digest's mix by reading whichever number the fixture produced, so converting the mix into a
distribution was invisible to them. What makes the claim checkable is that the vocabulary it is
built from is spelled in three languages, and the shape is read by a component that divides by
it -- so this file pins the seven positions across ``analytics.py``, ``ApplicationService.java``,
``pipeline.ts`` and ``types.ts``, the digest's own return expression, the page's chart feed, the
doc row that promises the mix, and the backend test stub that hands the shape out.
"""

import ast
import re
from functools import lru_cache
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
FEATURES = ROOT / "ai-service" / "app" / "features"
ANALYTICS = FEATURES / "analytics.py"
JAVA = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros"
APP_SERVICE = JAVA / "application" / "service" / "ApplicationService.java"
FAKE = (ROOT / "backend" / "src" / "test" / "java" / "com" / "careeros"
        / "support" / "FakeAiServiceClientConfig.java")
TS = ROOT / "frontend" / "src"
PIPELINE_TS = TS / "lib" / "pipeline.ts"
TYPES_TS = TS / "lib" / "api" / "types.ts"
PAGE = TS / "app" / "(app)" / "analysis" / "page.tsx"
DOC = ROOT / "docs" / "API.md"

# The seven positions are the whole vocabulary; a scan that lost one would still be able to
# agree with itself, so the count is pinned before any comparison is made.
POSITIONS = 7

# The engine's own order, and the order the board and the type union are written in. The
# backend declares a Set, which has no order, so it is graded as a set against this list.
BOARD_ORDER = ["saved", "applied", "oa", "interview", "final_round", "offer", "rejected"]


# --------------------------------------------------------------------------- reading helpers


def read(path: Path) -> str:
    """Shipped text with LF endings; ``git archive`` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def balanced(text: str, open_at: int, opener: str, closer: str) -> int:
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"no matching {closer!r} after offset {open_at}")


@lru_cache(maxsize=None)
def _analytics_tree() -> ast.Module:
    return ast.parse(read(ANALYTICS))


def _engine_list(name: str) -> list[str]:
    """A module-level ``NAME = ["a", "b"]`` literal, read off the syntax tree."""
    for node in _analytics_tree().body:
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.List)
                and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)):
            return [ast.unparse(element).strip("'\"") for element in node.value.elts]
    raise AssertionError(f"analytics.py no longer declares {name} as a list literal")


def engine_stages() -> list[str]:
    return _engine_list("STAGES")


def engine_pipeline() -> list[str]:
    return _engine_list("PIPELINE")


def _java_string_set(path: Path, name: str) -> set[str]:
    """The literals of ``<NAME> = Set.of("a", "b", …)`` -- the spellings Java declares."""
    text = collapse(read(path))
    decl = re.search(rf"\b{name}\s*=\s*Set\.of\(([^)]*)\)", text)
    assert decl, f"{path.name} no longer declares {name} as a Set.of literal"
    values = set(re.findall(r'"([^"]+)"', decl.group(1)))
    assert values, f"{path.name}.{name} reads empty: {decl.group(1)!r}"
    return values


def backend_statuses() -> set[str]:
    return _java_string_set(APP_SERVICE, "STATUSES")


def board_stages() -> list[str]:
    """The order the kanban board renders, from ``APPLICATION_STAGES`` in the page's own module."""
    text = collapse(read(PIPELINE_TS))
    table = re.search(r"APPLICATION_STAGES[^=]*=\s*\[(.*?)\];", text)
    assert table, "pipeline.ts no longer declares APPLICATION_STAGES as an array literal"
    order = re.findall(r'\{\s*value:\s*"([^"]+)"', table.group(1))
    assert order, f"APPLICATION_STAGES reads empty: {table.group(1)[:120]!r}"
    return order


def status_union() -> list[str]:
    """``type ApplicationStatus = | "saved" | ...`` -- the spellings the frontend can hold."""
    text = read(TYPES_TS)
    decl = re.search(r"type ApplicationStatus\s*=\s*([^;]+);", text)
    assert decl, "types.ts no longer declares ApplicationStatus as a string union"
    return re.findall(r'"([^"]+)"', decl.group(1))


def strip_comments(text: str) -> str:
    """TSX comments blanked out, strings left alone.

    The page's own prose is full of apostrophes ("the funnel's own colour"), and a scanner that
    tracks quotes without tracking comments starts a string inside a comment and never ends it --
    which makes every bracket after it invisible and the tag look unclosed. Comments go first.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end == -1 else end + 2
            out.append(" " * (end - i))
            i = end
        elif text.startswith("//", i):
            end = text.find("\n", i)
            end = n if end == -1 else end
            out.append(" " * (end - i))
            i = end
        elif ch in "\"'`":
            end = i + 1
            while end < n:
                if text[end] == "\\":
                    end += 2
                    continue
                if text[end] == ch:
                    break
                end += 1
            out.append(text[i:end + 1])
            i = end + 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def jsx_element(text: str, component: str) -> list[str]:
    """Every ``<Component ... />`` in a page, with its prop expressions intact.

    The scan is character-wise with bracket and string depth over comment-blanked text: a JSX
    open tag is full of ``=>``, so the first ``>`` after the name is almost never the one that
    ends it.
    """
    source = strip_comments(text)
    opening = re.compile(rf"<{component}(?=[\s/>])")
    out = []
    for m in opening.finditer(text):
        i, depth, quote = m.end(), 0, None
        while i < len(source):
            ch = source[i]
            if quote:
                if ch == quote:
                    quote = None
            elif ch in "\"'`":
                quote = ch
            elif ch in "{([":
                depth += 1
            elif ch in "})]":
                depth -= 1
            elif ch == ">" and depth == 0:
                break
            i += 1
        assert i < len(source), f"<{component}> never closes in the page"
        if source[i - 1] == "/":
            out.append(text[m.start():i + 1])
            continue
        # an element with children: run to the closing tag that has no same-named element open
        closing = f"</{component}>"
        scan = i + 1
        while True:
            at = source.find(closing, scan)
            assert at != -1, f"<{component}> has no closing tag in the page"
            if not opening.search(text[i + 1:at]):
                break
            scan = at + len(closing)
        out.append(text[m.start():at + len(closing)])
    return out


def prop_expression(element: str, prop: str) -> str:
    """The source of one JSX prop, braces balanced -- ``data={...}`` including its object literal."""
    at = re.search(rf"\b{prop}=\{{", element)
    assert at, f"no {prop}={{...}} prop in {element[:120]!r}"
    brace = element.index("{", at.end() - 1)
    return element[brace + 1:balanced(element, brace, "{", "}")].strip()


def doc_row(route: str) -> str:
    """The API.md table row whose *route cell* is ``route``, verbatim.

    Matched on the cell, not on a substring: the digest row now cross-references
    ``/analysis/pipeline-funnel``, and a search by name would grade the referencing row for the
    referenced one and call both claims satisfied.
    """
    for line in read(DOC).splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.split("|")]
        if len(cells) >= 4 and cells[2] == route:
            return collapse(line)
    raise AssertionError(f"docs/API.md has no table row whose route cell is {route}")


# --------------------------------------------------------------------------- the fixtures


def _rows():
    """Five applications, one at each of five positions, spelled the way the bridge sends them.

    The keys are the eleven ``ApplicationInput`` fields #249 established, so a row here is a row
    the endpoint receives -- not a row the test invented.
    """
    return [
        {"id": f"a{i}", "status": status, "title": f"Role {i}", "company": "FakeCorp",
         "applied_at": applied, "oa_at": None, "interview_at": None, "final_round_at": None,
         "offer_at": None, "created_at": applied, "last_seen": applied}
        for i, (status, applied) in enumerate(
            [("applied", "2026-09-14T00:00:00+00:00"), ("saved", "2026-09-04T00:00:00+00:00"),
             ("rejected", "2026-09-24T00:00:00+00:00"), ("offer", "2026-09-24T00:00:00+00:00"),
             ("interview", "2026-10-02T00:00:00+00:00")], start=1)
    ]


# --------------------------------------------------------------------------- the cases


def test_the_engine_declares_the_positions_the_board_and_backend_validate():
    """Case 1: one vocabulary, four spellings, in the order the product teaches it."""
    stages = engine_stages()
    assert len(stages) == len(set(stages)) == POSITIONS, (
        f"analytics.py STAGES is {stages}: the mix is drawn over these keys, so a duplicate "
        "double-counts a position and a loss hides rows")
    assert stages == BOARD_ORDER, (
        f"analytics.py STAGES order is {stages}, not the board order {BOARD_ORDER}: the digest "
        "emits keys in this order and the chart draws them in that order")
    assert board_stages() == BOARD_ORDER, (
        f"pipeline.ts APPLICATION_STAGES says {board_stages()}: the board columns and the "
        "engine's distribution order have to be the same list or the card reads out of order")
    assert status_union() == BOARD_ORDER, (
        f"types.ts ApplicationStatus says {status_union()}: a status the type cannot hold is a "
        "row the frontend casts away before the chart ever sees it")

    declared = backend_statuses()
    assert declared == set(BOARD_ORDER), (
        f"ApplicationService.STATUSES is {sorted(declared)} against the {POSITIONS} positions "
        "the mix is built over: a status the backend validates and the engine does not list is "
        "a row counted under its raw spelling, and one the engine lists and the backend "
        "rejects is a position no application can ever sit at")


def test_the_pipeline_is_a_run_through_the_positions_not_a_substitute_for_them():
    """Case 2: the funnel's five stages are a slice of the seven positions, on purpose.

    ``saved`` and ``rejected`` are positions a candidate is at but never *reaches* on the way to
    an offer, which is why the funnel reports them beside its rows instead of among them. The
    mix needs all seven. Pinning the two lists apart is what stops either shape being "fixed" by
    editing the wrong one.
    """
    stages, pipeline = engine_stages(), engine_pipeline()
    assert len(pipeline) == 5 and set(pipeline) < set(stages), (
        f"PIPELINE {pipeline} is not a proper subset of STAGES {stages}")
    assert [s for s in stages if s not in pipeline] == ["saved", "rejected"], (
        "the positions outside the funnel are exactly the two it reports beside its rows; "
        f"now they are {[s for s in stages if s not in pipeline]}")


def test_the_digest_counts_each_application_once_and_the_funnel_still_does_not():
    """Case 3: the distribution adds up, the funnel does not, on the same five rows.

    Seven counts for five applications is the bug; ten for the funnel is correct. A chart may
    divide by the first total and never by the second.
    """
    from datetime import datetime, timezone

    from app.features import analytics as A

    now = datetime(2026, 10, 14, tzinfo=timezone.utc)
    rows = _rows()
    digest = A.insight_digest(rows, now=now, stale_days=14)
    mix, funnel = digest["stageCounts"], A.pipeline_funnel(rows)

    assert sum(mix.values()) == digest["totalApplications"] == len(rows), (
        f"stageCounts sums to {sum(mix.values())} over {len(rows)} applications "
        f"(totalApplications={digest['totalApplications']}): ShareChart divides each bar by "
        "this sum, so a total inflated by double counting shrinks every share on the card")
    assert mix == {"applied": 1, "saved": 1, "rejected": 1, "interview": 1, "offer": 1}
    assert set(mix) <= set(engine_stages()), (
        f"stageCounts carries {sorted(set(mix) - set(engine_stages()))}: a key outside the "
        "board's positions is a chart row no label or colour rule knows")

    reached = {s["stage"]: s["count"] for s in funnel["pipeline"]}
    assert sum(reached.values()) > len(rows), (
        f"the funnel's reached-counts sum to {sum(reached.values())} over {len(rows)} "
        "applications: reached semantics are cumulative, so flattening them would rewrite 15.1 "
        "and make the leak chart agree with the mix by both being wrong")
    assert reached["applied"] == 4 and reached["offer"] == 1, (
        f"reached counts are {reached}: the offer and interview rows also passed applied, "
        "and the rejected row is credited there -- that is the funnel's claim, unchanged")
    assert mix["applied"] == 1, (
        f"the mix says {mix['applied']} applications are at applied; the funnel says "
        f"{reached['applied']} passed through it. Two answers to two questions -- the card "
        "title picks which one the number belongs to")


def test_the_mix_function_the_digest_calls_never_looks_at_the_funnel():
    """Case 4: the return expression is a row counter, not a projection of the funnel's rows.

    The defect lived here: ``stageCounts`` was built as ``{s["stage"]: s["count"] for s in
    funnel["pipeline"]}``, which reads a distribution off a shape that counts a row once per
    stage reached. Pinning the syntax is what makes the revert a red test rather than a review
    comment -- the numbers only disagree once there are applications to count, and a gate that
    waits for that is a gate that trusts the fixture.
    """
    from datetime import datetime, timezone

    from app.features import analytics as A

    tree = _analytics_tree()
    digest = next((n for n in tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "insight_digest"), None)
    assert digest, "analytics.py no longer defines insight_digest"

    pairs = {node.keys[i].value: node.values[i]
             for node in ast.walk(digest) if isinstance(node, ast.Dict)
             for i in range(len(node.keys))
             if isinstance(node.keys[i], ast.Constant) and isinstance(node.keys[i].value, str)}
    assert "stageCounts" in pairs, "the digest no longer returns a stageCounts key"
    value = pairs["stageCounts"]
    assert isinstance(value, ast.Call), (
        f"stageCounts is built from {type(value).__name__} ({ast.unparse(value)}), not from a "
        "call: an inline projection over funnel['pipeline'] is exactly how #250 shipped")

    called = ast.unparse(value.func)
    helper = next((n for n in tree.body if isinstance(n, ast.FunctionDef)
                   and n.name == called), None)
    assert helper, f"stageCounts calls {called}(), which is not a module-level function"
    # The prose is excluded: #249 found a gate reading a sentence about a token as a use of it,
    # and this file's own first run just tripped the same way on "the funnel answers…" in the
    # helper's docstring. The claim is about the code the interpreter runs.
    statements = helper.body[1:] if (
        helper.body and isinstance(helper.body[0], ast.Expr)
        and isinstance(helper.body[0].value, ast.Constant)) else helper.body
    body = "\n".join(ast.unparse(statement) for statement in statements)
    assert "funnel" not in body, (
        f"{called}() reads the funnel, so its counts are reached-counts again: {body[:200]!r}")
    loops = [n for n in statements if isinstance(n, ast.For)]
    assert len(loops) == 1, (
        f"{called}() walks the rows {len(loops)} times: a distribution counts each row in one "
        "pass, and a second pass is where a row starts being counted twice")
    increments = [n for node in statements for n in ast.walk(node) if isinstance(n, ast.AugAssign)] + \
                 [n for node in statements for n in ast.walk(node)
                  if isinstance(n, ast.Assign) and "get(" in ast.unparse(n.value)
                  and "+ 1" in ast.unparse(n.value)]
    assert increments, (
        f"{called}() never adds one per row, so it is not counting a distribution: "
        f"{body[:200]!r}")

    # and the shape the engine hands the chart is the shape the chart is typed for
    digest_out = A.insight_digest(_rows(), now=datetime(2026, 10, 14, tzinfo=timezone.utc))
    assert isinstance(digest_out["stageCounts"], dict), (
        "stageCounts is not a mapping: the page maps Object.entries over it")


def test_a_row_whose_status_is_not_a_known_position_is_still_counted():
    """Case 5: no application vanishes from a distribution the chart normalises by.

    ``withdrawn`` is a status the backend's own transition rules can produce, and a row can
    arrive with no status at all. Dropping either would make the remaining shares add up to one
    while the card claims to show where the applications are -- a quieter version of #250, and
    just as invisible from the bar widths alone.
    """
    from datetime import datetime, timezone

    from app.features import analytics as A

    rows = [dict(r, status=s) for r, s in zip(_rows(), ["applied", "saved", "withdrawn",
                                                        "offer", ""])]
    digest = A.insight_digest(rows, now=datetime(2026, 10, 14, tzinfo=timezone.utc))
    mix = digest["stageCounts"]

    assert sum(mix.values()) == len(rows) == digest["totalApplications"], (
        f"{sorted(mix)} adds up to {sum(mix.values())} for {len(rows)} rows: a status the "
        "engine does not list still belongs to an application the reader is counting")
    assert "withdrawn" in mix and "" not in mix, (
        f"an unknown spelling or a blank status is missing or blank-keyed in {mix}")


def test_the_page_draws_the_mix_into_the_share_chart_and_the_funnel_into_the_bars():
    """Case 6: the component that divides by its own total is fed the data that adds up.

    ``ShareChart`` computes ``total = data.reduce(...)`` and prints each row as a share of it.
    The funnel belongs in ``BarChart``, whose copy says "a share of the applications that were
    submitted" and is fed the funnel's own conversion field, not a division by the sum.
    """
    text = read(PAGE)
    shares = jsx_element(text, "ShareChart")
    assert shares, "the analysis page no longer draws a ShareChart -- re-aim this case"

    fed = [prop_expression(el, "data") for el in shares]
    assert any("stageCounts" in expr for expr in fed), (
        f"no ShareChart on the page is fed the digest's stageCounts ({fed}): the card is left "
        "with a chart whose rows are whatever else the page happens to have")
    assert not any("pipeline" in expr for expr in fed), (
        f"a ShareChart is fed the funnel's pipeline ({fed}): reached-counts divided by their "
        "own sum draw every stage as a fraction of a total that double counts")

    bars = [prop_expression(el, "data") for el in jsx_element(text, "BarChart")]
    assert any("pipeline" in expr for expr in bars), (
        f"no BarChart is fed funnel.pipeline ({bars}): the leak chart and the mix chart are "
        "one chart until the funnel loses its own card")


def test_the_colours_the_page_keys_on_are_positions_the_engine_can_emit():
    """Case 7: a colour branch on a stage name is dead code until the data can produce it.

    Before #250 the mix could never contain ``rejected``, so the card's ``stage === "rejected"``
    branch coloured nothing while the funnel's own ``final_round`` branch was live. A literal
    compared against a value the feed can never carry is a rule that reads as covered and is not.
    """
    text = read(PAGE)
    shares = [prop_expression(el, "data") for el in jsx_element(text, "ShareChart")]
    assert shares, "the page no longer builds ShareChart data"

    keyed = sorted({m.group(1) for expr in shares for m in
                    re.finditer(r'stage\s*===\s*"([a-z_]+)"', expr)})
    assert keyed, (
        "the stage-mix data expression no longer compares ``stage`` against a literal, so the "
        "card colours every position alike -- re-aim this case at whatever replaced the ternary")
    unknown = sorted(set(keyed) - set(engine_stages()))
    assert not unknown, (
        f"the page colours {unknown}, which the engine's mix never emits ({engine_stages()}): "
        "a dead branch beside a live one looks like coverage in a screenshot")
    assert "rejected" in keyed, (
        f"the card colours {keyed} but not ``rejected``: the position most applications end at "
        "reads in the same colour as the ones still in play")


def test_the_doc_row_that_promises_a_distribution_does_not_promise_a_funnel():
    """Case 8: docs/API.md's two rows hold their own semantics, in both directions.

    The digest row used to advertise "the live stage mix" and then excuse reached-counts in the
    same sentence, citing "the honest bound of a schema that stores just the current status" -- a
    premise #249 ended, since the bridge reads the status-change log for the durations. The row is
    graded on three promises now: each application counted once, the counts adding up, and the
    cumulative counts sent to the funnel row. The old excuse is forbidden by its own wording, so a
    re-aim of this case cannot keep it by paraphrasing.
    """
    digest = doc_row("/analysis/insight-digest")
    funnel = doc_row("/analysis/pipeline-funnel")

    assert re.search(r"counted once", digest), (
        f"the digest row no longer says each application is counted once: {digest[:220]!r}")
    assert re.search(r"add up to", digest), (
        f"the digest row no longer says the mix adds up to the total, which is the one "
        f"property a share chart may be drawn from: {digest[:220]!r}")
    assert re.search(r"cumulative[^.]*pipeline-funnel|pipeline-funnel[^.]*cumulative",
                     digest, re.I), (
        f"the digest row names neither cumulative counts nor the funnel row they belong to: "
        f"{digest[:220]!r} -- a reader of this row alone cannot tell the two shapes apart")
    assert "honest bound of a schema" not in read(DOC), (
        "docs/API.md re-carries the excuse that the schema stores only the current status; #249 "
        "made the bridge read the status-change log, so the sentence is false wherever it sits")
    assert "cumulative" in funnel and "do not add up" in funnel, (
        f"the funnel row must keep claiming cumulative reached-counts that do not add up: "
        f"{funnel[:220]!r}")


def test_the_stub_that_hands_the_shape_out_hands_out_a_distribution():
    """Case 9: the backend's fake ai-service answers with the shape the engine answers.

    ``FakeAiServiceClientConfig`` is what the bridge's integration surface serves, so a stub that
    returns a funnel-shaped mix lets the chart pass against data the product never produces --
    which is how the same bug survived on both sides of the wire.
    """
    text = collapse(read(FAKE))
    digest = re.search(r"insightDigest\(UUID userId[^{]*\{.*?return map\((.*?)\);", text, re.S)
    assert digest, (
        "the fake ai-service no longer builds the digest from a map(...) literal -- re-aim this "
        "case at whatever answers insightDigest")
    body = digest.group(1)

    total = re.search(r'"totalApplications",\s*(\d+)', body)
    mix = re.search(r'"stageCounts",\s*map\(([^)]*)\)', body)
    assert total and mix, (
        "the fake digest no longer declares a numeric totalApplications beside a stageCounts "
        f"map literal (total={total and total.group(1)}, stageCounts={bool(mix)})")

    pairs = re.findall(r'"([a-z_]+)",\s*(\d+)', mix.group(1))
    assert pairs, f"the fake's stageCounts reads empty: {mix.group(1)!r}"
    counts = {k: int(v) for k, v in pairs}
    assert sum(counts.values()) == int(total.group(1)), (
        f"the fake's stageCounts sums to {sum(counts.values())} against totalApplications "
        f"{total.group(1)}: the page divides these by their own sum, so a stub that does not "
        "add up trains the chart on the shape it must reject")
    stray = sorted(set(counts) - set(engine_stages()))
    assert not stray, f"the fake emits positions the engine has none of: {stray}"
    zeroed = sorted(k for k, v in counts.items() if v == 0)
    assert not zeroed, (
        f"the fake lists {zeroed} with a count of zero: the engine only reports positions an "
        "application is actually at, and a stub padded with the funnel's stage rows is the "
        "old shape wearing new keys")
