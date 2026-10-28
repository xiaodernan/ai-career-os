"""The anonymized export has to actually forget -- everywhere.

The reader has two ways to leave with their data: the **redaction** drops
whole sections, and the **anonymized export** keeps the shape and takes the
people out of it. The docs call the second one "the right-to-be-forgotten
surface", so it has to forget.

It used to forget nothing. It blanked four field names on the profile --
``email``, ``display_name``, ``phone``, ``address`` -- and the profile has
carried none of them for as long as the export has existed, so the button
called "Export anonymized" exported everything: the reader's own uuid, the
links to their profiles, their resume's plaintext, every answer they gave
an interviewer, and (since 1.2.0) the notes they typed and the people they
know, with their email.

Then it forgot almost everything, and the rest of the leaks were all one
shape: **a column nobody thought of as the reader's.** Proven against the
running system rather than against the code:

* the note's full text, inside the knowledge row's ``meta`` -- a JSON bag
  whose *name* says nothing about what is in it;
* the note's title, and the note's tags;
* the reader's own uuid in every job-description row;
* the reader's own uuid inside the storage key of every uploaded document;
* the reader's uuid and the evaluation that quotes their answer back, in
  every interview turn.

The gate holds four things:

* the *profile entity* is checked against the old strip list, so the list
  that used to do nothing cannot quietly start doing something;
* the bundle the gate works on is **built from the real sources** -- the
  real tables, the real queries, the real rows the backend writes -- so a
  fixture shaped like the old thing cannot make the gate pass again. The
  fixture that hid the ``meta`` leak was shaped like a document row that
  has no ``meta`` in it;
* every real column is **classified**: the reader's, or the substance of a
  job search. A column nobody classified fails the gate;
* the anonymized bundle carries **none** of the reader's words -- not in a
  named field, not in a bag, not in a row inside a row.
"""

from pathlib import Path
import json
import re

import pytest

from app.features import export as ex

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "backend" / "src" / "main" / "resources" / "db" / "migration" / "V1__init_schema.sql"
EXPORT_SOURCE = ROOT / "ai-service" / "app" / "features" / "export.py"
DOMAIN_SOURCE = ROOT / "ai-service" / "app" / "db" / "domain.py"
INGEST_SOURCE = ROOT / "ai-service" / "app" / "api" / "ingest.py"
BACKEND_EXPORT = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "report" / "service" / "ExportService.java"
PROFILE_ENTITY = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "auth" / "entity" / "UserProfile.java"

# The marker that stands for "the reader's own words". Every column the gate
# calls the reader's carries its own marker, so the check at the end can say
# which one survived and where.
MARKER = "LEAK-{section}-{column}"


# --------------------------------------------------------------------------- #
# The real shape of the data. Nothing here is written down twice: the
# columns come out of the tables the export reads and the rows the backend
# writes.
# --------------------------------------------------------------------------- #


def _entity_columns(path: Path) -> set[str]:
    """The column names an entity declares."""
    source = path.read_text(encoding="utf-8")
    named = set(re.findall(r'@Column\([^)]*name\s*=\s*"([a-z_]+)"', source))
    return named


def _table(name: str) -> dict[str, str]:
    """A table's columns and their types, read out of the migration."""
    sql = MIGRATION.read_text(encoding="utf-8")
    start = sql.index(f"CREATE TABLE {name} ")
    body = sql[start : sql.index(");", start)]
    columns: dict[str, str] = {}
    for line in body.splitlines()[1:]:
        m = re.match(r"\s{2}(\w+)\s+([a-zA-Z]+)", line)
        if not m:
            continue
        if m.group(1).upper() in {
            "UNIQUE", "PRIMARY", "FOREIGN", "CONSTRAINT", "CHECK", "INDEX", "EXCLUDE",
        }:
            continue
        columns[m.group(1)] = m.group(2)
    return columns


