"""The knowledge-notes surface: the reader and the writer mount, and the palette promise predates them.

This file used to pin the surface as dead -- two exported hooks with no call site, a palette sentence
naming a group no screen could fill. Both ends closed when the knowledge page grew a notes panel:
`components/knowledge/notes-panel.tsx` mounts `useKnowledgeNotes` (the reader, `GET /knowledge/notes`
through `normalizePage`) and `useNoteMutations` (the writer, POST/PATCH/DELETE through the same
route), so the `["knowledge","notes"]` invalidation in `actions.ts` refreshes a query a screen
subscribes to. The page itself still imports one data hook from `resources.ts` -- the sources list --
because the notes reader lives in the panel component, not in the page.

What did not move: the writer census. The only server-side author of a note row is still
`KnowledgeService.createNote`, behind the POST the client now calls; no seed, migration or Python
path writes the table. And the palette still builds its capability sentence from `SEARCH_GROUPS`, so
the "Notes" hit links to a screen that can finally render one.

These gates hold the new shape still: a second caller for either hook, a notes reader outside the
knowledge panel, a seed under the table, or the group leaving the table all have to cost an edit
here, because every one of them is re-derived from the walks below.

#231 re-aimed the two route censuses after two commits joined them without being explained --
`2c2ba5e`'s palette spec (which POSTs a note so the palette's search has a real row) and `aba55e8`'s
API-docs gate (which names the route to justify holding a combined-verb row to its paths). Reading
why the list grows found the reason it grows at all: the search asked for the route's *characters*,
and `/knowledge/notes` is also the first half of `components/knowledge/notes-panel.tsx`. Four of the
twenty speakers never mention the route; they name the panel that lives under it. So the census now
pins the character after the route, which keeps `/knowledge/notes`, `/knowledge/notes/{id}` and
`/api/v1/knowledge/notes` and drops `notes-panel.tsx`, and the four path coincidences are declared in
a ledger of their own. The writer census changed shape too: it used to answer "which files name the
route?", while its own message asked "is there a second writer?" -- a question of *verbs*. It now
counts each named file's operations, and separates a spec that POSTs to the collection (a second
caller of `createNote`, which the Java clause above proved is the route's handler) from a path that
names the `user_notes` table itself (a second author of the rows, which is the thing feared).

The verb scan reads literal `api.<verb>("<path>")` calls and nothing else. Its limit is stated rather
than re-checked: a note request whose path arrives from a variable or a shared helper disappears from
`writes` or `reads`, which is the same red a second writer would cost, so the equalities are the
warning and no separate clause is needed to say so.

Measured on the shapes the ledgers now hold: sixteen speakers, four path coincidences, three non-Java
speakers all in `e2e`, and four readable calls over them -- three POSTs to the collection and one GET.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from tests._repo_walk import walk_files

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/knowledge/web/KnowledgeController.java"
KNOWLEDGE_PAGE = "frontend/src/app/(app)/knowledge/page.tsx"
RESOURCES = "frontend/src/lib/hooks/resources.ts"
ACTIONS = "frontend/src/lib/hooks/actions.ts"
NORMALIZE = "frontend/src/lib/api/normalize.ts"
PALETTE = "frontend/src/components/common/command-palette.tsx"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"
NOTE_ROUTE = "/knowledge/notes"
NOTES_PANEL = "frontend/src/components/knowledge/notes-panel.tsx"

# The route, with the character after it pinned: `/knowledge/notes` is also the first half of
# `components/knowledge/notes-panel.tsx`, so a bare substring search reports a file naming the panel
# as one naming the route. This accepts the route bare, its `{id}` child and the `/api/v1` spelling,
# and rejects a hyphen or word character following it.
MENTION = re.compile(r"/knowledge/notes(?![\w-])")
# A literal `api.<verb>("<path>")` call. Deliberately narrow, and the writer census counts what it
# finds so the narrowness is a stated limit rather than a silent one.
NOTE_OP = re.compile(r"""\.(get|post|put|patch|delete)\(\s*["'`]([^"'`\n]*)["'`]""")

# Each speaker of the notes route, with the reason it speaks. A new speaker has to join this ledger,
# which is the point: the list is not a photograph of the repository, it is a claim about it.
SPEAKERS: dict[str, str] = {
    "ai-service/tests/test_knowledge_controller_request_contract.py":
        "pins the two client path spellings and the POST/PATCH bodies the route takes",
    f"ai-service/tests/{Path(__file__).name}":
        "a census that searches for a route has to name it",
    "ai-service/tests/test_the_api_docs_public_tables_are_the_controllers_own.py":
        "explains why API.md's combined row over the four note verbs is held to its paths, not its verbs",
    "ai-service/tests/test_the_data_model_names_columns_that_exist.py":
        "prose: the user_notes table is what serves GET /knowledge/notes, not a knowledge_sources row",
    "ai-service/tests/test_window_sizes_whose_callers_decide_them_ship.py":
        "pins the route's default window (20) against the caller that decides it",
    "backend/src/test/java/com/careeros/DomainApiIT.java":
        "drives create, read and a cross-user forbidden delete over the route",
    "backend/src/test/java/com/careeros/PagingApiIT.java":
        "pages the notes collection through the route",
    "backend/src/test/java/com/careeros/ratelimit/RateLimitFilterTest.java":
        "asserts the route carries no rate-limit rule",
    "docs/API.md":
        "the row advertising GET / POST / PATCH / DELETE over the route and its {id} child",
    "docs/architecture.md":
        "prose: the notes the panel reads come from GET /knowledge/notes",
    "e2e/tests/command-palette.spec.ts":
        "POSTs one note so the palette's server search has a real row to find",
    "e2e/tests/golden-journey.spec.ts":
        "polls GET to verify what the panel wrote through its own POST -- a reader, not a second writer",
    "e2e/tests/pagination.spec.ts":
        "POSTs the twenty-five rows a pager needs",
    NOTES_PANEL:
        "the panel's docstring spells the four verbs it calls",
    "frontend/src/lib/api/endpoints.test.ts":
        "pins the body keys the POST takes",
    "frontend/src/lib/api/endpoints.ts":
        "the client's own map: knowledgeNotes and the knowledgeNote(id) child",
}

# Files whose text contains the route's characters without mentioning the route, because the panel
# that renders notes lives at `components/knowledge/notes-panel.tsx`. Declared so the two ledgers
# reconcile exactly against the loose search: a file may not move from one to the other unnoticed.
PATH_COINCIDENCES: dict[str, str] = {
    "ai-service/tests/test_anonymous_mappers_producers_ship.py":
        "names the panel's path as useKnowledgeNotes' caller",
    "ai-service/tests/test_page_window_names_and_their_readers_ship.py":
        "names the panel's path in its caller table, six times",
    "ai-service/tests/test_the_knowledge_page_pages_both_of_its_lists.py":
        "names the panel's path as the caller of a page-window read",
    "frontend/src/app/(app)/knowledge/page.tsx":
        'imports the panel: "@/components/knowledge/notes-panel"',
}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def mentions_route(text: str) -> bool:
    """Whether the text speaks of the notes route itself, not of a path that merely starts with it."""
    return bool(MENTION.search(text))


@lru_cache(maxsize=1)
def client_sources() -> tuple[str, ...]:
    """The app's own sources: frontend/src, tests excluded -- a test naming a hook does not put it on screen."""
    found = []
    for path in (ROOT / "frontend" / "src").rglob("*"):
        if path.is_dir() or path.suffix not in {".ts", ".tsx"}:
            continue
        if ".test." in path.name:
            continue
        found.append(path.relative_to(ROOT).as_posix())
    return tuple(sorted(found))


def exported_bodies(text: str) -> dict[str, str]:
    """Every top-level `export function NAME(` in a TS file, mapped to the source up to the next export."""
    marks = [(m.group(1), m.start()) for m in re.finditer(r"^export function (\w+)\(", text, re.M)]
    return {name: text[start:(marks[i + 1][1] if i + 1 < len(marks) else len(text))]
            for i, (name, start) in enumerate(marks)}


def hook_call_sites(name: str) -> list[str]:
    """Files that reach for the hook -- a call or an import -- other than the file that declares it."""
    rx = re.compile(r"(?<![\w$.])%s(?![\w$])" % re.escape(name))
    declared = re.compile(r"^export function %s\(" % re.escape(name), re.M)
    return [rel for rel in client_sources()
            if rx.search(read(rel)) and not declared.search(read(rel))]


def hooks_using_note_route() -> dict[str, str]:
    """The exported client hooks whose own body names the notes endpoint, from one walk of the client."""
    rx = re.compile(r"endpoints\.knowledgeNotes\b|endpoints\.knowledgeNote\(")
    out: dict[str, str] = {}
    for rel in client_sources():
        text = read(rel)
        if not rx.search(text):
            continue
        for name, body in exported_bodies(text).items():
            if rx.search(body):
                out[name] = rel
    return out


def search_group_rows() -> list[dict[str, str]]:
    """The `SEARCH_GROUPS` table, read as rows: key, type, label and the href arrow's body."""
    text = read(NORMALIZE)
    start = text.index("export const SEARCH_GROUPS")
    opener = text.index("= [", start) + 2
    depth = 0
    for index in range(opener, len(text)):
        if text[index] == "[":
            depth += 1
        elif text[index] == "]":
            depth -= 1
            if depth == 0:
                break
    else:
        raise AssertionError("no closing ] for the SEARCH_GROUPS array -- the walk would read a prefix")
    rows = re.findall(r'\{ key: "(\w+)", type: "(\w+)", label: "(\w+)", href: \((.*?)\)\s*=>\s*(.*?)\s*\},?$',
                      text[opener:index], re.M)
    assert len(rows) >= 4, f"the group-table walk found only {len(rows)} rows: {rows}"
    return [dict(zip(("key", "type", "label", "href_args", "href_body"), row)) for row in rows]


def query_keys(rel: str) -> dict[str, list[tuple[str, str]]]:
    """Each exported hook's react-query keys, reduced to their first two literal segments.

    A shipped key is `["knowledge", "sources", live ? "live" : "once", documentId ?? null]`, so the
    prefix is the identity of the cache and the tail is its window.
    """
    out: dict[str, list[tuple[str, str]]] = {}
    for name, body in exported_bodies(read(rel)).items():
        keys = [tuple(re.findall(r'"([^"]+)"', k)[:2])
                for k in re.findall(r"queryKey: \[([^\]]+)\]", body)]
        keys = [k for k in keys if len(k) == 2]
        if keys:
            out[name] = keys
    return out


def test_the_notes_route_has_two_client_hooks_and_a_screen_reaches_both() -> None:
    """`GET/POST/PATCH/DELETE /knowledge/notes` are served, and the notes panel is the one caller."""
    routes = re.findall(r'@(Get|Post|Patch|Delete)Mapping\("(/notes[^"]*)"\)', read(CONTROLLER))
    assert sorted(v.upper() for v, _ in routes) == ["DELETE", "GET", "PATCH", "POST"], \
        f"the server no longer binds the four note verbs this gate assumes: {routes}"

    files = client_sources()
    assert len(files) > 40, f"the client census read almost nothing ({len(files)} files): the gate would prove reach by reading no source"
    hooks = hooks_using_note_route()
    assert set(hooks) == {"useKnowledgeNotes", "useNoteMutations"}, \
        f"the notes route now has a different set of client hooks: {hooks}"

    callers = {name: hook_call_sites(name) for name in hooks}
    assert all(sites == [NOTES_PANEL] for sites in callers.values()), \
        f"the notes hooks gained or lost a caller, so this file's reach claim must be re-measured: {callers}"
    assert hooks["useKnowledgeNotes"] == RESOURCES and hooks["useNoteMutations"] == ACTIONS, \
        f"the two hooks moved off the files whose mappers the other cases read: {hooks}"


def test_the_only_writer_of_note_rows_is_behind_the_post_the_client_calls() -> None:
    """One `new UserNote(` in the shipped product, and no seed, migration or Python path writes the table."""
    writers = []
    for path in (ROOT / "backend" / "src" / "main").rglob("*.java"):
        if re.search(r"\bnew UserNote\(", path.read_text(encoding="utf-8", errors="replace")):
            writers.append(path.relative_to(ROOT).as_posix())
    assert writers == ["backend/src/main/java/com/careeros/knowledge/service/KnowledgeService.java"], \
        f"note rows now have another Java author, so the single-writer claim needs re-measuring: {writers}"
    assert re.search(r"public NoteItem createNote", read(
        "backend/src/main/java/com/careeros/knowledge/service/KnowledgeService.java")), \
        "the one author is no longer reached through createNote, which is the route the panel writes through"

    sql = read("backend/src/main/resources/db/migration/V1__init_schema.sql")
    assert not re.search(r"INSERT INTO user_notes", sql), \
        "a migration now seeds note rows, so the client no longer authors everything on screen"

    route_speakers: list[str] = []
    table_speakers: list[str] = []
    operations: dict[str, list[tuple[str, str]]] = {}
    walked = 0
    for sub in ("ai-service/app", "ai-service/ops", "scripts", "e2e"):
        # `e2e` carries its own `node_modules`; rglob would walk it to discard every file.
        for path in walk_files(ROOT / sub):
            if path.suffix not in {".py", ".sql", ".yml", ".ts", ".mjs", ".sh"}:
                continue
            walked += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            rel = path.relative_to(ROOT).as_posix()
            if "user_notes" in text:
                table_speakers.append(rel)
            if mentions_route(text):
                route_speakers.append(rel)
                found = sorted((verb, target) for verb, target in NOTE_OP.findall(text)
                               if NOTE_ROUTE in target)
                if found:
                    operations[rel] = found
    assert walked > 30, f"the writer census read {walked} files, so its silence proves nothing"

    # Naming the TABLE from outside the Java service would write rows around the entity layer, which
    # is the second author this test's title forbids. Nothing does: all three specs reach the route
    # with a verb, so every row they create is made by the handler the clauses above pinned to
    # `createNote` -- a spec that seeds is a second caller of one author, not a second author.
    assert table_speakers == [], (
        f"a path outside the Java service names the notes table itself ({table_speakers}): that is a second "
        "author of note rows, not a caller of the one the route serves")
    assert route_speakers == ["e2e/tests/command-palette.spec.ts",
                              "e2e/tests/golden-journey.spec.ts",
                              "e2e/tests/pagination.spec.ts"], (
        f"the notes route now has a different set of non-Java speakers ({route_speakers}): read each one's "
        "verbs before this gate claims again that one handler authors every row")

    writes = {rel: [op for op in ops if op[0] != "get"] for rel, ops in operations.items()}
    writes = {rel: ops for rel, ops in writes.items() if ops}
    reads = {rel: [target for verb, target in ops if verb == "get"] for rel, ops in operations.items()}
    reads = {rel: paths for rel, paths in reads.items() if paths}
    assert writes == {
        "e2e/tests/command-palette.spec.ts": [("post", NOTE_ROUTE)],
        "e2e/tests/pagination.spec.ts": [("post", NOTE_ROUTE), ("post", NOTE_ROUTE)],
    }, (f"a note row is now authored by a path that is not the collection POST ({writes}): the panel writes "
        "through POST /knowledge/notes, and that is the only verb the Java clause above accounts for")
    assert reads == {"e2e/tests/golden-journey.spec.ts": [NOTE_ROUTE]}, \
        f"the route's readers changed shape: {reads}"
    # No separate "a speaker the verb scan cannot see" clause: the two equalities above already hold
    # every one of the three names, so a file that lost its only readable call has lost its entry in
    # `writes` or `reads` and reddens there first. The scan's limit is real -- a path built from a
    # variable is invisible -- but it lands as a vanished writer, which is the message to read.


def test_the_files_that_speak_of_the_notes_route() -> None:
    """Every file naming the route, and every file naming only a path that starts with it -- one walk."""
    sites: list[str] = []
    loose_sites: list[str] = []
    skip_parts = {"node_modules", "__pycache__", "dist", "build", "target"}
    # Pruning walk: `ROOT.rglob("*")` traverses 107k entries from here, 81k of them under
    # `frontend/node_modules`, which the `skip_parts` guard below throws away by name.
    for path in walk_files(ROOT, skip_parts):
        if path.suffix not in {".java", ".py", ".ts", ".tsx", ".md", ".sql", ".yml"}:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if set(rel.split("/")) & skip_parts or any(part.startswith(".") for part in rel.split("/")):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if NOTE_ROUTE not in text:
            continue
        loose_sites.append(rel)
        if mentions_route(text):
            sites.append(rel)
    # The controller that SERVES the route is not among the speakers, because it spells the path in two
    # pieces (`@RequestMapping("/api/v1/knowledge")` plus `@GetMapping("/notes")`); the first test in
    # this file is what holds those four verbs, and a route rename there reddens it, not this list.
    unexplained = sorted(set(sites) - set(SPEAKERS))
    silent = sorted(set(SPEAKERS) - set(sites))
    assert sites == sorted(SPEAKERS), (
        f"speakers with no reason recorded: {unexplained}; reasons whose speaker went silent: {silent}. "
        "A speaker is a claim about the route, so give it a reason in SPEAKERS or make it stop speaking")
    extra = sorted(set(loose_sites) - set(sites) - set(PATH_COINCIDENCES))
    stale = sorted(set(PATH_COINCIDENCES) - set(loose_sites))
    assert sorted(set(SPEAKERS) | set(PATH_COINCIDENCES)) == loose_sites, (
        f"the loose substring search and the two ledgers disagree: {extra} contain the route's characters "
        f"without being declared a speaker or a path coincidence, and {stale} no longer contain them")
    assert not set(SPEAKERS) & set(PATH_COINCIDENCES), (
        f"a file cannot both speak of the route and only carry its characters in a path: "
        f"{sorted(set(SPEAKERS) & set(PATH_COINCIDENCES))}")
    assert len(PATH_COINCIDENCES) == 4, (
        f"the panel-path coincidence ledger holds {len(PATH_COINCIDENCES)} files; it exists to prove the "
        "boundary rule removes exactly the four that name notes-panel.tsx and nothing else")
    assert 'knowledgeNotes: "%s"' % NOTE_ROUTE in read(ENDPOINTS), \
        "the client's endpoint map no longer spells the route this census searched for, so its hits are not the client's"


def test_the_knowledge_screen_keeps_one_page_hook_and_the_notes_reader_lives_in_the_panel() -> None:
    """`/knowledge` renders sources through the page and notes through the panel component."""
    text = read(KNOWLEDGE_PAGE)
    imported = re.findall(r'import \{([^}]*)\} from "@/lib/hooks/resources"', text)
    names = sorted(n.strip() for chunk in imported for n in chunk.split(",") if n.strip())
    assert names == ["useKnowledgeSources"], \
        f"/knowledge now pulls a different set of data hooks into the page, so the screen's shape changed: {names}"
    # The page's one note-route mention is the panel import itself -- "components/knowledge/notes-panel"
    # contains "/knowledge/notes" as a substring -- so the route check runs on the page minus imports.
    without_imports = "\n".join(line for line in text.splitlines() if not line.startswith("import "))
    assert "useKnowledgeNotes" not in text and NOTE_ROUTE not in without_imports, \
        "the knowledge page itself gained a notes reader; the split this file pins (page = sources, panel = notes) is gone"

    components = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "frontend" / "src" / "components" / "knowledge").rglob("*.tsx")
                        if re.search(r"\bKnowledgeNote\b|endpoints\.knowledgeNotes\b",
                                     p.read_text(encoding="utf-8", errors="replace")))
    assert components == [NOTES_PANEL], \
        f"the notes reader moved or gained a sibling knowledge component: {components}"


def test_the_group_table_links_notes_to_the_screen_that_now_renders_them() -> None:
    """The notes row's `href` is a constant, so its destination is a screen, and that screen renders notes."""
    rows = search_group_rows()
    assert [r["key"] for r in rows] == ["jobs", "companies", "resumes", "notes", "conversations", "applications"], \
        f"the group table's rows or order moved, so the palette's sentence names a different list: {[r['key'] for r in rows]}"
    notes = next(r for r in rows if r["key"] == "notes")
    assert notes["href_args"] == "" and notes["href_body"] == '"/knowledge"', \
        f"the notes row now links somewhere that carries an id ({notes['href_args']} => {notes['href_body']}): " \
        "re-read the destination screen before trusting the reach claim"
    assert not any(r["href_args"] == "" and r["href_body"] == '"/knowledge"' for r in rows if r["key"] != "notes"), \
        "another group also links to /knowledge, so the screen's sources query now serves two kinds"

    page = read(KNOWLEDGE_PAGE)
    assert re.findall(r'import \{([^}]*)\} from "@/lib/hooks/resources"', page), \
        "the destination screen stopped importing its data hook, so this gate can no longer say what it renders"
    assert "NotesPanel" in page, "the destination screen stopped rendering the notes panel the link lands on"


def test_the_palette_sentence_is_built_from_that_table_and_the_notes_group_is_backed_now() -> None:
    """`searchGroupNames()` is the footer's subject: the sentence on screen is the table, not a typed string."""
    labels = [r["label"].lower() for r in search_group_rows()]
    sentence = ", ".join(labels[:-1]) + f" and {labels[-1]}"
    assert sentence == "jobs, companies, resumes, notes, conversations and applications", \
        f"the capability line the footer prints changed: {sentence}"
    assert "notes" in labels, f"the palette stopped promising notes: {labels}"

    derived = read(NORMALIZE)
    body = derived[derived.index("export function searchGroupNames"):]
    body = body[:body.index("\n}")]
    assert 'g.label.toLowerCase()' in body and 'names.join(", ")' in body, \
        f"searchGroupNames no longer builds the sentence from the table, so pinning the footer against the table proves nothing:\n{body}"

    footer = read(PALETTE)
    # The footer's tail reads from the locale table now, so the gate asserts
    # the key the palette reads rather than the English copy it carried.
    assert "Search {searchGroupNames()} — {t(\"chrome.resultsStreamIn\")}" in footer, \
        "the palette footer no longer interpolates the table, so its capability line is a typed string and this gate is stale"
    assert "once the API is live" not in footer, \
        "the footer went back to promising a future for an endpoint SearchController has answered for a while"
    assert 't("chrome.searchFailed")' in footer, \
        "the palette lost its failure line, so the sentence is the only copy a user gets about content search"
    assert "results.refetch()" in footer, \
        "the failure line no longer offers the retry the client's backoff hands every other reader"

    hooks = hooks_using_note_route()
    assert all(hook_call_sites(name) for name in hooks), \
        "a notes hook lost its caller, so the group the sentence names went back to being a promise"


def test_the_note_mutations_invalidate_a_key_the_mounted_query_subscribes_to() -> None:
    """`["knowledge","notes"]` is invalidated by a hook the panel calls, over a key the panel reads."""
    keys = query_keys(ACTIONS)
    assert "useNoteMutations" in keys, f"the note actions are no longer an exported hook this walk reads: {sorted(keys)}"
    invalidated = [k for name, ks in keys.items() for k in ks if name == "useNoteMutations"]
    assert ("knowledge", "notes") in invalidated, \
        f"the note mutations stopped invalidating the notes key, so the subscriber question changed shape: {invalidated}"

    readers = query_keys(RESOURCES)
    declared = {k for ks in readers.values() for k in ks}
    assert ("knowledge", "notes") in declared, \
        f"no hook declares the notes key the mutations invalidate: {sorted(declared)}"
    subscriber = [name for name, ks in readers.items() if ("knowledge", "notes") in ks]
    assert subscriber == ["useKnowledgeNotes"], \
        f"the notes key is now subscribed by {subscriber}: re-read which query the invalidation refreshes"
    assert hook_call_sites("useKnowledgeNotes"), \
        "useKnowledgeNotes lost its caller, so the invalidation refreshes an empty set again"

    control = [name for name, ks in readers.items() if ("knowledge", "sources") in ks]
    assert control == ["useKnowledgeSources"] and hook_call_sites("useKnowledgeSources"), \
        f"the walk cannot tell a live key from a dead one (sources control: {control}): it would call any invalidation pointless"


def test_the_word_notes_in_the_app_belongs_to_two_tables_and_only_one_is_the_group() -> None:
    """`application-dialog.tsx` has a Notes field; it is `applications.notes`, not the notes route."""
    dialog = read("frontend/src/components/applications/application-dialog.tsx")
    assert 'field("notes"' in dialog, \
        "the applications editor lost its notes field, so this anti-conflation control no longer has anything to name"
    assert NOTE_ROUTE not in dialog and "knowledgeNotes" not in dialog, \
        "the applications editor now reaches the knowledge notes route, so the two `notes` namespaces merged and every claim above needs re-reading"
    assert re.search(r'notes: list<string>\(raw, "notes"\)', read(NORMALIZE)), \
        "normalize.ts no longer reads a `notes` list from some other payload: if the second namespace went away, say so here"


def test_the_surface_closed_through_the_reader_and_the_writer() -> None:
    """reader / writer / promise: the first two went true together; the promise was always there."""
    reader = bool(hook_call_sites("useKnowledgeNotes"))
    writer = bool(hook_call_sites("useNoteMutations"))
    promise = "notes" in [r["label"].lower() for r in search_group_rows()]

    assert (reader, writer, promise) == (True, True, True), \
        f"the notes surface changed shape (reader={reader}, writer={writer}, promise={promise}). " \
        "The reader and the writer mounted together in the knowledge page's notes panel; if either went " \
        "false, the palette's Notes group is a dead end again and this file has to say which end broke."
