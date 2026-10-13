"""The pasted-posting floor: one declaration on the client, and above the bound the API declares.

A job posting is the one piece of user text the app sends to three different AI-service requests,
and each of those carries its own bound: `JdReq.raw_text` on `POST /jd/analyze`, `SuggestReq.jd_raw`
on `POST /jd/suggestions`, `ParseReq.text` on `POST /resume/parse`. All three say
`Field(min_length=20)`. The screens that fill them said `40` -- four times, in two files, as a bare
literal in a guard and again in a `disabled` expression. Nothing connected the two numbers.

That is the shape #214 and #215 closed for the auth records: a client floor and a server bound that
agree by accident, with no site that notices when they stop agreeing. The accident is load-bearing
here, because the client floor is deliberately *higher* than the server's. Twenty characters clears
the API's sanity check and is too short to analyse into anything a user can act on, and the refusal
below it is a 422 whose text no screen renders well -- so a screen that dropped to the server's
number would start sending postings the analyst answers with noise. The floor therefore has one
home, `frontend/src/lib/jd-text.ts`, and the relationship to the server's bound is read from the
server's own file rather than typed in here.

The server's bound had no witness at all: no test in this repository built one of those three models
with a short value, so nothing proved `min_length` was really 20 rather than absent. The second case
asks the models themselves -- nineteen characters raise, twenty pass -- which is also what makes the
comparison in the fifth case mean something: the number on the client is held above a number that is
shown to bite.

The walk that finds those bounds reads a SHAPE -- a plain `str` field carrying `Field(min_length=...)`
on a model some `@router.post` handler takes -- and a shape cannot say whether the field holds a
pasted posting. When Epic 10.1 added `GapReq.target_role` (`min_length=10`, one role name typed into
one box) the same walk admitted it, and the floor was suddenly compared against a fourth feature that
never sees a paste. So the walk stays the population and the judgement moves to two ledgers keyed by
(model, field, route): which bounded fields carry the posting, and which bound a str for some other
reason. A fourth paste, or a new bounded str anywhere on a POST body, has to be admitted to one of
them before anything else in this file gets to answer.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[1]

FEATURES = "ai-service/app/api/features.py"
MODULE = "frontend/src/lib/jd-text.ts"
MODULE_TEST = "frontend/src/lib/jd-text.test.ts"
ANALYZE = "frontend/src/components/jobs/analyze-jd-dialog.tsx"
IMPORT = "frontend/src/components/jobs/import-job-dialog.tsx"
MODULE_IMPORT = "@/lib/jd-text"
CLIENT_FLOOR = 40

# An import statement, not the specifier anywhere in the file: both dialogs name `@/lib/jd-text` in
# prose, and a comment is not a caller. The braces may span lines, as every other multi-name import
# in these two files does.
HELPER_IMPORT = re.compile(r'^import\s+(?:type\s+)?\{[^{}]*\bjdTextIssue\b[^{}]*\}\s+from\s+"'
                           + re.escape(MODULE_IMPORT) + r'"', re.M | re.S)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def asks_the_helper(text: str) -> bool:
    return HELPER_IMPORT.search(text) is not None


def strip_comments(text: str) -> str:
    r"""The module's code with its `//` and block comments gone.

    The docstring legitimately names the API's own bound while code may not, so the literal census
    below reads the comment-free text. Block comments are anchored at the start of a line, which is
    how this module writes them; a trailing `//` beside a statement would survive, and the module
    has no such line to lose.
    """
    text = re.sub(r"(?m)^\s*//[^\n]*$", "", text)
    return re.sub(r"(?ms)^\s*/\*.*?\*/", "", text)


# ------------------------------------------------- the server's own bound


@lru_cache(maxsize=1)
def walked_bounds() -> dict[tuple[str, str, str], int]:
    """Every `min_length` on a plain `str` field of a POST request model, keyed by where it is bound.

    Admission is structural, not by name: the class must be the request parameter of a `@router.post`
    handler, and the field must be a plain `str` with a `Field(min_length=...)` on it -- an optional
    id or a count never joins, whatever it is called. The walk therefore cannot tell a paste from
    any other bounded sentence, which is what the two ledgers below are for.
    """
    text = read(FEATURES)
    models: dict[str, list[tuple[str, int]]] = {}
    for m in re.finditer(r"^class (\w+)\(BaseModel\):\n((?:(?:    .*\n|\n)+))", text, re.M):
        name, body = m.group(1), m.group(2)
        for field in re.finditer(r"^    (\w+): str = Field\(min_length=(\d+)\)", body, re.M):
            models.setdefault(name, []).append((field.group(1), int(field.group(2))))
    out: dict[tuple[str, str, str], int] = {}
    for m in re.finditer(r'@router\.post\("([^"]+)"\)\nasync def \w+\(req: (\w+)', text):
        route, cls = m.group(1), m.group(2)
        for field, bound in models.get(cls, []):
            out[(cls, field, route)] = bound
    return out


# The three bounds the client floor is held above, each stated as the (model, field, route) the walk
# has to find. The sentence is why it is a paste, so a row cannot be kept as a placeholder.
PASTED_TEXT_FIELDS: dict[tuple[str, str, str], str] = {
    ("JdReq", "raw_text", "/jd/analyze"): "the posting a candidate pastes into the analyse dialog",
    ("SuggestReq", "jd_raw", "/jd/suggestions"): "that same paste, re-sent for resume suggestions",
    ("ParseReq", "text", "/resume/parse"): "that same paste, handed to the parser as the posting",
}

# Bounded `str` fields the walk finds that hold no paste. Being here costs a reason: the walk will
# keep admitting this shape, and a row that stops describing a field the walk still finds goes stale.
# The growth/salary/negotiate/outreach/readiness/progress/compare-offers family joined with Epic 10.x:
# each bounds a role or a person's name typed into one box, at 1-10 characters, never a posting.
# The Epic 10.10-10.12 and 4.8 waves extended the same shape: every new analysis endpoint takes a
# role or company name in one box (min_length 2 or 10), and the interview-prep wave's prep endpoint
# takes the target role the session drills toward.
BOUNDED_NOT_PASTED: dict[tuple[str, str, str], str] = {
    ("GapReq", "target_role", "/gap-analysis"): "one role name typed into one box, never a paste",
    ("SalaryReq", "role", "/salary-benchmark"): "one role name, the salary question's subject",
    ("NegotiateReq", "role", "/negotiate"): "one role name, the negotiation's subject",
    ("ReadinessReq", "target_role", "/readiness"): "one role name, the readiness question's subject",
    ("LearningReq", "target_role", "/learning-plan"): "one role name, the plan's target",
    ("CompareOffersReq", "role", "/compare-offers"): "one role name, the comparison's subject",
    ("OutreachReq", "name", "/outreach"): "one person's name for the outreach draft's greeting",
    ("ProgressReq", "target_role", "/progress"): "one role name, the progress question's subject",
    ("GrowthReportReq", "target_role", "/growth-report"): "one role name, the report's subject",
    ("CounterOfferReq", "role", "/counter-offer"): "one role name, the counter-offer's subject",
    ("SkillDemandReq", "role", "/skill-demand"): "one role name, the demand question's subject",
    ("CompanyBriefReq", "company", "/company-brief"): "one company name, the brief's subject",
    ("ProgressionReq", "aspirational_role", "/progression"): "one role name, the stepping-stone plan's target",
    ("LearningPriorityReq", "target_role", "/learning-priority"): "one role name, the priority ranking's subject",
    ("InterviewPrepReq", "target_role", "/interview-prep"): "one role name, the prep session's target",
}


def test_the_walked_bounds_are_split_by_the_two_ledgers() -> None:
    """Nothing bounded gets to be unexplained, and no ledger row gets to describe a field gone.

    Both directions matter: the first is what makes a fourth feature join the conversation instead of
    silently moving the number the floor is compared against, and the second is what stops a ledger
    from keeping a row the API no longer binds -- a paste nobody sends would still be held above.
    """
    walked = set(walked_bounds())
    both = sorted(set(PASTED_TEXT_FIELDS) & set(BOUNDED_NOT_PASTED))
    assert not both, (
        f"{both} is ledgered as a paste and as not-a-paste at once, so the union below cannot say which "
        "the floor answers to")
    explained = set(PASTED_TEXT_FIELDS) | set(BOUNDED_NOT_PASTED)
    assert not walked - explained, (
        f"{FEATURES} bounds a str field no ledger row explains: {sorted(walked - explained)} -- either "
        "it carries a paste, and the floor has to stay above it, or it does not, and saying why is the "
        "only thing that keeps this file's `20` about the posting")
    assert not explained - walked, (
        f"a ledger row names a bound the walk no longer finds: {sorted(explained - walked)} -- the field "
        "was renamed, unbounded, or its route stopped taking that model, and a stale row is a claim "
        "about a paste the API never asked for")
    for row, reason in list(PASTED_TEXT_FIELDS.items()) + list(BOUNDED_NOT_PASTED.items()):
        assert reason.strip(), f"{row} is ledgered with an empty reason, which explains nothing"


def test_three_requests_bound_their_pasted_text_at_twenty() -> None:
    """The API's own file is where the number the screens stay above comes from."""
    bounds = walked_bounds()
    unfound = sorted(row for row in PASTED_TEXT_FIELDS if row not in bounds)
    assert not unfound, (
        f"the pasted-text ledger's rows are not in the walked bounds: {unfound} -- the case above says "
        "which moved, this one refuses to hold a floor above a bound it cannot find")
    assert len(PASTED_TEXT_FIELDS) == 3, (
        f"the pasted-text ledger has {len(PASTED_TEXT_FIELDS)} rows, not the three requests one posting "
        "text feeds: a fourth paste is a new screen's decision, and this file's `40` has to answer to "
        "it on purpose rather than because a shape walk included it")
    assert {row[1]: bounds[row] for row in PASTED_TEXT_FIELDS} == {"raw_text": 20, "jd_raw": 20,
                                                                   "text": 20}, (
        f"the three pastes no longer bound at these field names and numbers: "
        f"{ {row[1]: bounds[row] for row in PASTED_TEXT_FIELDS} } -- the client floor is compared "
        "against them, so a bound that moved alone is a screen that starts sending what the API "
        "refuses")