def _sql_fragments(source: str) -> list[str]:
    """The SQL in a source file, one statement at a time.

    The statements live in triple-quoted strings, and a reader that matches
    ``SELECT ... FROM <table>`` across the whole file will happily join two
    statements into one query -- and then the gate is holding a query that
    was never written.
    """
    return [part for part in source.split('"""') if "SELECT" in part.upper()]


def _query_columns(source: str, table: str) -> tuple[list[str] | None, list[str]]:
    """What a query over ``table`` names: the columns, and the AS aliases.

    ``None`` for the columns means the query said ``*`` -- then the table
    decides.
    """
    for fragment in _sql_fragments(source):
        m = re.search(
            r"SELECT\s+(.+?)\s+FROM\s+" + table + r"\b", fragment, re.S | re.I
        )
        if not m:
            continue
        columns: list[str] = []
        aliases: list[str] = []
        star = False
        for part in m.group(1).split(","):
            part = part.strip()
            if part == "*" or part.endswith(".*"):
                star = True
                continue
            alias = re.search(r"\bAS\s+(\w+)\s*$", part, re.I)
            if alias:
                aliases.append(alias.group(1))
                columns.append(alias.group(1))
            else:
                columns.append(part.split(".")[-1].split()[0])
        # A query that says `*` takes its columns from the table -- but the
        # aliases it adds are its own, and they are columns the bundle carries
        # that the table does not have.
        return (None if star else columns), aliases
    return None, []


# The export's own fetch function per section. The gate follows it to the
# query it runs -- including through a call into the domain module -- so the
# columns are the ones the bundle really carries, not the ones a name
# suggests.
FETCHERS: dict[str, tuple[str, str]] = {
    "profile": ("export", "fetch_profile"),
    "resumes": ("export", "fetch_resume_versions"),
    "knowledge": ("export", "fetch_documents"),
    "job_descriptions": ("export", "fetch_jds"),
    "memories": ("export", "fetch_memories"),
    "interviews": ("export", "fetch_interview_sessions"),
}


