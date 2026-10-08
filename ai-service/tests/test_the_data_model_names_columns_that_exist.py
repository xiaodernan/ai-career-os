"""docs/architecture.md section 4 names columns; the migrations are what create them.

The data-model section is prose a reader trusts to be the schema -- it is where you look
before writing a query, a projection, or a migration of your own. Six of the names it
wrote existed in no migration at all: `jobs.required_years` (the column is
`experience_years`), `applications.stage_order` and `applications.updated_by_user` (the
board orders by `position`, and nothing records who last moved a card),
`knowledge_sources.doc_id` (the column is `document_id`), `experiences.end_date` (the
columns are `start_month`/`end_month`), and `password_reset_tokens.used` (it is
`used_at`). Two more tables the migrations create -- `application_events`, the timeline
`GET /applications/{id}/timeline` replays, and `user_notes`, the table behind
`GET /knowledge/notes` -- the section never named at all. Nothing reddened: a doc string
is not compiled, and the schema it describes is only ever created by the migrations.

So the section is read as data. Every `` `table(col, col, ...)` `` it writes is checked
against the columns the Flyway migrations actually create -- every CREATE TABLE body plus
every ALTER TABLE ADD COLUMN -- and a column the doc names that no migration creates
fails here. The other direction is deliberately not asserted: the section's own
convention line says `created_at`/`updated_at` ride along on every table, so an
undocumented timestamp is the doc being terse, not the doc being wrong.

Column lists are split on commas at bracket depth zero, because the doc writes
`kind enum[a, b, c]` and `structured jsonb (the canonical ResumeProfile JSON, §3 of PRD)`
and a naive split would invent columns out of the enum values.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
MIGRATIONS = ROOT / "backend" / "src" / "main" / "resources" / "db" / "migration"
DOC = ROOT / "docs" / "architecture.md"

SECTION = re.compile(r"## 4\. Data model.*?(?=\n## )", re.S)
COMMENT = re.compile(r"/\*.*?\*/", re.S)
# `-- oauth-ready` trails a column definition in V1; left in place it swallows the column
# that follows it, because the split then hands `split_columns` a part starting with `--`
LINE_COMMENT = re.compile(r"--[^\n]*")
CREATE = re.compile(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)\s*\((.*?)\n\);", re.S)

# the doc spells these out once in prose instead of per table
CONVENTION_COLUMNS = {"id", "created_at", "updated_at", "deleted_at"}

# written inside a `table(...)` body but not columns: `uniq(user,job,rv)`
CONSTRAINT_WORDS = {"uniq", "unique", "pk", "primary", "foreign", "check", "constraint",
                    "index", "references"}


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def split_columns(inside: str) -> list[str]:
    """The column names in a `table(...)` body, splitting only on top-level commas."""
    inside = LINE_COMMENT.sub(" ", COMMENT.sub(" ", inside))
    parts, depth, buf = [], 0, ""
    for char in inside:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(buf)
            buf = ""
        else:
            buf += char
    parts.append(buf)
    names = []
    for part in parts:
        name = re.match(r"\s*([a-z_][a-z0-9_]*)", part.strip())
        if name and name.group(1) not in CONSTRAINT_WORDS:
            names.append(name.group(1))
    return names


def section_bullets() -> list[str]:
    """Section 4's bullets, with the wrapped continuation lines folded back in."""
    body = SECTION.search(read(DOC))
    assert body, "architecture.md no longer has a `## 4. Data model` section"
    out: list[str] = []
    for line in body.group(0).split("\n"):
        if line.startswith("- "):
            out.append(line[2:])
        elif line.strip() and out:
            out[-1] += " " + line.strip()
    return out


def documented_tables() -> dict[str, set[str]]:
    """table -> the columns section 4 names for it.

    A `` `table(...)` `` span is found by opening paren and closed by the paren that balances
    it, not by the next backtick: the section quotes identifiers *inside* the column list
    (`job_matches`'s `_technical_score` denominator), and a backtick-delimited match would
    silently cut that table out of the census -- which is how a phantom column survived here.
    """
    out: dict[str, set[str]] = {}
    for bullet in section_bullets():
        for opening in re.finditer(r"`(\w+)\(", bullet):
            depth, end = 1, opening.end()
            while end < len(bullet) and depth:
                if bullet[end] in "([{":
                    depth += 1
                elif bullet[end] in ")]}":
                    depth -= 1
                end += 1
            if depth:
                continue
            # `educations(...)` and `achievements(...)` are named with no column list on
            # purpose ("same pattern"), and still count as described
            out.setdefault(opening.group(1), set()).update(
                split_columns(bullet[opening.end():end - 1]))
    return out


def schema() -> dict[str, set[str]]:
    """table -> the columns the migrations create, CREATE TABLE bodies and ALTERs alike."""
    out: dict[str, set[str]] = {}
    for path in sorted(MIGRATIONS.glob("*.sql")):
        text = read(path)
        for match in CREATE.finditer(text):
            out.setdefault(match.group(1), set()).update(split_columns(match.group(2)))
        table = None
        for line in text.split("\n"):
            altered = re.search(r"ALTER TABLE (?:IF NOT EXISTS )?(\w+)", line)
            if altered:
                table = altered.group(1)
                out.setdefault(table, set())
                out[table].update(re.findall(r"ADD COLUMN (?:IF NOT EXISTS )?(\w+)", line))
                continue
            if line.strip().startswith(("CREATE ", "INSERT ", "UPDATE ", "DROP ",
                                        "COMMENT ON", "--", "/*", "SET ", "DO ")):
                table = None
                continue
            if table:
                out[table].update(re.findall(r"ADD COLUMN (?:IF NOT EXISTS )?(\w+)", line))
    return out


def test_every_column_the_data_model_names_is_a_column_a_migration_creates():
    columns = schema()
    problems = []
    for table, named in sorted(documented_tables().items()):
        if table not in columns:
            problems.append(f"section 4 documents a table `{table}` no migration creates")
            continue
        phantom = sorted(named - columns[table])
        if phantom:
            problems.append(f"{table}: {', '.join(phantom)}")
    assert problems == [], (
        "docs/architecture.md section 4 names columns the schema does not have:\n  "
        + "\n  ".join(problems))


def test_the_data_model_describes_every_table_the_migrations_create():
    """The other direction: a table the schema creates and the section never names.

    Checked too, because a section that documented one table correctly would pass the
    column check above on its own. Two were missing when this gate was written --
    `application_events` (the timeline `GET /applications/{id}/timeline` replays, and what
    the dashboard's recent activity reads) and `user_notes` (the table behind
    `GET /knowledge/notes`, which is not the same thing as an ingested `knowledge_sources`
    row of `kind = note`).
    """
    documented, actual = documented_tables(), schema()
    assert len(actual) >= 30, f"only {len(actual)} tables walked; the migration parser is broken"
    missing = sorted(set(actual) - set(documented))
    assert missing == [], (
        f"section 4 describes {len(documented)} of {len(actual)} tables; {missing} are absent, "
        f"so a reader learns their shape from the migrations or not at all")
    for table in ("jobs", "applications", "knowledge_sources", "resume_versions",
                  "job_matches", "user_notes", "application_events"):
        assert table in documented, f"section 4 no longer describes `{table}`"