def test_the_servers_bound_actually_bites_at_nineteen_characters() -> None:
    """Nineteen raises, twenty does not -- the bound's first witness in this repository.

    Every bound the walk finds is asked, pasted or not, because the question is the same for all of
    them: does the `min_length` this file compares numbers against actually refuse what it claims to.
    The models are looked up by the names the walk found, not a second hard-coded list: a rename
    belongs to the reconciliation case, and a name list here would hold the same claim twice.

    A model whose request carries other required fields (`CompareOffersReq` needs its `offers`
    list) is filled minimally -- one type-appropriate value per other required field -- so the
    only thing varying between the nineteen- and twenty-character attempts is the field under
    test. A filler that stops satisfying a future constraint fails loudly here, the same way a
    ledger row does.
    """
    import pydantic

    from app.api import features

    def fill(model) -> dict:
        """Minimal kwargs satisfying every required field, so only the tested field varies."""
        kwargs = {}
        for name, info in model.model_fields.items():
            if not info.is_required():
                continue
            ann = info.annotation
            origin = getattr(ann, "__origin__", None)
            if origin in (list, tuple):
                args = getattr(ann, "__args__", ())
                item = args[0] if args else str
                kwargs[name] = [fill(item) if isinstance(item, type)
                                and issubclass(item, pydantic.BaseModel) else "x"]
            elif isinstance(ann, type) and issubclass(ann, pydantic.BaseModel):
                kwargs[name] = fill(ann)
            elif ann is int or ann is float:
                kwargs[name] = 1
            elif ann is bool:
                kwargs[name] = True
            else:
                kwargs[name] = "x"
        return kwargs

    bounds = walked_bounds()
    assert bounds, (
        f"the walk of {FEATURES} found no bounded `str` field at all, so looping over it proves only "
        "that an empty set has no counterexamples -- a narrowed walk is a red, not a pass")
    for (cls, field, route), bound in sorted(bounds.items()):
        model = getattr(features, cls)
        base = fill(model)
        try:
            model(**{**base, field: "x" * (bound - 1)})
            refused = False
        except pydantic.ValidationError:
            refused = True
        assert refused, (f"{cls}.{field} on {route} accepted {bound - 1} characters: min_length does not "
                         f"bite, so the client floor is held above a bound that never fires")
        try:
            model(**{**base, field: "x" * bound})
        except pydantic.ValidationError as exc:
            raise AssertionError(f"{cls}.{field} on {route} refused its own declared bound "
                                 f"({bound} characters): {exc}") from exc


