"""The ai-service's SQL has to name columns the schema actually declares.

The export bundle is the reason this file exists. It read
`interview_sessions` with `ORDER BY s.created_at` -- a column that table has
never had: it has `started_at`. Every unit test passed, because the
export's fetch functions are monkeypatched in the tests and a fixture row
is a plain dict. The bundle was broken for every real workspace, and the
only thing that found it was the end-to-end suite running against a
database.

This is the gate that finds it without a database. The schema of record is
the backend's migrations -- the same files Flyway runs -- so the columns are
read out of them, and every column the ai-service's SQL names under a table
alias has to be one of them.

What it holds:

- every table the ai-service's SQL reads is a table the migrations create;
- every `<alias>.<column>` reference names a column that table declares;
- every migration that adds a table is one the ai-service could read.

The scan is textual, and it says so: it reads the SQL strings out of the
Python sources, so a query built at runtime out of fragments is not seen.
That is a known limit rather than an oversight -- the queries that talk to
the database are written out in full, and the ones that are not are the
ones the schema cannot check anyway.
"""

import io
import re
import tokenize
from pathlib import Path

MAIN = Path(__file__).resolve().parents[1]
BACKEND = MAIN.parents[0] / "backend"
MIGRATIONS = BACKEND / "src" / "main" / "resources" / "db" / "migration"

# The ai-service's own sources -- not its tests, which mock the database.
SOURCES = MAIN / "app"

# A `CREATE TABLE` block: the name, then the body up to the closing paren.
CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\n\);",
    re.IGNORECASE | re.DOTALL,
)

# A column declaration: the name, then its type. A `CONSTRAINT` line is not
# a column, and neither is a `PRIMARY KEY (...)` table constraint.
COLUMN = re.compile(r"^\s*(\w+)\s+\w", re.IGNORECASE)
NOT_A_COLUMN = re.compile(r"^\s*(CONSTRAINT|PRIMARY|FOREIGN|UNIQUE|CHECK|EXCLUDE|LIKE)\b",
                          re.IGNORECASE)

# `FROM <table> [AS] <alias>` -- the alias is what the columns are qualified
# with. A comma-joined table list is read one at a time.
FROM_TABLE = re.compile(
    r"\bFROM\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?",
    re.IGNORECASE,
)

# `<alias>.<column>` -- a qualified reference.
QUALIFIED = re.compile(r"\b(\w+)\.(\w+)\b")

# A SQL string in the Python sources.
#
# The literals are found with `tokenize`, which is the standard library's own
# answer to "where are the string literals" -- a scanner written by hand gets
# it wrong in two ways that both matter here: an apostrophe in a comment
# ("the bundle's own schema version") opens a string that swallows the query
# after it, and a `"""` string ends at the apostrophe in a docstring.
def string_literals(text: str) -> list[str]:
    """Every string literal's contents, in the order the file has them."""
    out: list[str] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type != tokenize.STRING:
                continue
            body = token.string
            # Drop the prefix (`r`, `b`, `f`, and their combinations) and
            # the quotes themselves.
            prefix = re.match(r"[A-Za-z]*", body).group(0)
            body = body[len(prefix):]
            for quote in ('"""', "'''", '"', "'"):
                if body.startswith(quote) and body.endswith(quote) and len(body) >= 2 * len(quote):
                    out.append(body[len(quote):-len(quote)])
                    break
    except (tokenize.TokenError, IndentationError):
        # A file that does not tokenize has no literals this gate can read.
        pass
    return out

# A word that is not a table alias: a schema qualifier, a function call's
# argument, a number, a keyword.
NOT_AN_ALIAS = re.compile(
    r"^(and|or|not|null|true|false|select|from|where|group|order|by|limit|offset|"
    r"join|left|right|inner|outer|on|as|distinct|case|when|then|else|end|"
    r"insert|into|values|update|set|delete|returning|with|union|all|"
    r"coalesce|nullif|count|sum|avg|min|max|coalesce|jsonb?|array|now|"
    r"interval|extract|date_trunc|coalesce)$",
    re.IGNORECASE,
)


