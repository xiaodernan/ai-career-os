"""The export bundle's sections, read across the four places that name them.

The bundle is the one artifact this product hands a user to take somewhere
else, and it is written in more than one place: the ai-service writes it,
the backend writes the applications and the growth runs and hands them
over, the browser reads it back to redact a section and to restore one, and
the backend reads a restored bundle back to put it into the database.

The sections are named in each of those places, and the names are the
contract. Nothing about a bundle is more fragile than its section list: a
section the writer adds and the reader does not know about is a section
the reader cannot redact -- so the export carries the user's pipeline and
the redaction silently leaves it in -- and a section the reader knows and
the writer does not write is a section the reader promises to redact and
the bundle never had.

There is no parser here and no schema to read, because there is no
schema: the sections are a tuple of names in one file, a list of keys in
another, and two `Map.put` calls in a third. So the gate reads all of them
-- the ai-service's own tuple, the browser's own list, the backend's own
writer and the backend's own reader -- and holds them to the same set. A
section added on one side and not the other fails here rather than in a
user's export.

The browser's list is read from the page that offers the redaction
checkboxes (`app/(app)/data/page.tsx`), because that is the list that
decides what a reader can leave out. The backend's writer is read from
`ExportService`, which owns the two sections only the backend can produce.
The backend's reader is read from `ImportService`, which dispatches on the
plan's section names -- so a section the plan names and the importer does
not read is a section that is planned, counted, and then dropped on the
floor.
"""

from pathlib import Path
import re

import pytest

from app.features.export import (
    AI_SECTIONS,
    BACKEND_SECTIONS,
    SCHEMA_VERSION,
    SECTIONS,
    required_sections,
)

AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_SERVICE_ROOT.parent
FRONTEND_DATA_PAGE = REPO_ROOT / "frontend" / "src" / "app" / "(app)" / "data" / "page.tsx"
BACKEND_SERVICE = REPO_ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "report" / "service"
EXPORT_SERVICE = BACKEND_SERVICE / "ExportService.java"
IMPORT_SERVICE = BACKEND_SERVICE / "ImportService.java"

# The browser's redaction list: `{ key: "profile", labelKey: "data.sections.profile" }`.
# The `key` is the section's name in the bundle; the label is the reader's.
_SECTION_KEY = re.compile(r'\{\s*key:\s*"([a-z_]+)"\s*,\s*labelKey:\s*"data\.sections\.')

# The backend writes its sections with `sections.put("name", ...)`.
_JAVA_PUT = re.compile(r'\bsections\.put\(\s*"([a-z_]+)"')
# The backend reads the plan's sections with `sections.get("name")` and the
# bundle's rows with `data.get("name")`.
_JAVA_SECTION_GET = re.compile(r'\bsections\.get\(\s*"([a-z_]+)"')
_JAVA_DATA_GET = re.compile(r'(?<!bundle\.)\bdata\.get\(\s*"([a-z_]+)"')


def _frontend_sections() -> list[str]:
    """The section names the browser offers to redact."""
    source = FRONTEND_DATA_PAGE.read_text(encoding="utf-8")
    # Only the SECTIONS table, not the strings that happen to match elsewhere.
    start = source.index("const SECTIONS")
    end = source.index("] as const;", start)
    return _SECTION_KEY.findall(source[start:end])


def _backend_written_sections() -> list[str]:
    """The section names the backend writes into a bundle."""
    source = EXPORT_SERVICE.read_text(encoding="utf-8")
    return _JAVA_PUT.findall(source)


def _backend_read_sections() -> list[str]:
    """The section names the backend reads a plan's ops for."""
    source = IMPORT_SERVICE.read_text(encoding="utf-8")
    return _JAVA_SECTION_GET.findall(source)


def _backend_read_rows() -> list[str]:
    """The section names the backend reads a bundle's rows for."""
    source = IMPORT_SERVICE.read_text(encoding="utf-8")
    return _JAVA_DATA_GET.findall(source)


