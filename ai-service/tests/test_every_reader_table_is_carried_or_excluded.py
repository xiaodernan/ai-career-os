"""Every table a migration creates is carried, excluded, or shared -- by name.

The bundle promises to be everything that is the reader's. The promise is
only as good as the table list it was measured against: `db/migration` is
where a new table lands, and a table on the wrong side of the boundary is a
reader's data that never travels -- or a credential that does. Epic 40
measured the boundary by hand (40.0) and carried every gap it found
(40.1-40.3); 40.4 makes the measurement a census.

The census reads the migrations, not a list: every `CREATE TABLE` body is
parsed for its columns and its foreign keys, and the reader-scoped closure
is computed -- every table with a `user_id`, the `users` root, and every
table reachable from those by a foreign key (`messages` through
`conversations`, `agent_traces` through `agent_runs`). Every table in that
closure must be either CARRIED (a table -> section map; a nested child
names its parent and rides the parent's section) or named in the exclusion
table in `docs/EXPORT.md` with a reason that starts `Rebuilt:` or
`Bookkeeping:`.

Three tables sit outside the closure -- `companies`, `jobs` and
`nightly_reports` -- because they are nobody's rows: the catalogue the
postings live in and the platform's own nightly run record. The exclusion
table lists them too, under `Shared:`, so "not the reader's" is a stated
decision rather than the default a table falls into by having no column.

The gate fails by name on a new table. That is the point: the next
migration that adds a reader-owned table, or a credential, must say which
it is before the suite goes green.

The second half of 40.4 is the one list. The manifest's counts, the
Markdown view and the print-ready HTML all walk `SECTIONS`; the browser
derives its redaction list from the manifest instead of typing one (held
in `test_export_bundle_contract.py`). The order gates here hold the three
server-side walks to the tuple.
"""

from pathlib import Path
import re

from app.features.export import SECTIONS, section_counts, to_markdown
from app.features.export_render import to_html
from app.features.export_words import section_titles

AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_SERVICE_ROOT.parent
MIGRATIONS = REPO_ROOT / "backend" / "src" / "main" / "resources" / "db" / "migration"
EXPORT_DOC = REPO_ROOT / "docs" / "EXPORT.md"

# The tables the bundle carries, and the section that carries each one. This
# is the decision the census exists to protect: every reader-scoped table is
# here, and every name here is a table the migrations actually create.
CARRIED: dict[str, str] = {
    # The AI half.
    "user_profiles": "profile",
    "resumes": "resumes",
    "resume_versions": "resumes",
    "documents": "knowledge",
    "job_jds": "job_descriptions",
    "interview_sessions": "interviews",
    "interview_turns": "interviews",
    "interview_evaluations": "interviews",
    "user_memories": "memories",
    # The backend half, in the order the sections grew.
    "applications": "applications",
    "growth_plans": "growth_plans",
    "user_notes": "notes",
    "contacts": "contacts",
    "conversations": "conversations",
    "messages": "conversations",
    "saved_searches": "saved_searches",
    "ingestion_feeds": "ingestion_feeds",
    "saved_jobs": "saved_jobs",
    "inbound_mails": "inbound_mails",
}

# A child table with no section of its own: its rows are embedded in the
# parent's row inside the bundle, so it must ride the parent's section.
NESTED: dict[str, str] = {
    "resume_versions": "resumes",
    "interview_turns": "interview_sessions",
    "interview_evaluations": "interview_sessions",
    "messages": "conversations",
}

_REASON_PREFIXES = ("Rebuilt:", "Bookkeeping:", "Shared:")

