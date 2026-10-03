"""The knowledge-notes surface: the app can neither write it nor read it, and the palette promises it.

Three shipped tables make the claim, and one walk reads each of them. `endpoints.knowledgeNotes` names
the route, `KnowledgeController` binds it four ways, and `SEARCH_GROUPS` links a "Notes" hit to
`/knowledge`. Walking the first two through the client gives two exported hooks -- `useKnowledgeNotes`
and `useNoteMutations` -- and walking those gives no call site, so no screen can list a note, create
one, edit one or delete one. Walking the entity gives one writer, `KnowledgeService.createNote`, which
sits behind the POST no client calls, and no seed, migration or Python path writes the table: the only
thing in this repository that ever posts a note is `DomainApiIT`.

The promise is still on screen. `command-palette.tsx` renders `Search {searchGroupNames()} once the API
is live.` -- a sentence built from that same table -- and the notes row's `href` is the constant
`/knowledge`, the screen whose one data hook is the sources list. So a note hit would link to a board
that cannot show it, and today the group is empty because nothing in the product can fill it.

Nothing here is a fix. These gates hold the shape still: closing the loop needs a notes reader in a
screen, or a writer, or the group out of the table and its label out of the sentence -- and the last
case prints which of the three has happened, because it re-derives all three from the walks.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/knowledge/web/KnowledgeController.java"
KNOWLEDGE_PAGE = "frontend/src/app/(app)/knowledge/page.tsx"
RESOURCES = "frontend/src/lib/hooks/resources.ts"
ACTIONS = "frontend/src/lib/hooks/actions.ts"
NORMALIZE = "frontend/src/lib/api/normalize.ts"
PALETTE = "frontend/src/components/common/command-palette.tsx"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"
NOTE_ROUTE = "/knowledge/notes"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


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


def test_the_notes_route_has_two_client_hooks_and_neither_has_a_call_site() -> None:
    """`GET/POST/PATCH/DELETE /knowledge/notes` are served, and no screen reaches them."""
    routes = re.findall(r'@(Get|Post|Patch|Delete)Mapping\("(/notes[^"]*)"\)', read(CONTROLLER))
    assert sorted(v.upper() for v, _ in routes) == ["DELETE", "GET", "PATCH", "POST"], \
        f"the server no longer binds the four note verbs this gate assumes: {routes}"

    files = client_sources()
    assert len(files) > 40, f"the client census read almost nothing ({len(files)} files): the gate would prove absence by reading no source"
    hooks = hooks_using_note_route()
    assert set(hooks) == {"useKnowledgeNotes", "useNoteMutations"}, \
        f"the notes route now has a different set of client hooks: {hooks}"

    unreachable = {name: hook_call_sites(name) for name in hooks}
    assert all(not sites for sites in unreachable.values()), \
        f"a note hook gained a caller, so this file's dead-surface claim must be re-measured, not edited: " \
        f"{ {k: v for k, v in unreachable.items() if v} }"
    assert hooks["useKnowledgeNotes"] == RESOURCES and hooks["useNoteMutations"] == ACTIONS, \
        f"the two hooks moved off the files whose mappers the other cases read: {hooks}"


def test_the_only_writer_of_note_rows_is_behind_the_post_no_client_calls() -> None:
    """One `new UserNote(` in the shipped product, and no seed, migration or Python path writes the table."""
    writers = []
    for path in (ROOT / "backend" / "src" / "main").rglob("*.java"):
        if re.search(r"\bnew UserNote\(", path.read_text(encoding="utf-8", errors="replace")):
            writers.append(path.relative_to(ROOT).as_posix())
    assert writers == ["backend/src/main/java/com/careeros/knowledge/service/KnowledgeService.java"], \
        f"note rows now have another Java author, so the unreachable-writer claim needs re-measuring: {writers}"
    assert re.search(r"public NoteItem createNote", read(
        "backend/src/main/java/com/careeros/knowledge/service/KnowledgeService.java")), \
        "the one author is no longer reached through createNote, which is the route the client cannot call"

    sql = read("backend/src/main/resources/db/migration/V1__init_schema.sql")
    assert not re.search(r"INSERT INTO user_notes", sql), \
        "a migration now seeds note rows, so the palette's Notes group is no longer guaranteed empty"

    service = []
    walked = 0
    for sub in ("ai-service/app", "ai-service/ops", "scripts", "e2e"):
        for path in (ROOT / sub).rglob("*"):
            if path.is_dir() or path.suffix not in {".py", ".sql", ".yml", ".ts", ".mjs", ".sh"}:
                continue
            walked += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            if NOTE_ROUTE in text or "user_notes" in text:
                service.append(path.relative_to(ROOT).as_posix())
    assert walked > 30, f"the writer census read {walked} files, so its silence proves nothing"
    assert service == [], \
        f"a seed, script or e2e path now names the notes route or its table ({service}): the group may no longer be empty"


def test_the_only_thing_that_ever_posts_a_note_is_a_java_test() -> None:
    """Every file in the repository naming the route, counted as one walk -- including this gate."""
    sites = []
    skip_parts = {"node_modules", "__pycache__", "dist", "build", "target"}
    for path in ROOT.rglob("*"):
        if path.is_dir() or path.suffix not in {".java", ".py", ".ts", ".tsx", ".md", ".sql", ".yml"}:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if set(rel.split("/")) & skip_parts or any(part.startswith(".") for part in rel.split("/")):
            continue
        if NOTE_ROUTE in path.read_text(encoding="utf-8", errors="replace"):
            sites.append(rel)
    assert sites == [
        f"ai-service/tests/{Path(__file__).name}",
        "ai-service/tests/test_window_sizes_whose_callers_decide_them_ship.py",
        "backend/src/test/java/com/careeros/DomainApiIT.java",
        "backend/src/test/java/com/careeros/PagingApiIT.java",
        "backend/src/test/java/com/careeros/ratelimit/RateLimitFilterTest.java",
        "docs/API.md",
        "frontend/src/lib/api/endpoints.test.ts",
        "frontend/src/lib/api/endpoints.ts",
    ], f"a new speaker about the notes route appeared, or one stopped: {sites}"
    assert 'knowledgeNotes: "%s"' % NOTE_ROUTE in read(ENDPOINTS), \
        "the client's endpoint map no longer spells the route this census searched for, so its hits are not the client's"


def test_the_knowledge_screen_has_one_data_hook_and_it_is_the_sources_list() -> None:
    """`/knowledge` renders sources: the notes board it is linked to from the palette does not exist here."""
    text = read(KNOWLEDGE_PAGE)
    imported = re.findall(r'import \{([^}]*)\} from "@/lib/hooks/resources"', text)
    names = sorted(n.strip() for chunk in imported for n in chunk.split(",") if n.strip())
    assert names == ["useKnowledgeSources"], \
        f"/knowledge now pulls a different set of data hooks, so the screen the Notes group links to changed: {names}"
    assert "useKnowledgeNotes" not in text and NOTE_ROUTE not in text, \
        "the knowledge screen gained a notes reader, so the palette's Notes link is no longer a dead end"
    components = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "frontend" / "src" / "components" / "knowledge").rglob("*.tsx")
                        if re.search(r"\bKnowledgeNote\b|endpoints\.knowledgeNotes\b",
                                     p.read_text(encoding="utf-8", errors="replace")))
    assert components == [], f"a knowledge component reads notes, which this screen does not: {components}"


def test_the_group_table_links_notes_to_a_screen_that_cannot_render_a_note() -> None:
    """The notes row's `href` is a constant, so its destination is a screen, and that screen has one query."""
    rows = search_group_rows()
    assert [r["key"] for r in rows] == ["jobs", "companies", "resumes", "notes", "conversations", "applications"], \
        f"the group table's rows or order moved, so the palette's sentence names a different list: {[r['key'] for r in rows]}"
    notes = next(r for r in rows if r["key"] == "notes")
    assert notes["href_args"] == "" and notes["href_body"] == '"/knowledge"', \
        f"the notes row now links somewhere that carries an id ({notes['href_args']} => {notes['href_body']}): " \
        "re-read the destination screen before trusting the dead-end claim"
    assert not any(r["href_args"] == "" and r["href_body"] == '"/knowledge"' for r in rows if r["key"] != "notes"), \
        "another group also links to /knowledge, so the screen's single query now serves two kinds"

    page = read(KNOWLEDGE_PAGE)
    assert re.findall(r'import \{([^}]*)\} from "@/lib/hooks/resources"', page), \
        "the destination screen stopped importing its data hook, so this gate can no longer say what it renders"


