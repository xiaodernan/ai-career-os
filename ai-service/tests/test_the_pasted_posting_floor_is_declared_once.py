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
def posting_bounds() -> dict[str, tuple[str, int, str]]:
    """Every `min_length` in features.py that guards a pasted-text field, with the route that binds it.

    Admission is structural, not by name: the class must be the request parameter of a `@router.post`
    handler, and the field must be a plain `str` with a `Field(min_length=...)` on it -- an optional
    id or a count never joins, whatever it is called.
    """
    text = read(FEATURES)
    models: dict[str, list[tuple[str, int]]] = {}
    for m in re.finditer(r"^class (\w+)\(BaseModel\):\n((?:(?:    .*\n|\n)+))", text, re.M):
        name, body = m.group(1), m.group(2)
        for field in re.finditer(r"^    (\w+): str = Field\(min_length=(\d+)\)", body, re.M):
            models.setdefault(name, []).append((field.group(1), int(field.group(2))))
    out: dict[str, tuple[str, int, str]] = {}
    for m in re.finditer(r'@router\.post\("([^"]+)"\)\nasync def \w+\(req: (\w+)', text):
        route, cls = m.group(1), m.group(2)
        for field, bound in models.get(cls, []):
            out[cls] = (field, bound, route)
    return out


def test_three_requests_bound_their_pasted_text_at_twenty() -> None:
    """The API's own file is where the number the screens stay above comes from."""
    bounds = posting_bounds()
    assert set(bounds) == {"JdReq", "SuggestReq", "ParseReq"}, \
        f"the pasted-text bounds are no longer these three request models: {sorted(bounds)}"
    assert [(bounds[c][0], bounds[c][1]) for c in ("JdReq", "SuggestReq", "ParseReq")] == \
        [("raw_text", 20), ("jd_raw", 20), ("text", 20)], \
        f"a bound or its field name moved, so the client floor is compared against a different number: {bounds}"
    assert [bounds[c][2] for c in ("JdReq", "SuggestReq", "ParseReq")] == \
        ["/jd/analyze", "/jd/suggestions", "/resume/parse"], \
        f"these three bounds are no longer held by these routes: {sorted(bounds[c][2] for c in bounds)}"


def test_the_servers_bound_actually_bites_at_nineteen_characters() -> None:
    """Nineteen raises, twenty does not -- the bound's first witness in this repository.

    The models are looked up by the name the census found, not imported by a second hard-coded list:
    a rename belongs to the case above, and a name list here would hold the same claim twice.
    """
    import pydantic

    from app.api import features

    for cls, (field, bound, route) in sorted(posting_bounds().items()):
        model = getattr(features, cls)
        try:
            model(**{field: "x" * (bound - 1)})
            refused = False
        except pydantic.ValidationError:
            refused = True
        assert refused, (f"{cls}.{field} on {route} accepted {bound - 1} characters: min_length does not "
                         f"bite, so the client floor is held above a bound that never fires")
        try:
            model(**{field: "x" * bound})
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
        f"literal in this module that is not the declared floor is a floor someone can change alone")
    literals = re.findall(r"\d+", strip_comments(module))
    assert literals == [str(CLIENT_FLOOR)], (
        f"the module's code carries a second number (literals found: {literals}): the floor is meant "
        "to be spelled once, in the declaration, and any other literal in it is a floor or a bound "
        "that nothing here reconciles")


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
    declared = int(re.search(r"^export const JD_TEXT_MIN_CHARS = (\d+);$", read(MODULE), re.M).group(1))
    highest = max(bound for _, bound, _ in posting_bounds().values())
    assert declared > highest, (
        f"the client floor ({declared}) is no longer above the API's own bound ({highest}): at or below "
        "it, a paste the UI invites reaches the analyst with text too short to parse into anything "
        "usable, and the refusal is a 422 no screen explains")
    doc = read(MODULE)[:read(MODULE).index("export const JD_TEXT_MIN_CHARS")]
    for route in sorted(r for _, _, r in posting_bounds().values()):
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
    importers = sorted(rel for rel in files if rel != MODULE and asks_the_helper(read(rel)))
    assert importers == [ANALYZE, IMPORT], (
        f"the floor now has a different set of callers ({importers}): every screen that blocks a short "
        "posting should ask the helper, and one that stopped should say why here")
