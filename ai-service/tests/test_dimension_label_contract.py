"""The interview rubric's dimensions, read across the two services that name them.

The evaluator grades an answer on eight dimensions, and it asks for them by
name: the prompt interpolates the list key by key (`", ".join(f'"{d}": 0.0-1.0' …)`),
so the list is literally what the model is told to answer with. The browser
draws a bar per dimension and has to name each one, and the names it uses
live in the browser's own table (`frontend/src/lib/dimensions.ts`).

Nothing held the two lists together, and the failure is quiet in the way
this product's failures usually are. A dimension the service adds and the
browser does not know is drawn with a raw column name -- "problem_solving"
-- in the middle of a report whose other seven bars read as words, and in
every language. A dimension the browser names and the service does not ask
for is a bar that can never be drawn, and the table is covering for
nothing.

So this reads both lists and holds them to the same set, and then holds
every name in the set to a label in *both* languages -- because a name
with an English fallback is a name the reader cannot change, which is the
one thing the whole locale table exists to prevent.
"""

from pathlib import Path
import re

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = REPO_ROOT / "frontend" / "src"

INTERVIEW_FEATURE = APP_ROOT / "features" / "interview.py"
DIMENSIONS_MODULE = FRONTEND / "lib" / "dimensions.ts"
TRANSLATIONS = FRONTEND / "lib" / "i18n" / "translations.ts"


def _service_dimensions() -> list[str]:
    """The dimensions the evaluator asks the model for."""
    source = INTERVIEW_FEATURE.read_text(encoding="utf-8")
    declared = re.search(r"^DIMENSIONS\s*=\s*\[([^\]]*)\]", source, re.M)
    if declared is None:
        raise AssertionError(
            "interview.py no longer declares DIMENSIONS as one bracketed list: the label "
            "table's other half would be checked against nothing"
        )
    return re.findall(r'"([^"]+)"', declared.group(1))


def _browser_dimensions() -> list[str]:
    """The dimensions the browser's table names."""
    source = DIMENSIONS_MODULE.read_text(encoding="utf-8")
    start = source.index("export const INTERVIEW_DIMENSIONS")
    block = source[start : source.index("];", start)]
    keys = re.findall(r'\{\s*key:\s*"([^"]+)"', block)
    if not keys:
        raise AssertionError(
            "lib/dimensions.ts no longer declares INTERVIEW_DIMENSIONS as one bracketed list: "
            "the label table's other half would be checked against nothing"
        )
    return keys


def _locale_labels() -> dict[str, set[str]]:
    """The interview dimension labels the locale table holds, per language.

    Read out of the table itself rather than restated here: a gate that
    keeps its own copy of the vocabulary is a gate that goes green the
    moment the two drift.

    Each half is bounded by the next one, so a language whose own half has
    no block cannot fall through to the other language's and pass on its
    contents.
    """
    source = TRANSLATIONS.read_text(encoding="utf-8")
    out: dict[str, set[str]] = {}
    for language, nxt in (("en", "zh"), ("zh", None)):
        half = source[source.index(f"  {language}: {{") :]
        if nxt is not None:
            half = half[: half.index(f"  {nxt}: {{")]
        # The dimensions block holds four vocabularies; the interview one
        # is the one these names live in. Reading the whole block would let
        # a criterion's label satisfy a dimension -- two different tables
        # that happen to share an indent.
        block = _block(half, r"^ {4}dimensions: \{")
        if block is None:
            out[language] = set()
            continue
        inner = _block(block, r"^ {6}interview: \{")
        if inner is None:
            out[language] = set()
            continue
        out[language] = set(re.findall(r"^ {8}(\w+):\s*\{\s*label:", inner, re.M))
    return out


def _block(text: str, opener: str) -> str | None:
    """The body of a block, from its opening line to the line that closes it.

    The indentation is the closing brace's: a block opened at four spaces
    closes at four. That is what tells one block's end from another's, and
    it is why the reader is a pattern and not a search for a comma.
    """
    match = re.search(opener, text, re.M)
    if match is None:
        return None
    indent = len(match.group(0)) - len(match.group(0).lstrip(" "))
    closer = re.compile(r"^ {%d}\}," % indent, re.M)
    end = closer.search(text, match.end())
    if end is None:
        return None
    return text[match.end() : end.start()]


def test_the_browser_names_exactly_the_dimensions_the_service_asks_for() -> None:
    service = _service_dimensions()
    browser = _browser_dimensions()
    assert service, "the service declared no dimension: the comparison below would pass on empty"
    assert browser, "the browser named no dimension: the comparison below would pass on empty"
    assert sorted(service) == sorted(browser), (
        "the evaluator's dimensions and the browser's label table have drifted apart: "
        f"the service asks for {sorted(service)}, the browser names {sorted(browser)}"
    )


def test_the_browser_does_not_name_a_dimension_twice() -> None:
    browser = _browser_dimensions()
    assert len(browser) == len(set(browser)), f"a dimension is named twice: {browser}"


def test_every_dimension_has_a_label_in_every_language() -> None:
    # A dimension with no label is drawn with a raw column name -- "problem
    # _solving" -- in the middle of a report whose other bars read as words.
    labels = _locale_labels()
    dimensions = set(_service_dimensions())
    for language, keys in labels.items():
        assert keys, f"the {language} table holds no dimension label: the rule below would pass on empty"
        missing = dimensions - keys
        assert missing == set(), (
            f"a dimension with no {language} label: {sorted(missing)} -- it would be drawn as a "
            "raw column name"
        )