def test_the_palette_sentence_is_built_from_that_table_and_names_the_unreachable_group() -> None:
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
    assert "Search {searchGroupNames()} once the API is live." in footer, \
        "the palette footer no longer interpolates the table, so its capability line is a typed string and this gate is stale"
    assert "Content search isn't available yet" in footer.replace("&apos;", "'"), \
        "the palette lost its failure line, so the sentence is the only copy a user gets about content search"

    hooks = hooks_using_note_route()
    assert all(not hook_call_sites(name) for name in hooks), \
        "a notes hook became reachable, so the group the sentence names may no longer be the unreachable one"


def test_the_note_mutations_invalidate_a_key_no_reachable_query_declares() -> None:
    """`["knowledge","notes"]` is invalidated by a hook nobody calls, over a key nobody subscribes to."""
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
        f"the notes key is now subscribed by {subscriber}: gate its screen before calling the invalidation pointless"
    assert not hook_call_sites("useKnowledgeNotes"), \
        "useKnowledgeNotes gained a caller, so the invalidation now refreshes something on screen"

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


def test_the_surface_closes_one_of_three_ways_and_today_none_of_the_two_ends_exists() -> None:
    """reader / writer / promise: exactly one of the three is true, and it is the promise."""
    reader = bool(hook_call_sites("useKnowledgeNotes"))
    writer = bool(hook_call_sites("useNoteMutations"))
    promise = "notes" in [r["label"].lower() for r in search_group_rows()]

    assert (reader, writer, promise) == (False, False, True), \
        f"the notes surface changed shape (reader={reader}, writer={writer}, promise={promise}). " \
        "The three ways to close it are: give a screen a notes reader, give one a notes writer, or drop the " \
        "row from SEARCH_GROUPS so the palette stops naming the group. Update this file to say which happened."
