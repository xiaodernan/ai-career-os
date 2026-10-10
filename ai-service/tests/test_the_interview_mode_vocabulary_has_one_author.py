"""The mock-interview mode vocabulary: one table on the service, one list on the client, one default per plane.

A candidate picks a mode from a menu, the backend stores the string on the session row, and the
ai-service looks it up in `_INTERVIEWER_PERSONA` to decide who asks the questions. That chain has
had four spellings of the same seven words: the persona table, a `MODES` list next to it that
nothing in the service read, the client's `@/lib/interview-modes`, and a hand copy of that list
inside the job page -- the two menus send the same field and could therefore offer different
interviews. The `MODES` list is gone: the persona table's keys ARE the vocabulary, because they
are the only copy the engine reads.

The relationship worth a gate is the silent one. `opening_question` and `advance` both look the
persona up with `.get(mode, _INTERVIEWER_PERSONA["mixed"])`, so a mode that exists in one author
and not the other does not fail -- it runs the default interview. Someone could add a menu entry,
watch it save, watch the session open, and see nothing wrong. So every clause below is stated
against the persona table read from the module itself: the client's list must be exactly that
table minus the mode the engine falls back to, the table's personas must all differ so a pick
always changes the interview, and the three defaults (the Java entity's column, the Python
fallback, the client
mapper's `??`) must name the same mode, because a session started through one path and read
through another should still say what kind of interview it was.

"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MODULE = "frontend/src/lib/interview-modes.ts"
MODULE_TEST = "frontend/src/lib/interview-modes.test.ts"
INTERVIEWS_PAGE = "frontend/src/app/(app)/interviews/page.tsx"
JOB_PAGE = "frontend/src/app/(app)/jobs/[id]/page.tsx"
FEATURE_PY = "ai-service/app/features/interview.py"
JAVA_SESSION = "backend/src/main/java/com/careeros/interview/entity/InterviewSession.java"
JAVA_DTO = "backend/src/main/java/com/careeros/interview/dto/InterviewDtos.java"
RESOURCES_TS = "frontend/src/lib/hooks/resources.ts"

SPECIFIER = "@/lib/interview-modes"

# The engine's own fail-open, read as an expression so the default's name is never typed here.
FALLBACK = re.compile(r'_INTERVIEWER_PERSONA\.get\(mode, _INTERVIEWER_PERSONA\["([a-z_]+)"\]\)')
CLIENT_VALUE = re.compile(r'\{\s*value:\s*"([a-z_]+)"')
DECLARATION = re.compile(r"^(?:export\s+)?const INTERVIEW_MODES\s*=\s*\[", re.M)
READER = re.compile(r'^import\s+(?:type\s+)?\{[^{}]*\bINTERVIEW_MODES\b[^{}]*\}\s+from\s+"'
                    + re.escape(SPECIFIER) + r'"', re.M | re.S)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def persona_table() -> dict[str, str]:
    from app.features import interview
    return dict(interview._INTERVIEWER_PERSONA)


def fallback_sites() -> list[str]:
    """Every place the engine says "a mode I do not have becomes this one"."""
    return FALLBACK.findall(read(FEATURE_PY))


def client_modes() -> list[str]:
    src = read(MODULE)
    body = src[src.index("INTERVIEW_MODES"):]
    return CLIENT_VALUE.findall(body[: body.index("];")])


@lru_cache(maxsize=1)
def client_files() -> list[str]:
    return sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "frontend" / "src").rglob("*.ts*")
                  if not p.is_dir() and ".test." not in p.name)


def one(regex: re.Pattern, rel: str, what: str) -> str:
    hits = regex.findall(read(rel))
    assert len(hits) == 1, f"{rel} no longer states {what} exactly once: {hits}"
    return hits[0]


def test_every_mode_the_service_names_gets_a_persona_that_is_not_the_fallback() -> None:
    table = persona_table()
    sites = fallback_sites()
    assert len(set(sites)) == 1, (
        f"the engine's fallback personas disagree ({sorted(set(sites))} across {len(sites)} sites), "
        "so `the mode a session defaults to` is not one answer")
    default = sites[0]
    assert default in table, (
        f"the engine falls back to {default!r}, which its own persona table does not name, so every "
        "unlisted mode -- including the documented default -- runs an unlisted persona")
    assert len({*table.values()}) == len(table), (
        f"two modes share one persona in {FEATURE_PY}, so a candidate's pick stops changing the "
        "interview they get -- and one of them has stopped being the default's")


def test_the_unlisted_mode_really_does_run_the_default_interview() -> None:
    """The fail-open is why the clause above exists; if it stops failing open, this gate moves."""
    sites = fallback_sites()
    assert len(sites) >= 2, (
        f"only {len(sites)} site(s) in {FEATURE_PY} still fall back to a default persona, so the "
        "count the vocabulary clause is pinned against has changed shape")
    table, default = persona_table(), sites[0]
    assert default in table, (
        f"the engine falls back to {default!r} but its own table has no persona under that key, so "
        "the clause below would be comparing against a persona that does not exist")
    runs = table.get("no_such_mode", table[default])
    assert runs == table[default], (
        f"an unlisted mode no longer takes the {default!r} persona, so the silent-substitution this "
        "gate exists to prevent is gone and the guard should be re-aimed, not left asserting a "
        "behaviour the engine abandoned")


def test_the_client_picks_every_mode_except_the_one_the_service_defaults_to() -> None:
    table, default = persona_table(), fallback_sites()[0]
    assert sorted(client_modes()) == sorted(k for k in table if k != default), (
        f"{MODULE} offers {sorted(client_modes())} while {FEATURE_PY} speaks "
        f"{sorted(table)} less its own default {default!r}: a menu entry the table lacks runs the "
        "default interview, and a table entry no menu offers is unreachable from the app")


def test_the_service_names_its_vocabulary_in_one_place() -> None:
    """Each mode name appears once -- as the persona key -- plus once per fallback site for the default."""
    src, table = read(FEATURE_PY), persona_table()
    extra = len(fallback_sites())
    default = fallback_sites()[0]
    for mode in table:
        hits = src.count(f'"{mode}"')
        expected = 1 + (extra if mode == default else 0)
        assert hits == expected, (
            f'"{mode}" is spelled {hits} times in {FEATURE_PY}, not the {expected} a single author '
            "leaves (its key, and the fallback's copy for the default mode): a second enumeration "
            "of the mode list can drift from the personas nobody reads it against")


def test_the_client_list_has_one_author_and_the_two_menus_read_it() -> None:
    files = client_files()
    assert len(files) > 100, (
        f"the client walk read {len(files)} files, so finding one author proves nothing")
    authors = [rel for rel in files if DECLARATION.search(read(rel))]
    assert authors == [MODULE], (
        f"the mode list is declared in {authors}, not the one file {MODULE}: the two menus that "
        "send this field would then be free to offer different interviews")
    readers = sorted(rel for rel in files
                     if rel != MODULE and any(READER.finditer(read(rel))))
    assert readers == sorted([INTERVIEWS_PAGE, JOB_PAGE]), (
        f"{SPECIFIER} is imported by {readers}, not the two menus that were meant to share it; "
        "a screen that stops importing it has grown its own list again")


def test_the_modes_the_client_sends_fit_the_backends_own_bound() -> None:
    bound = int(one(re.compile(r"@Size\(\s*max\s*=\s*(\d+)\s*\)\s+String mode"), JAVA_DTO,
                    "the ceiling on a mode string"))
    modes = client_modes()
    assert modes, (
        f"{MODULE} declares no mode values, so there is no longest mode to hold against the "
        f"backend's @Size(max = {bound}) -- the comparison below would not have run")
    longest = max(((len(value), value) for value in modes))
    assert longest[0] < bound, (
        f"the client's longest mode {longest[1]!r} is {longest[0]} characters against the backend's "
        f"own @Size(max = {bound}): the menu would offer a mode the request cannot carry, and the "
        "candidate would get the 400 instead of the interview")


def test_every_plane_defaults_to_the_same_mode() -> None:
    """Three planes choose a mode for a session nobody picked one for; they must choose the same."""
    java = one(re.compile(r'private String mode = "([a-z_]+)"'), JAVA_SESSION, "the column's default")
    client = one(re.compile(r'mode: str\([^)]*\)\s*\?\?\s*"([a-z_]+)"'), RESOURCES_TS,
                 "the mapper's default")
    table, python = persona_table(), fallback_sites()[0]
    assert java == client == python, (
        f"a session with no picked mode is {java!r} to the database, {python!r} to the engine and "
        f"{client!r} to the browser, so the same interview is reported as three different kinds")
    assert java in table, (
        f"the default {java!r} is not a mode the persona table names, so every default session "
        "silently runs the fallback persona instead of the one its own row claims")


def test_the_module_ships_with_a_test_that_reads_the_fields_both_menus_render() -> None:
    test = read(MODULE_TEST)
    assert "INTERVIEW_MODES" in test, f"{MODULE_TEST} no longer imports the list it is about"
    for field in ("value", "label", "hint"):
        assert f"mode.{field}" in test, (
            f"{MODULE_TEST} never names mode.{field}, so the menu that renders only {field} could "
            f"start printing nothing and this file would still be green")
    assert "new Set(" in test, (
        f"{MODULE_TEST} no longer checks the list for duplicates, so two modes could share one "
        "wire value and the menus would send an ambiguous field")
