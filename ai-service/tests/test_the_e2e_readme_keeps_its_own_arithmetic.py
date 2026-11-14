"""e2e/README's expected count is arithmetic, not an aspiration.

`e2e/README.md` names the run result as `**66 passed**` plus a breakdown
in parentheses. Nothing ever checked that list against the specs it names:
on 2026-11-08 it said "4 locale" for a file that ships three tests, and
the bold number survived by accident because the drift was compensated
elsewhere in the sentence -- a doc whose arithmetic is wrong in one place
is wrong, whether or not the total happens to land.

This gate counts each spec file the way the reader would: every
`test(` call that is not a `.test(` regex method and not `test.describe`,
`test.skip`, `test.only`, `test.use` or a helper's name, measured with
`(?<![\\w.])test\\(`. It then asserts:

* every number in the parenthetical matches the file it names (aliases
  spelled out below, exactly as the README spells them);
* every `.spec.ts` under `e2e/tests/` is either named in the list or
  covered by the unnamed remainder clause ("and the pagination suite");
* the bold total equals the sum of the stated counts plus the unnamed
  files' counts -- so the doc cannot keep a true total with a false
  breakdown, nor a true breakdown with a false total;
* the walk finds at least ten spec files, so a README rewrite that
  drops every number reddens rather than going vacuous.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E2E_TESTS = ROOT / "e2e" / "tests"
README = ROOT / "e2e" / "README.md"

STRICTLY_A_TEST_CALL = re.compile(r"(?<![\w.])test\(")

# README label (normalized) -> spec file stem. Every spec file must appear
# either here or in the unnamed remainder; a new spec reddens this gate
# until the README counts it.
ALIASES = {
    "golden journey": "golden-journey",
    "routes": "routes",
    "memory": "memory",
    "locale": "locale",
    "forward surfaces": "forward-surfaces",
    "ingest surfaces": "ingest-surfaces",
    "activity trace": "activity-trace",
    "a11y keyboard": "a11y-keyboard",
    "title": "title",
    "redaction": "redaction",
    "command palette": "command-palette",
    "networking": "networking",
    "stored-jd rehydrate": "jd-rehydrate",
    "timeline": "timeline",
    "fleet observability": "fleet-observability",
    "gateway edge": "gateway-edge",
    "deadline mesh": "deadline-mesh",
    "pace heatmap": "pace-heatmap",
    "offer shelf": "offer-shelf",
}

UNNAMED_CLAUSE = "the pagination suite"


def _normalize(label: str) -> str:
    label = re.sub(r"\(.*?\)", "", label)          # "(71.3)" suffixes
    label = re.sub(r"^(and|the)\s+", "", label.strip(), flags=re.I)
    return re.sub(r"\s+", " ", label).lower()


def _counts() -> dict[str, int]:
    out = {}
    for path in sorted(E2E_TESTS.glob("*.spec.ts")):
        out[path.name[: -len(".spec.ts")]] = len(
            STRICTLY_A_TEST_CALL.findall(path.read_text(encoding="utf-8", errors="replace")))
    return out


def _stated() -> tuple[int, list[tuple[int, str]], bool]:
    """(bold total, [(stated count, normalized label)], whether an unnamed clause exists).

    The parenthetical may itself contain a parenthesised suffix -- "1 stored-JD
    rehydrate (71.3), and the pagination suite" -- so a naive first-')' split
    cuts the list inside the suffix. The list is instead matched up to the
    first ').' that closes it, which the suffix never produces.
    """
    text = README.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\*\*(\d+) passed\*\*\s*\((.*?)\)\.", text, re.S)
    assert m, "e2e/README.md no longer states the bold 'N passed' result and its breakdown"
    total = int(m.group(1))
    inner = m.group(2)
    stated = []
    unnamed_clause = bool(re.search(r"pagination\s+suite", inner))
    for piece in inner.split(","):
        mm = re.match(r"^\s*(\d+)\s+(.+?)\s*$", piece)
        if mm:
            stated.append((int(mm.group(1)), _normalize(mm.group(2))))
    return total, stated, unnamed_clause


def test_the_readme_names_every_spec_or_reaches_it_through_the_unnamed_clause():
    counts = _counts()
    assert len(counts) >= 10, "too few spec files found -- the walk narrowed"
    _, stated, unnamed = _stated()
    named = {ALIASES[label] for _, label in stated if label in ALIASES}
    unnamed_files = sorted(set(counts) - named)
    assert unnamed, (
        f"{unnamed_files}: the list no longer names its cover clause, so these "
        "spec files would silently stop being counted by the doc")


def test_each_stated_count_equals_the_spec_it_names():
    counts = _counts()
    _, stated, _ = _stated()
    assert stated, "no 'N label' pair parsed from the parenthetical -- the walk narrowed"
    for stated_count, label in stated:
        stem = ALIASES.get(label)
        assert stem is not None, (
            f"{label!r}: the README names a file no alias table knows -- "
            "update ALIASES or the README, never neither")
        assert counts[stem] == stated_count, (
            f"{label!r}: README says {stated_count}, {stem}.spec.ts ships {counts[stem]}")


def test_the_bold_total_is_the_sum_of_the_parts():
    counts = _counts()
    total, stated, unnamed = _stated()
    named = {ALIASES[label] for _, label in stated if label in ALIASES}
    stated_sum = sum(n for n, _ in stated)
    remainder = sum(counts[stem] for stem in set(counts) - named)
    assert total == stated_sum + remainder, (
        f"bold says {total}, parts say {stated_sum} + unnamed {remainder} = {stated_sum + remainder} "
        f"(unnamed files: {sorted(set(counts) - named)})")


def test_product_md_names_the_same_count():
    """PRODUCT.md records the live-stack verification result as NN/NN.

    That sentence is a claim about the same population the README counts:
    it drifts the same way. It is checked against the shipped specs, not
    against the README, so the two documents cannot drift apart either.
    """
    product = (ROOT / "docs" / "PRODUCT.md").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"golden-journey suite passes\s+(\d+)/(\d+)", product)
    assert m, "PRODUCT.md no longer records a Playwright golden-journey NN/NN result"
    passed, total = int(m.group(1)), int(m.group(2))
    shipped = sum(_counts().values())
    assert total == shipped, (
        f"PRODUCT.md says {total} cases in the suite, e2e/tests/ ships {shipped}")
    assert passed == total, (
        "PRODUCT.md says fewer passes than cases -- either the sentence is stale "
        "or the suite is red, and neither belongs in 'verified against the live stack'")