_CONSTRAINT_WORDS = {"CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "EXCLUDE"}


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def _sql(path: Path) -> str:
    """A migration with its `--` comments removed.

    The migrations explain themselves with SQL in their comments (V4 shows the
    `ALTER TABLE` it performs, V5 shows the columns it adds), and a commented
    `CREATE TABLE` is prose about a table, not a table. The census reads the
    statements, so the comments go first.
    """
    return "\n".join(line.split("--", 1)[0] for line in read(path).split("\n"))


def _body(text: str, start: int) -> str:
    """The parenthesised body that starts just past a `(`, to its matching `)`."""
    depth, i = 1, start
    while i < len(text) and depth:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
        i += 1
    return text[start:i - 1]


def _top_level_parts(body: str) -> list[str]:
    """The comma-separated parts of a table body, ignoring commas in defaults."""
    parts, buf, depth = [], [], 0
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def _columns(body: str) -> set[str]:
    """The column names a body declares, skipping table constraints."""
    columns: set[str] = set()
    for part in _top_level_parts(body):
        match = re.match(r"\s*([a-z_][a-z0-9_]*)\b", part, re.I)
        if match and match.group(1).upper() not in _CONSTRAINT_WORDS:
            columns.add(match.group(1).lower())
    return columns


def _references(body: str) -> set[str]:
    """The tables a body points at with `REFERENCES`."""
    return {
        match.lower()
        for match in re.findall(
            r"REFERENCES\s+(?:public\.)?([a-z_][a-z0-9_]*)", body, re.I
        )
    }


def migration_tables() -> dict[str, dict]:
    """Every table the migrations create: its columns and the tables it references.

    `ALTER TABLE ... ADD COLUMN user_id` and `ALTER TABLE ... REFERENCES` are
    folded in too: a table can gain its reader scope or its parent after the
    `CREATE`, and the census is about the schema the migrations end with, not
    the one they started from.
    """
    tables: dict[str, dict] = {}
    for path in sorted(MIGRATIONS.glob("*.sql")):
        text = _sql(path)
        for match in re.finditer(
            r"CREATE TABLE(?: IF NOT EXISTS)?\s+([a-z_][a-z0-9_]*)\s*\(",
            text,
            re.I,
        ):
            body = _body(text, match.end())
            tables[match.group(1).lower()] = {
                "columns": _columns(body),
                "references": _references(body),
            }
        for match in re.finditer(
            r"ALTER TABLE\s+(?:IF EXISTS\s+)?([a-z_][a-z0-9_]*)\s+(.*?);",
            text,
            re.S | re.I,
        ):
            table = tables.get(match.group(1).lower())
            if table is None:
                continue
            body = match.group(2)
            if re.search(r"ADD COLUMN(?: IF NOT EXISTS)?\s+user_id\b", body, re.I):
                table["columns"].add("user_id")
            table["references"] |= _references(body)
    return tables


def reader_closure(tables: dict[str, dict]) -> set[str]:
    """The tables whose rows are a reader's: `user_id`, the `users` root, FK reach."""
    scoped = {name for name, table in tables.items() if "user_id" in table["columns"]}
    scoped.add("users")
    while True:
        reachable = {
            name
            for name, table in tables.items()
            if name not in scoped and table["references"] & scoped
        }
        if not reachable:
            return scoped
        scoped |= reachable


def documented_rows() -> list[tuple[str, str]]:
    """The exclusion table's `(table, reason)` rows, in the order it lists them."""
    text = read(EXPORT_DOC)
    start = text.index("## What the bundle does not carry")
    end = text.index("\n## ", start + 3)
    rows: list[tuple[str, str]] = []
    for line in text[start:end].split("\n"):
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 2:
            rows.append((cells[0].strip("`").strip(), cells[1]))
    return rows


def _named(documented: dict[str, str], prefix: str) -> set[str]:
    return {table for table, reason in documented.items() if reason.startswith(prefix)}


def test_the_parser_reads_every_create_table_statement() -> None:
    # A parse that silently misses a table would make the census pass by
    # looking away. The count on both sides is the guard: every `CREATE TABLE`
    # in the migrations is a table the census classified.
    statements = sum(
        len(re.findall(r"CREATE TABLE", _sql(path), re.I))
        for path in MIGRATIONS.glob("*.sql")
    )
    assert len(migration_tables()) == statements, (
        f"{statements} CREATE TABLE statements in {MIGRATIONS}, "
        f"{len(migration_tables())} parsed"
    )


def test_every_reader_table_is_carried_or_excluded() -> None:
    tables = migration_tables()
    assert tables, f"no tables were read out of {MIGRATIONS}"
    closure = reader_closure(tables)

    rows = documented_rows()
    names = [name for name, _ in rows]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    assert not duplicates, f"the exclusion table names a table twice: {duplicates}"
    documented = dict(rows)

    unknown = sorted(set(documented) - set(tables))
    assert not unknown, (
        "the exclusion table names tables no migration creates: "
        f"{unknown} (read from {EXPORT_DOC})"
    )
    ghost = sorted(set(CARRIED) - set(tables))
    assert not ghost, f"the carried map names tables no migration creates: {ghost}"
    both = sorted(set(CARRIED) & set(documented))
    assert not both, (
        "a table is both carried and listed as excluded: "
        f"{both} -- the census does not allow a table to be half in the bundle"
    )

    excluded = _named(documented, "Bookkeeping:") | _named(documented, "Rebuilt:")
    shared = _named(documented, "Shared:")

    unclassified = sorted(closure - set(CARRIED) - excluded)
    assert not unclassified, (
        "reader-scoped tables are neither carried by a section nor listed in "
        f"the exclusion table in {EXPORT_DOC}: {unclassified}"
    )
    assert excluded == closure - set(CARRIED), (
        "the exclusion table's bookkeeping/rebuilt rows do not match the reader "
        f"tables the bundle leaves out: extra {sorted(excluded - (closure - set(CARRIED)))}, "
        f"missing {sorted((closure - set(CARRIED)) - excluded)}"
    )
    assert shared == set(tables) - closure, (
        "the shared rows do not match the tables the reader closure cannot "
        f"reach: extra {sorted(shared - (set(tables) - closure))}, "
        f"missing {sorted((set(tables) - closure) - shared)}"
    )


def test_every_section_is_fed_by_a_table() -> None:
    # The other direction: a section with no table behind it is a section the
    # census never measured, and a carried table of a section the bundle does
    # not name is a row the writer would have to invent a home for.
    assert set(CARRIED.values()) == set(SECTIONS), (
        f"carried sections {sorted(set(CARRIED.values()))} != bundle sections {sorted(SECTIONS)}"
    )


def test_a_nested_table_rides_its_parent_s_section() -> None:
    # `messages` has no section of its own -- it travels inside a conversation
    # -- so leaving it out of the parent's section would mean the census
    # counted a table whose rows never leave. The same holds for the resume
    # versions and the interview turns and evaluations.
    for child, parent in NESTED.items():
        assert child in CARRIED, f"nested table {child} is not carried at all"
        assert parent in CARRIED, f"nested table {child} names a parent ({parent}) not carried"
        assert CARRIED[child] == CARRIED[parent], (
            f"{child} rides {parent} but maps to section {CARRIED[child]!r}, "
            f"while {parent} maps to {CARRIED[parent]!r}"
        )


def test_the_exclusion_table_says_which_kind_of_exclusion() -> None:
    rows = documented_rows()
    assert rows, f"no rows were read out of the exclusion table in {EXPORT_DOC}"
    for table, reason in rows:
        assert reason.startswith(_REASON_PREFIXES), (
            f"the exclusion of {table} does not start with one of "
            f"{_REASON_PREFIXES}: {reason!r}"
        )
        prefix = next(p for p in _REASON_PREFIXES if reason.startswith(p))
        assert len(reason) > len(prefix) + 10, (
            f"the exclusion of {table} says only {reason!r}; a reason has to "
            "say why the reader does not need it"
        )


def full_bundle() -> dict:
    """A bundle carrying one row in every section, for the order gates."""
    data = {section: [{}] for section in SECTIONS}
    data["profile"] = {"display_name": "A candidate"}
    return {
        "schema_version": "1.5.0",
        "generated_at": "2026-10-31T00:00:00Z",
        "user": {"id": "00000000-0000-0000-0000-000000000000"},
        "manifest": {"counts": section_counts(data)},
        "data": data,
    }


def test_the_manifest_counts_walk_the_section_tuple() -> None:
    # The manifest is what the browser reads its list from (40.4), so its
    # order is the page's order. A dict built in another order would let the
    # server's tuple and the page's badges drift while both stayed complete.
    assert list(section_counts({})) == list(SECTIONS)
    assert list(full_bundle()["manifest"]["counts"]) == list(SECTIONS)


def _positions(text: str, headings: list[tuple[str, str]]) -> list[int]:
    found: list[int] = []
    for section, heading in headings:
        assert heading in text, f"the document has no heading for {section}: {heading!r}"
        found.append(text.index(heading))
    return found


def test_the_markdown_view_walks_the_section_tuple() -> None:
    titles = section_titles("en")
    text = to_markdown(full_bundle(), "en")
    headings = [(section, f"## {titles[section]}") for section in SECTIONS]
    positions = _positions(text, headings)
    assert positions == sorted(positions), (
        "the Markdown view lists its sections out of the bundle's order: "
        f"{[section for section, _ in headings]}"
    )


def test_the_print_view_walks_the_section_tuple() -> None:
    titles = section_titles("en")
    text = to_html(full_bundle(), "en")
    headings = [(section, f"<h2>{titles[section]}</h2>") for section in SECTIONS]
    positions = _positions(text, headings)
    assert positions == sorted(positions), (
        "the print view lists its sections out of the bundle's order: "
        f"{[section for section, _ in headings]}"
    )