def schema() -> dict[str, set[str]]:
    """Every table the migrations create, with the columns it declares."""
    tables: dict[str, set[str]] = {}
    for path in sorted(MIGRATIONS.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        for name, body in CREATE_TABLE.findall(text):
            columns: set[str] = set()
            for line in body.splitlines():
                if NOT_A_COLUMN.match(line):
                    continue
                match = COLUMN.match(line)
                if match:
                    columns.add(match.group(1).lower())
            tables[name.lower()] = columns
    return tables


def sql_statements() -> list[tuple[str, str]]:
    """Every SQL string in the ai-service's sources, with the file it came from.

    A literal only counts when it *is* SQL: it starts with a statement
    keyword, once leading comments and whitespace are out of the way. English
    prose in a docstring says "from memory" and "from a batch", and a
    scanner that cannot tell a sentence from a query will find tables in it.
    """
    out: list[tuple[str, str]] = []
    for path in sorted(SOURCES.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(MAIN)).replace("\\", "/")
        for body in string_literals(text):
            stripped = re.sub(r"(?m)^\s*--.*$", "", body).strip()
            if not re.match(r"(?is)^(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|WITH)\b",
                            stripped):
                continue
            out.append((rel, stripped))
    return out


def aliases(statement: str) -> dict[str, str]:
    """The alias each table is read under, and the table it stands for."""
    found: dict[str, str] = {}
    for table, alias in FROM_TABLE.findall(statement):
        table = table.lower()
        if alias and not NOT_AN_ALIAS.match(alias):
            found[alias.lower()] = table
        else:
            found[table] = table
    # A table read without an alias is qualified by its own name.
    return found


def test_the_migrations_are_readable_and_the_schema_is_not_empty():
    tables = schema()
    assert len(tables) >= 15, (
        f"{len(tables)} tables were read out of the migrations, which is fewer than the "
        "schema has; the reader has stopped understanding the DDL")
    assert "interview_sessions" in tables
    # The table the export bundle got wrong, read once so the pin is visible:
    # it has a start time and no creation time.
    assert "started_at" in tables["interview_sessions"]
    assert "created_at" not in tables["interview_sessions"]


def test_every_table_the_ai_service_reads_is_one_the_schema_declares():
    tables = schema()
    unknown: list[str] = []
    for rel, statement in sql_statements():
        for alias, table in aliases(statement).items():
            if table not in tables:
                unknown.append(f"{rel}: {table} (as {alias})")
    assert unknown == [], (
        f"{unknown}: the ai-service reads tables the migrations do not create; either the "
        "migration is missing or the query names a table that never existed")


def test_every_column_the_ai_service_names_is_one_the_table_declares():
    tables = schema()
    wrong: list[str] = []
    for rel, statement in sql_statements():
        mapping = aliases(statement)
        for alias, column in QUALIFIED.findall(statement):
            alias = alias.lower()
            column = column.lower()
            if alias not in mapping:
                continue
            table = mapping[alias]
            if table not in tables:
                continue
            if column in tables[table]:
                continue
            wrong.append(f"{rel}: {alias}.{column} -- {table} has no such column")
    assert wrong == [], (
        f"{wrong}: the ai-service names columns the schema does not declare. A query "
        "like this fails at runtime and nowhere else: the unit tests mock the "
        "database, and the end-to-end suite only reaches the query if a workspace "
        "has a row in that table.")


def test_the_gate_reads_the_schema_the_backend_actually_runs():
    """The schema of record is the migrations, and they are Flyway's."""
    names = {p.name for p in MIGRATIONS.glob("*.sql")}
    assert "V1__init_schema.sql" in names
    # And the ai-service's sources are where the gate looks -- a gate that
    # walked the tests would find only mocked queries and prove nothing.
    assert (SOURCES / "features" / "export.py").exists()
    assert (SOURCES / "db" / "domain.py").exists()