# ------------------------------------------------- the client's one declaration


def test_the_client_declares_its_floor_once_and_uses_it_by_name() -> None:
    """`JD_TEXT_MIN_CHARS` is the only place the client writes the number, and the helper reads it."""
    module = read(MODULE)
    declared = re.findall(r"^export const JD_TEXT_MIN_CHARS = (\d+);$", module, re.M)
    assert declared == [str(CLIENT_FLOOR)], (
        f"the client floor is declared as {declared}: exactly one `export const JD_TEXT_MIN_CHARS = "
        f"{CLIENT_FLOOR};` is expected, and a second spelling means two floors")
    body = module[module.index("export function jdTextIssue"):][:
        module[module.index("export function jdTextIssue"):].index("\n}")]
    assert "value.trim().length < JD_TEXT_MIN_CHARS" in body, \
        f"jdTextIssue no longer judges the trimmed length against the declared constant:\n{body}"
    assert not re.search(r"\d", body), (
        f"jdTextIssue carries a digit of its own, so the exported constant is not the only floor it "
        f"speaks:\n{body}")
    assert "${JD_TEXT_MIN_CHARS}" in body, (
        f"the sentence no longer interpolates the constant, so a changed floor would print an old "
        f"number on screen:\n{body}")
    literals = re.findall(r"\d+", strip_comments(module))
    assert literals == [str(CLIENT_FLOOR)], (
        f"the module's code carries a second number besides its own floor (it spells {literals}): a "
        "literal in this module that is not the declared floor is a floor someone can change alone")