def test_the_browser_offers_exactly_the_sections_the_writer_writes() -> None:
    frontend = _frontend_sections()
    assert frontend, f"no sections were read out of {FRONTEND_DATA_PAGE}"
    assert sorted(frontend) == sorted(SECTIONS), (
        "the browser's redaction list and the bundle's sections have drifted apart: "
        f"the browser offers {sorted(frontend)}, the writer writes {sorted(SECTIONS)}"
    )


def test_the_browser_offers_no_section_twice() -> None:
    frontend = _frontend_sections()
    assert len(frontend) == len(set(frontend)), (
        f"the browser offers a section twice: {frontend}"
    )


def test_the_bundle_carries_the_pipeline_too() -> None:
    # The backend's sections are the ones the reader cannot get anywhere
    # else: the applications and the growth runs. A bundle without them is
    # a reading list, not a record of a search -- so they are in the
    # bundle, and the browser offers to redact them.
    assert BACKEND_SECTIONS == ("applications", "growth_plans")
    assert set(BACKEND_SECTIONS) <= set(SECTIONS)
    assert set(AI_SECTIONS) <= set(SECTIONS)


def test_the_backend_writes_exactly_the_sections_it_owns() -> None:
    # The backend owns two sections -- the applications and the growth runs
    # -- because those rows live in its own database and the ai-service
    # cannot read them. It writes them under their bundle names, and a name
    # the ai-service does not know is a section the bundle's manifest counts
    # and the reader cannot restore.
    written = _backend_written_sections()
    assert written, f"no sections were read out of {EXPORT_SERVICE}"
    assert sorted(written) == sorted(BACKEND_SECTIONS), (
        "the backend writes sections the bundle does not name, or names them "
        f"differently: the backend writes {sorted(written)}, the bundle names "
        f"{sorted(BACKEND_SECTIONS)}"
    )


def test_the_backend_restores_every_section_the_bundle_carries() -> None:
    # This is the half that was unguarded. The importer dispatches on the
    # plan's section names, so a section the plan names and the importer
    # does not read is a section that is planned, counted in `op_counts`,
    # and then silently dropped -- the user is told the import wrote their
    # resumes and their interview history was simply gone.
    read = _backend_read_sections()
    assert read, f"no sections were read out of {IMPORT_SERVICE}"
    assert sorted(read) == sorted(SECTIONS), (
        "the importer does not restore every section the bundle carries: "
        f"the importer reads {sorted(read)}, the bundle carries {sorted(SECTIONS)}"
    )


def test_the_backend_reads_the_rows_of_every_section_it_plans() -> None:
    # Two reads per section: the plan's ops (`sections.get`) and the
    # bundle's rows (`data.get`). A section whose ops are read but whose
    # rows are not is a section the importer counts as applied and writes
    # nothing for -- it reads the row it was told to write, finds none, and
    # records a skip.
    planned = _backend_read_sections()
    rows = _backend_read_rows()
    assert rows, f"no rows were read out of {IMPORT_SERVICE}"
    assert sorted(planned) == sorted(rows), (
        "the importer reads the plan's ops for some sections and not the "
        f"bundle's rows for them: ops for {sorted(planned)}, rows for {sorted(rows)}"
    )


def test_the_backend_reads_no_section_twice() -> None:
    read = _backend_read_sections()
    assert len(read) == len(set(read)), f"the importer reads a section twice: {read}"


def test_the_required_sections_follow_the_schema_version() -> None:
    # A 1.0.0 bundle is still a valid bundle -- it just does not carry the
    # backend's sections -- so the required set is read off the version the
    # bundle says it has, not assumed.
    assert required_sections(SCHEMA_VERSION) == SECTIONS
    assert required_sections("1.0.0") == AI_SECTIONS
    assert set(AI_SECTIONS) < set(SECTIONS)


@pytest.mark.parametrize("version", ["1.1.0", "2.0.0", "not-a-version"])
def test_an_unknown_or_newer_version_carries_everything(version: str) -> None:
    # The version comparison is a string comparison, so a future version
    # ("1.2.0", "2.0.0") is read as newer and gets the full set -- and a
    # version nobody wrote is read as older, which would silently drop the
    # backend's sections from a bundle that is meant to have them.
    assert required_sections(version) == SECTIONS
