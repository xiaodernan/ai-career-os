"""The native-query census in SECURITY.md is the census the backend actually has.

The security review's SQL-injection row is a promise with a number in it: "only four native
queries exist", each one parameterised, with the two interpolations the review names
(`${len(args)}` placeholder indices and an int limit) as the whole exception list. Numbers in
prose rot quietly -- the two digest repositories that replaced the copilot sidebar's and the
interview list's per-row reads (`ConversationDigestRepository`, `InterviewDigestRepository`)
each run two grouped native statements, and the row still said four while the backend served
five. A reader auditing the injection surface would have walked four files and missed two.
Six now, and this pass moved the pin and the row together rather than letting the row fall
behind a third time: 44.3's retention purge counts the chunk rows its document delete takes
with it, and `document_chunks` is the one user table with no backend entity -- ai-service
writes it and V1's cascade removes it -- so only a native count over the table can say how
much the window took.

Seven with 69.2's `UserNoteRepository`: `tags` is a Postgres `text[]`, so counting the notes
behind each tag is `unnest(tags)` grouped in SQL -- a shape JPQL cannot spell -- and 64.2's
membership filter (`= any(tags)`) needed native SQL for the same reason. Both bind every
value; the only literals are column and type names.

This gate walks the backend for the two ways a native statement appears -- `createNativeQuery`
and `nativeQuery = true` -- pins the exact set, and then reads the doc row back: the census is
only useful if the document that states it states the same one. It also checks the claim the
row makes about interpolation, because that is the part that would make a seventh query
dangerous rather than merely undocumented: no native statement may splice a value into its
SQL text (the known `${...}` placeholder indices and the int limit live in JobSearchRepository
and are named in the doc).
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
JAVA = ROOT / "backend" / "src" / "main" / "java"
DOC = ROOT / "docs" / "SECURITY.md"

NATIVE_QUERIES = {
    "JobSearchRepository.java",
    "SearchRepository.java",
    "DashboardRepository.java",
    "ConversationDigestRepository.java",
    "InterviewDigestRepository.java",
    # 44.3's chunk count: `document_chunks` has no backend entity -- ai-service writes it and the
    # database's cascade removes it -- so the only way to report how many rows the window took is
    # a native count over the table. Bound parameters, no spliced value, like the other five.
    "DocumentRepository.java",
    # 69.2's tag counts: `tags` is a Postgres `text[]`, so grouping per tag means `unnest(tags)`
    # over the array, which JPQL cannot express. 64.2's `findByTag` in the same class is the
    # membership test (`= any(tags)`); both bind every value, the only literals being the column
    # and the cast's `text` type name.
    "UserNoteRepository.java",
    # 80's relation counts: the chip row's own question is one native count over the table — the
    # registry's vocabulary and the rows behind it — because `Contact` is the entity and a group-by
    # over `relation` is the only shape `relations` asks. Bound parameter, no literal, like the
    # other seven.
    "ContactRepository.java",
}

# Where a value may be spliced into SQL text, and why each is not user data.
INTERPOLATIONS = {
    "JobSearchRepository.java": "placeholder indices (${len(args)}) and an int LIMIT, both derived from the server's own paging window",
}


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def native_query_files() -> set[str]:
    return {p.name for p in JAVA.rglob("*.java")
            if "createNativeQuery" in read(p) or "nativeQuery = true" in read(p)}


def test_the_backend_has_exactly_the_native_queries_the_review_names():
    found = native_query_files()
    assert found == NATIVE_QUERIES, (
        f"the backend's native-query surface changed: {sorted(found)} vs the pinned "
        f"{sorted(NATIVE_QUERIES)} -- a new native statement means SECURITY.md's "
        f"SQL-injection row and this pin both move, in the same change")


def test_the_security_doc_names_every_native_query_it_counts():
    row = next(line for line in read(DOC).splitlines()
               if line.startswith("| SQL injection"))
    for name in NATIVE_QUERIES:
        stem = name[: -len(".java")]
        assert stem in row, (
            f"SECURITY.md's SQL-injection row does not name {stem}, which runs native SQL -- "
            f"the row's count is a promise and the file list is what makes it checkable")


def test_no_native_statement_splices_a_value_into_its_sql():
    """The injection claim itself: text blocks bind parameters, they do not format them."""
    for name in sorted(native_query_files()):
        path = next(p for p in JAVA.rglob("*.java") if p.name == name)
        text = read(path)
        for match in re.finditer(r'\$\{[^}]*\}', text):
            assert name in INTERPOLATIONS, (
                f"{name} interpolates {match.group(0)} into SQL text and the review does not "
                f"name it as an exception")
        assert "String.format" not in text, f"{name} formats SQL text with String.format"