def test_no_screen_keeps_a_posting_floor_of_its_own() -> None:
    """The two screens that paste postings ask the helper; neither spells a length comparison."""
    for rel in (ANALYZE, IMPORT):
        text = read(rel)
        assert asks_the_helper(text), (
            f"{rel} no longer takes its floor from {MODULE}: a screen holding its own number is the "
            "drift this file exists to stop")
        assert not re.search(r"length < \d+", text), \
            f"{rel} spells a length floor again beside the helper's own: two numbers, one rule"
        assert "const issue = jdTextIssue(text);" in text, \
            f"{rel} stopped computing the issue once for both its guard and its button"
        assert "if (issue) return;" in text, \
            f"{rel}'s run() no longer defers to the shared issue, so the guard and the button can disagree"
        assert "disabled={issue !== undefined}" in text, \
            f"{rel}'s primary button no longer disables on the shared issue"


def test_the_client_floor_stays_above_the_apis_own_bound() -> None:
    """The relationship, read from both sides: the screens send only what every route accepts."""
    module = read(MODULE)
    declared = int(re.search(r"^export const JD_TEXT_MIN_CHARS = (\d+);$", module, re.M).group(1))
    bounds = walked_bounds()
    assert PASTED_TEXT_FIELDS, (
        "the pasted-text ledger is empty, so there is no bound left for the floor to sit above: the "
        f"client still declares {declared} while nothing in {FEATURES} is asked to agree with it")
    unfound = sorted(row for row in PASTED_TEXT_FIELDS if row not in bounds)
    assert not unfound, (
        f"the floor cannot be held above bounds the walk does not find: {unfound} -- comparing against "
        "the bounds that ARE still walked would let the paste that left be the one that mattered")
    highest = max(bounds[row] for row in PASTED_TEXT_FIELDS)
    assert declared > highest, (
        f"the client floor ({declared}) is no longer above the API's own bound ({highest}): at or below "
        "it, a paste the UI invites reaches the analyst with text too short to parse into anything "
        "usable, and the refusal is a 422 no screen explains")
    doc = module[:module.index("export const JD_TEXT_MIN_CHARS")]
    for route in sorted(row[2] for row in PASTED_TEXT_FIELDS):
        # A boundary, not a substring: `/jd/suggest` is inside `/jd/suggestions`, so a route that lost
        # its tail would still be "named" by a plain `in` test.
        assert re.search(re.escape(route) + r"(?![\w-])", doc), (
            f"the module's stated reason no longer names {route} as a whole route, one of the bounds it "
            "stays above")