def _function_body(source: str, name: str) -> str:
    """A Python function's own body, up to the next one at the same level."""
    m = re.search(r"^async def " + name + r"\b|^def " + name + r"\b", source, re.M)
    assert m, f"the source has no `{name}` any more"
    rest = source[m.end() :]
    nxt = re.search(r"^(async def |def )", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def _query_for(section: str) -> tuple[list[str] | None, list[str]]:
    """The columns and aliases the section's own query names."""
    where, name = FETCHERS[section]
    if where == "export":
        body = _function_body(EXPORT_SOURCE.read_text(encoding="utf-8"), name)
        # A fetcher that asks the domain module does the asking there.
        call = re.search(r"domain\.(\w+)\(", body)
        if call and "SELECT" not in body:
            body = _function_body(DOMAIN_SOURCE.read_text(encoding="utf-8"), call.group(1))
    else:
        body = _function_body(DOMAIN_SOURCE.read_text(encoding="utf-8"), name)

    table = _table_for(section)
    columns, aliases = _query_columns(body, table)
    return columns, aliases


def _table_for(section: str) -> str:
    """The table a section's rows come from."""
    return {
        "profile": "user_profiles",
        "resumes": "resume_versions",
        "knowledge": "documents",
        "job_descriptions": "job_jds",
        "memories": "user_memories",
        "interviews": "interview_sessions",
    }[section]


def _ai_columns(table: str, sources: tuple[str, ...]) -> tuple[list[str], dict[str, str]]:
    """The columns one of the export's own queries carries, and their types."""
    for source in sources:
        columns, aliases = _query_columns(source, table)
        if columns is None:
            continue
        return _unique(columns + aliases), _table(table)
    for source in sources:
        _columns, aliases = _query_columns(source, table)
        if _columns is None and aliases:
            return _unique(list(_table(table)) + aliases), _table(table)
    return list(_table(table)), _table(table)


def _unique(columns: list[str]) -> list[str]:
    """The columns, in order, without the ones that repeat."""
    out: list[str] = []
    for column in columns:
        if column not in out:
            out.append(column)
    return out


def _backend_rows(section: str) -> list[str]:
    """The columns the backend puts in one section's rows, in its own words.

    The backend builds those rows by hand -- ``row.put("name", ...)`` -- so
    the row it writes is the real shape, and a field it starts writing has
    to be classified by the gate or the gate fails.
    """
    source = BACKEND_EXPORT.read_text(encoding="utf-8")
    m = re.search(
        r'sections\.put\("' + section + r'",[\s\S]{0,300}?ExportService::to(\w+)', source
    )
    assert m, f"the backend does not build the {section} section any more"
    method = source.index("static Map<String, Object> to" + m.group(1))
    body = _method_body(source, method)
    return re.findall(r'row\.put\("(\w+)"', body)


def _method_body(source: str, start: int) -> str:
    """A Java method's own body -- up to its closing brace, not the next one."""
    depth = 0
    opened = False
    for index in range(start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
            opened = True
        elif char == "}":
            depth -= 1
            if opened and depth == 0:
                return source[start : index + 1]
    return source[start:]


# --------------------------------------------------------------------------- #
# The gate's own judgement: which columns are the reader's, and which are
# the substance of a job search.
#
# The rule, in one line: a column is the reader's when it can hold their
# identity, their own words, or a pointer into their own storage.
# Everything else is the substance -- the posting, the title, the company,
# the status, the counts, the timestamps -- and an export that leaves
# nothing behind is not an export.
# --------------------------------------------------------------------------- #

PEOPLE: dict[str, frozenset[str]] = {
    "profile": frozenset({"user_id", "summary", "links"}),
    "resumes": frozenset({"user_id", "label", "resume_title", "plaintext", "structured", "diff"}),
    "knowledge": frozenset({"user_id", "title", "text_excerpt", "file_key"}),
    "job_descriptions": frozenset({"user_id"}),
    "memories": frozenset({"key", "content"}),
    "interviews": frozenset({"user_id", "evaluation"}),
    "notes": frozenset({"title", "content", "tags"}),
    "contacts": frozenset({"name", "role", "company", "relation", "email", "notes"}),
    "applications": frozenset({"notes", "rejection_reason", "offer_compensation"}),
    "growth_plans": frozenset({"coverage", "report"}),
}

# The interview turns are their own group: a list of rows inside the row.
TURN_PEOPLE = frozenset({"user_id", "content", "evaluation"})

# The bags: a column that holds a JSON object -- or a list of rows -- whose
# *inside* holds the reader. The column itself is neither the reader's nor
# the substance; what is inside it is classified below.
BAGS: dict[str, frozenset[str]] = {
    "knowledge": frozenset({"meta"}),
    "interviews": frozenset({"turns"}),
}

# The bags: a column that holds a JSON object whose *inside* holds the
# reader. The keys inside it that do are named here.
PEOPLE_INSIDE: dict[str, dict[str, frozenset[str]]] = {
    "knowledge": {"meta": frozenset({"inline_text"})},
    "interviews": {"turns": TURN_PEOPLE},
}

# The keys of the bag that are its shape rather than its content.
SHAPE_INSIDE: dict[str, dict[str, frozenset[str]]] = {
    "knowledge": {"meta": frozenset({"kind"})},
}

# The substance: the job search itself. The posting, the title, the company,
# the status, the counts, the timestamps, the ids.
#
# It is written out rather than derived, on purpose. Derived, a column that
# appears tomorrow would be substance by default -- and nobody would have
# decided anything about it. Written out, the gate says "which column is
# that?" and the answer has to be a decision.
SUBSTANCE: dict[str, frozenset[str]] = {
    "profile": frozenset({
        "id", "headline", "location", "years_experience", "target_roles",
        "target_locations", "work_authorization", "preferences",
        "created_at", "updated_at",
    }),
    "resumes": frozenset({
        "id", "resume_id", "kind", "job_id", "score", "created_at",
    }),
    "knowledge": frozenset({
        "id", "source_id", "media_type", "content_hash", "status",
        "created_at", "updated_at",
    }),
    "job_descriptions": frozenset({
        "id", "job_id", "raw_text", "parsed", "created_at",
    }),
    "memories": frozenset({
        "id", "kind", "importance", "source", "created_at", "updated_at",
    }),
    "interviews": frozenset({
        "id", "job_id", "jd_id", "resume_version_id", "company_name",
        "position_title", "mode", "status", "difficulty", "config",
        "started_at", "finished_at", "job_title",
    }),
    "notes": frozenset({"id", "created_at", "updated_at"}),
    "contacts": frozenset({"id", "last_touch_at", "created_at", "updated_at"}),
    "applications": frozenset({
        "id", "title", "company_name", "status", "applied_at", "reminder_at",
        "created_at", "updated_at",
    }),
    "growth_plans": frozenset({"id", "target_role", "created_at"}),
}

TURN_SUBSTANCE = frozenset({
    "id", "session_id", "seq", "role", "question_meta", "created_at",
})


# --------------------------------------------------------------------------- #
# The real columns, per section.
# --------------------------------------------------------------------------- #

def _real_columns() -> dict[str, list[str]]:
    real: dict[str, list[str]] = {}
    for section in FETCHERS:
        columns, aliases = _query_for(section)
        table = _table_for(section)
        if columns is None:
            columns = list(_table(table))
        real[section] = _unique(columns + aliases)
    # The turns are a list of rows inside the session's row -- the export
    # puts them there, so the session's row carries a key the table does
    # not have. The report is one too: it lives in its own table, and the
    # restore reads it off the session.
    real["interviews"] = real["interviews"] + ["turns", "evaluation"]
    for section in ("notes", "contacts", "applications", "growth_plans"):
        real[section] = _backend_rows(section)
    return real


def _turn_columns() -> list[str]:
    return list(_table("interview_turns"))


# --------------------------------------------------------------------------- #
# The bundle the gate works on: shaped like the real one.
# --------------------------------------------------------------------------- #

def _value(column: str, kind: str) -> object:
    """A value of the shape the real column holds."""
    if kind == "jsonb":
        return json.dumps({"kind": "note"})
    if kind.endswith("[]") or kind == "text[]":
        return ["one", "two"]
    if column.endswith("_at") or column.endswith("_date"):
        return "2026-01-01T00:00:00Z"
    if column == "id":
        return "00000000-0000-0000-0000-000000000001"
    if kind in {"int", "integer", "numeric", "bigint", "smallint", "real", "double"}:
        return 1
    if kind in {"bool", "boolean"}:
        return False
    return "ok"


def _marker(section: str, column: str) -> str:
    return MARKER.format(section=section, column=column)


def _row(section: str, columns: list[str], types: dict[str, str]) -> dict:
    """One row, carrying a marker in every column the reader's own."""
    row: dict = {}
    for column in columns:
        if column in PEOPLE.get(section, frozenset()):
            row[column] = _marker(section, column)
        elif column == "meta":
            # The bag: the reader's text inside, the shape beside it.
            row[column] = json.dumps(
                {"inline_text": _marker(section, "meta.inline_text"), "kind": "note"}
            )
        else:
            row[column] = _value(column, types.get(column, "text"))
    return row


def _realistic_bundle() -> dict:
    """A bundle shaped like the real one -- the columns the sources declare."""
    tables = {
        "profile": "user_profiles",
        "resumes": "resume_versions",
        "knowledge": "documents",
        "job_descriptions": "job_jds",
        "memories": "user_memories",
        "interviews": "interview_sessions",
    }
    raw: dict = {}
    for section, table in tables.items():
        columns, aliases = _query_for(section)
        if columns is None:
            columns = list(_table(table))
        row = _row(section, _unique(columns + aliases), _table(table))
        # The profile is the one section that is a single object, not a list.
        raw[section] = row if section == "profile" else [row]

    # The interview turns: a list of rows inside the session's row.
    session = raw["interviews"][0]
    session["turns"] = [
        {
            column: (
                _marker("interviews.turns", column)
                if column in PEOPLE_INSIDE["interviews"]["turns"]
                else _value(column, _table("interview_turns").get(column, "text"))
            )
            for column in _turn_columns()
        }
    ]
    # And the report the restore reads off the session: it quotes the
    # answers back, so it is the reader's in the same way the growth
    # report is.
    session["evaluation"] = _marker("interviews", "evaluation")

    for section in ("notes", "contacts", "applications", "growth_plans"):
        columns = _backend_rows(section)
        raw[section] = [_row(section, columns, {})]

    return ex.build_bundle("11111111-1111-1111-1111-111111111111", raw)


# --------------------------------------------------------------------------- #
# The gates.
# --------------------------------------------------------------------------- #

def test_the_old_strip_list_named_fields_the_profile_does_not_have() -> None:
    # The reason the export forgot nothing: the four names the old answer
    # blanked are not the profile's columns. If the profile ever grows one of
    # them, the list has to grow with it -- and until then, the list is
    # decoration.
    columns = _entity_columns(PROFILE_ENTITY)
    assert columns, "no column was read out of the profile entity: the gate would prove nothing"
    for name in ex.DEFAULT_PII_FIELDS:
        assert name not in columns, (
            f"the profile now carries `{name}`, which the anonymized export used "
            "to strip -- the list of what it removes has to grow before this goes quiet"
        )


def test_every_real_column_is_classified() -> None:
    """A column nobody classified is a column nobody thought about.

    This is the check that would have caught the leaks: the knowledge row's
    ``meta``, the note's ``tags``, the job description's ``user_id``, the
    document's ``file_key``. All of them were real columns, and all of them
    were nobody's decision.

    The classification is a partition -- the reader's, or the substance --
    and it has to be exact in both directions: a column nobody classified
    fails the gate, and so does a column that is classified twice.
    """
    for section, columns in _real_columns().items():
        classified = (
            PEOPLE.get(section, frozenset())
            | SUBSTANCE.get(section, frozenset())
            | BAGS.get(section, frozenset())
        )
        for column in columns:
            assert column in classified, (
                f"the {section} row carries a column nobody classified: "
                f"`{column}`. Say whether it is the reader's or the substance "
                "of a job search -- an export that leaves nothing behind is not "
                "an export, and an export that leaves the reader behind is not "
                "an export either"
            )
        assert classified == set(columns), (
            f"the {section} section is classified as {sorted(classified)}, but "
            f"the row carries {sorted(columns)}: the two have to be the same "
            "set of names"
        )


def test_every_turn_column_is_classified() -> None:
    """The turns are a group of their own: a list of rows inside the row."""
    classified = TURN_PEOPLE | TURN_SUBSTANCE
    for column in _turn_columns():
        assert column in classified, (
            f"the interview turn carries a column nobody classified: `{column}`"
        )
    assert classified == set(_turn_columns()), (
        f"the turns are classified as {sorted(classified)}, but the turn "
        f"carries {sorted(_turn_columns())}"
    )


def test_the_policy_is_exactly_what_the_gate_calls_the_readers() -> None:
    """The code and the gate have to agree about what is the reader's.

    The gate is the stricter statement: it names the reader's columns, and
    the code has to blank exactly those. A column the code blanks that the
    gate calls substance is a bug too -- it is the export that leaves
    nothing behind.
    """
    for section in sorted(PEOPLE):
        assert set(ex.ANONYMIZED_FIELDS.get(section, ())) == set(PEOPLE[section]), (
            f"the {section} section: the code blanks {sorted(ex.ANONYMIZED_FIELDS.get(section, ()))}, "
            f"and the gate calls {sorted(PEOPLE[section])} the reader's"
        )
    for section in sorted(PEOPLE_INSIDE):
        assert set(ex.ANONYMIZED_NESTED_FIELDS.get(section, {})) == set(PEOPLE_INSIDE[section]), (
            f"the {section} section: the code's bags are "
            f"{sorted(ex.ANONYMIZED_NESTED_FIELDS.get(section, {}))}, and the gate "
            f"knows {sorted(PEOPLE_INSIDE[section])}"
        )


def _call_arguments(source: str, start: int) -> str:
    """The arguments of a call, up to its closing parenthesis."""
    depth = 0
    for index in range(start, len(source)):
        char = source[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    return source[start:]


def test_the_bag_writer_has_no_unclassified_key() -> None:
    """The bag's shape is owned by whoever writes into it.

    The bag's keys are read out of the writer that fills it, so a writer that
    grows a new key -- a new place to put the reader's own text -- has to be
    classified here or the gate says so.
    """
    source = INGEST_SOURCE.read_text(encoding="utf-8")
    start = source.index("create_document(")
    keys = set(re.findall(r'"(\w+)"\s*:', _call_arguments(source, start)))
    assert keys, "no key was read out of the bag writer: the gate would prove nothing"

    declared = PEOPLE_INSIDE["knowledge"]["meta"] | SHAPE_INSIDE["knowledge"]["meta"]
    for key in keys:
        assert key in declared, (
            f"the bag writer puts `{key}` in the bag and nobody said whether it "
            "is the reader's words or the bag's shape"
        )


def test_the_anonymized_export_carries_none_of_the_readers_words() -> None:
    """The whole check, in one place: no marker survives anywhere.

    Not in a named field -- in a bag, not in a row inside a row, not in a
    column the policy forgot to mention. The file is searched as text, the
    way a person who received it would read it.
    """
    bundle = _realistic_bundle()
    out = ex.anonymize(bundle)
    text = json.dumps(out, ensure_ascii=False)

    survivors = [
        marker for marker in _markers(_realistic_bundle()) if marker in text
    ]
    assert survivors == [], (
        "the anonymized export still carries the reader's words: "
        + ", ".join(sorted(survivors))
    )


def _markers(bundle: dict) -> list[str]:
    """Every marker in the bundle, read out of the bundle itself."""
    found: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and value.startswith("LEAK-"):
            found.append(value)

    walk(bundle.get("data", {}))
    return found


def test_the_flag_means_the_file_is_anonymized() -> None:
    """The path the button takes, not the function behind it.

    The flag used to set the two ``anonymized`` markers and nothing else --
    and the printable document prints "（已匿名）" beside the reader's id
    because it believes them. So the file said it was anonymized while
    carrying the reader's uuid, their links, their resume's plaintext and
    every answer they gave an interviewer.

    The strip has to happen where the bundle is built, or the flag is a
    promise the file does not keep.
    """
    raw = _realistic_bundle()["data"]
    bundle = ex.build_bundle("11111111-1111-1111-1111-111111111111", raw, anonymized=True)

    assert bundle["user"]["anonymized"] is True
    assert bundle["manifest"]["anonymized"] is True
    assert bundle["user"]["id"] is None, "the bundle still carries the reader's id"
    assert bundle["data"]["profile"]["user_id"] is None
    assert bundle["data"]["contacts"][0]["name"] is None
    assert bundle["data"]["notes"][0]["content"] is None
    assert bundle["data"]["resumes"][0]["plaintext"] is None
    assert bundle["data"]["interviews"][0]["turns"][0]["content"] is None
    assert bundle["data"]["memories"][0]["content"] is None
    assert ex.validate_bundle(bundle) == [], (
        f"the anonymized bundle is not a valid bundle: {ex.validate_bundle(bundle)}"
    )


def test_the_anonymized_export_takes_the_people_out() -> None:
    bundle = _realistic_bundle()
    out = ex.anonymize(bundle)

    profile = out["data"]["profile"]
    for field in ("user_id", "links", "summary"):
        assert profile[field] is None, f"the profile still carries its `{field}`"

    contact = out["data"]["contacts"][0]
    for field in ("name", "role", "company", "relation", "email", "notes"):
        assert contact[field] is None, f"the contact still carries its `{field}`"

    note = out["data"]["notes"][0]
    for field in ("title", "content", "tags"):
        assert note[field] is None, f"the note still carries its `{field}`"

    resume = out["data"]["resumes"][0]
    for field in ("user_id", "label", "resume_title", "plaintext", "structured", "diff"):
        assert resume[field] is None, f"the resume still carries its `{field}`"

    turn = out["data"]["interviews"][0]["turns"][0]
    for field in ("user_id", "content", "evaluation"):
        assert turn[field] is None, f"the turn still carries its `{field}`"

    memory = out["data"]["memories"][0]
    for field in ("key", "content"):
        assert memory[field] is None, f"the memory still carries its `{field}`"

    application = out["data"]["applications"][0]
    for field in ("notes", "rejection_reason", "offer_compensation"):
        assert application[field] is None, f"the application still carries its `{field}`"

    document = out["data"]["knowledge"][0]
    for field in ("user_id", "title", "text_excerpt", "file_key"):
        assert document[field] is None, f"the document still carries its `{field}`"

    # The bag: the reader's text inside goes, the shape of the bag stays.
    bag = json.loads(out["data"]["knowledge"][0]["meta"])
    assert bag["inline_text"] is None, "the bag still carries the reader's text"
    assert bag["kind"] == "note", "the bag lost its shape: what it *was* is not the reader"

    assert out["user"]["id"] is None, "the envelope still carries the reader's id"
    assert out["user"]["anonymized"] is True
    assert out["manifest"]["anonymized"] is True


def test_the_anonymized_export_keeps_the_shape_and_the_substance() -> None:
    # The other half of the claim: an export that leaves nothing behind is
    # not an export. The counts still say what was there, the ids are still
    # ids, and the substance of a job search -- the posting, the headline,
    # the years -- is still in it.
    bundle = _realistic_bundle()
    out = ex.anonymize(bundle)

    assert out["manifest"]["counts"] == bundle["manifest"]["counts"], (
        "the anonymized export changed the counts: the reader cannot tell what "
        "the file holds"
    )
    assert out["data"]["profile"]["headline"] == bundle["data"]["profile"]["headline"]
    assert out["data"]["profile"]["location"] == bundle["data"]["profile"]["location"]
    assert out["data"]["notes"][0]["id"] == bundle["data"]["notes"][0]["id"]
    # The posting is not the reader's own material: an anonymized export
    # still carries it. The row that says *whose* posting it is does not.
    assert out["data"]["job_descriptions"][0]["raw_text"] == bundle["data"]["job_descriptions"][0]["raw_text"]
    assert out["data"]["job_descriptions"][0]["user_id"] is None


def test_the_anonymized_export_leaves_the_original_alone() -> None:
    bundle = _realistic_bundle()
    before = bundle["data"]["contacts"][0]["name"]
    ex.anonymize(bundle)
    assert bundle["data"]["contacts"][0]["name"] == before, (
        "the anonymized export changed the bundle it was given: the reader's own "
        "data was edited by a copy"
    )


def test_the_anonymized_export_re_stamps_the_hash() -> None:
    # The hash covers the data, so a bundle whose data changed carries a hash
    # of the old data -- and the import path would refuse it as tampered.
    bundle = _realistic_bundle()
    out = ex.anonymize(bundle)
    assert out["manifest"]["content_hash"] != bundle["manifest"]["content_hash"]
    assert ex.validate_bundle(out) == [], (
        f"the anonymized export is not a valid bundle: {ex.validate_bundle(out)}"
    )


@pytest.mark.parametrize("section", sorted(ex.ANONYMIZED_FIELDS))
def test_the_policy_names_fields_the_bundle_actually_carries(section: str) -> None:
    # The policy is written in the bundle's own field names, so a field the
    # bundle does not carry is a field the strip silently does nothing about
    # -- and the reader is still carrying it.
    bundle = _realistic_bundle()
    rows = bundle["data"].get(section)
    if isinstance(rows, dict):
        # The profile is the one section that is a single object.
        rows = [rows]
    if not isinstance(rows, list) or not rows:
        pytest.skip(f"the realistic bundle carries no {section} rows")
    for field in ex.ANONYMIZED_FIELDS[section]:
        assert field in rows[0], (
            f"the policy strips `{section}.{field}`, which the bundle does not "
            "carry: the strip does nothing and the reader keeps it"
        )
