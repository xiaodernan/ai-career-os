"""The export bundle's sections, read across the three services that touch it.

The bundle is the one artifact this product hands a user to take somewhere
else, and it is written in three places: the ai-service writes it, the
backend reads the applications and the growth runs and hands them over, and
the browser reads it back to redact a section and to restore one.

The sections are named in each of those places, and the names are the
contract. Nothing about a bundle is more fragile than its section list: a
section the writer adds and the reader does not know about is a section
the reader cannot redact -- so the export carries the user's pipeline and
the redaction silently leaves it in -- and a section the reader knows and
the writer does not write is a section the reader promises to redact and
the bundle never had.

There is no parser here and no schema to read, because there is no
schema: the sections are a tuple of names in one file and a list of keys
in another. So the gate reads both -- the ai-service's own tuple, and the
browser's own list -- and holds them to the same set. A section added on
one side and not the other fails here rather than in a user's export.

The browser's list is read from the page that offers the redaction
checkboxes (`app/(app)/data/page.tsx`), because that is the list that
decides what a reader can leave out.
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

# The browser's redaction list: `{ key: "profile", labelKey: "data.sections.profile" }`.
# The `key` is the section's name in the bundle; the label is the reader's.
_SECTION_KEY = re.compile(r'\{\s*key:\s*"([a-z_]+)"\s*,\s*labelKey:\s*"data\.sections\.')


def _frontend_sections() -> list[str]:
    """The section names the browser offers to redact."""
    source = FRONTEND_DATA_PAGE.read_text(encoding="utf-8")
    # Only the SECTIONS table, not the strings that happen to match elsewhere.
    start = source.index("const SECTIONS")
    end = source.index("] as const;", start)
    return _SECTION_KEY.findall(source[start:end])


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