def test_the_floors_sentence_has_a_reader_on_both_screens() -> None:
    """A message no screen renders is a dead string: both hints print the issue when there is one."""
    for rel, tail in ((ANALYZE, "nothing is sent until you run the analysis."),
                      (IMPORT, "nothing is sent until you import.")):
        text = read(rel)
        assert f'{{issue ?? "{tail}"}}' in text, (
            f"{rel} no longer falls back to {tail!r} when the paste clears the floor, so "
            "`jdTextIssue`'s sentence became a string nothing renders")


def test_the_helper_ships_with_a_test_that_reads_the_constant_it_checks() -> None:
    """The unit test ties its expectation to the declared floor, not to a number typed beside it."""
    test = read(MODULE_TEST)
    assert "JD_TEXT_MIN_CHARS" in test and "jdTextIssue" in test, \
        f"{MODULE_TEST} stopped naming both the constant and the function it is about"
    assert "${JD_TEXT_MIN_CHARS}" in test, (
        f"{MODULE_TEST} no longer interpolates the constant into its expected sentence, so its claim "
        "is a typed number rather than the one the module declares")
    assert not re.search(r"(?<![\w.$])40\b", test), (
        f"{MODULE_TEST} spells the floor as a bare 40 beside the constant: raise the floor in "
        f"{MODULE} and this test would still assert the old sentence")


def test_only_the_two_posting_screens_reach_for_the_floor() -> None:
    """The module's callers are exactly the two paste-a-posting dialogs -- one walk of the app.

    The census asks for an import statement, not the specifier anywhere in the file: both dialogs write
    `@/lib/jd-text` in prose as well, and a comment that outlives the import it describes would be a
    caller the app never reaches.
    """
    files = [p.relative_to(ROOT).as_posix() for p in (ROOT / "frontend" / "src").rglob("*.ts*")
             if not p.is_dir() and ".test." not in p.name]
    assert len(files) > 100, f"the client walk read {len(files)} files, so its silence proves nothing"
    unread = sorted(rel for rel in (ANALYZE, IMPORT) if rel not in set(files))
    assert not unread, (
        f"the walk does not even read the two screens it claims to census: {unread} -- a narrowed glob "
        "that drops a caller would otherwise make the list below look shorter by someone else's doing")
    importers = sorted(rel for rel in files if rel != MODULE and asks_the_helper(read(rel)))
    assert importers == [ANALYZE, IMPORT], (
        f"the floor now has a different set of callers ({importers}): every screen that blocks a short "
        "posting should ask the helper, and one that stopped should say why here")
