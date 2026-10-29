"""The Knowledge controller request: three endpoints, their DTOs, and what the browser sends.

KnowledgeController has three entry points with typed JSON request bodies:

1. ``POST /knowledge/notes`` and 2. ``PATCH /knowledge/notes/{id}`` -- create and update a
   note. Both bind the *same* ``NoteRequest(title, content, tags)`` where ``content`` is
   required (``@NotBlank``) and ``title`` is capped at 200 chars (``@Size(max = 200)``).
   The frontend calls these through ``useNoteMutations`` in ``actions.ts``: create posts the
   body whole to the collection route, update sends ``{ title, content }`` to the item route.

3. ``POST /knowledge/text`` -- ingest free text. Binds
   ``TextIngestRequest(title, text, kind, refId)`` where ``text`` and ``kind`` are required
   (``@NotBlank``). The frontend calls this through ``useIngestText``, which sends
   ``{ title, text, kind }`` and defaults ``kind`` to ``"note"`` -- a value that must stay in
   ``KnowledgeService``'s ``KINDS`` whitelist, or every defaulted ingest is rejected with
   "Unknown knowledge kind".

``POST /knowledge/documents`` binds a ``MultipartFile`` rather than a JSON DTO, so it is not
included in this gate.

This gate holds the contract at both ends:

- Each DTO declares exactly the expected field names (no extra fields silently accepted).
- Every call site in the app sends exactly those names.
- The ``@NotBlank`` guards are armed on ``content`` (NoteRequest) and ``text``/``kind``
  (TextIngestRequest).
- ``NoteRequest`` is still bound by *both* note endpoints -- the create and the update must
  not drift onto different request shapes.
- The ``kind`` the hook sends by default is a value the backend accepts.
- The mutation failure paths are announced via ``fail()``.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/knowledge/web/KnowledgeController.java"
DTOS = "backend/src/main/java/com/careeros/knowledge/dto/KnowledgeDtos.java"
SERVICE = "backend/src/main/java/com/careeros/knowledge/service/KnowledgeService.java"
ACTIONS = "frontend/src/lib/hooks/actions.ts"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


# --------------------------------------------------------------------------- helpers

@lru_cache(maxsize=1)
def dto_source() -> str:
    return read(DTOS)


@lru_cache(maxsize=1)
def controller_source() -> str:
    return read(CONTROLLER)


@lru_cache(maxsize=1)
def service_source() -> str:
    return read(SERVICE)


@lru_cache(maxsize=1)
def actions_source() -> str:
    return read(ACTIONS)


def record_body(record_name: str, source: str) -> str:
    """Return the raw text between ``record Name(`` and ``) {``, or "" if absent."""
    m = re.search(r"record\s+" + record_name + r"\s*\((.*?)\)\s*\{", source, re.DOTALL)
    return m.group(1) if m else ""


def java_record_fields(record_name: str, source: str) -> list[str]:
    """Return the field names declared inside ``record RecordName(...)`` in Java source.

    Annotations are stripped first (``@JsonAlias("ref_id")``, ``@Size(max = 200)``, ...),
    then generics (``List<String>`` -> ``List``), so the remaining commas are field
    separators even when several fields share a line.
    """
    body = record_body(record_name, source)
    if not body:
        return []
    cleaned = re.sub(r"@[\w.]+\s*(?:\{[^}]*\}|\([^)]*\))?\s*", "", body)
    cleaned = re.sub(r"<[^>]*>", "", cleaned)
    cleaned = cleaned.replace("\n", " ")
    fields = []
    for part in cleaned.split(","):
        part = part.strip()
        if not part or part.startswith("//"):
            continue
        tokens = part.split()
        if tokens:
            fields.append(tokens[-1])
    return fields


def ts_call_bodies(fn_name: str, source: str) -> list[str]:
    """Return the text of every top-level ``export function fn_name(...) { ... }`` block."""
    blocks = []
    for m in re.finditer(r"export function\s+" + fn_name + r"\s*\([^)]*\)\s*\{", source):
        start = m.end() - 1  # position of the opening brace
        depth = 0
        i = start
        while i < len(source):
            ch = source[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(source[start:i + 1])
                    break
            i += 1
    return blocks


# --------------------------------------------------------------------------- case 1: NoteRequest has three fields

def test_the_note_request_dto_declares_three_names():
    fields = java_record_fields("NoteRequest", dto_source())
    assert sorted(fields) == ["content", "tags", "title"], (
        "NoteRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 2: TextIngestRequest has four fields

def test_the_text_ingest_request_dto_declares_four_names():
    fields = java_record_fields("TextIngestRequest", dto_source())
    assert sorted(fields) == ["kind", "refId", "text", "title"], (
        "TextIngestRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 3: both note routes bind NoteRequest, ingest binds its own

def test_the_controller_binds_note_request_on_both_routes_and_ingest_once():
    src = controller_source()
    note_bindings = src.count("@RequestBody @Valid NoteRequest")
    assert note_bindings == 2, (
        "expected both POST /notes and PATCH /notes/{id} to bind @Valid NoteRequest, "
        "found %d binding(s)" % note_bindings
    )
    ingest_bindings = src.count("@RequestBody @Valid TextIngestRequest")
    assert ingest_bindings == 1, (
        "expected exactly one @Valid TextIngestRequest binding, found %d" % ingest_bindings
    )


# --------------------------------------------------------------------------- case 4: content is guarded

def test_the_note_content_field_is_guarded_by_notblank():
    body = record_body("NoteRequest", dto_source())
    assert body, "NoteRequest record not found"
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"\bcontent\b", line):
            context = (lines[i - 1] + "\n" + line) if i > 0 else line
            assert "@NotBlank" in context, (
                "content field lost its @NotBlank guard:\n%s" % context
            )
            break
    else:
        assert False, "content field not found in NoteRequest"


# --------------------------------------------------------------------------- case 5: text and kind are guarded

def test_the_ingest_text_and_kind_fields_are_guarded_by_notblank():
    body = record_body("TextIngestRequest", dto_source())
    assert body, "TextIngestRequest record not found"
    lines = body.splitlines()
    guarded: dict[str, bool] = {}
    for i, line in enumerate(lines):
        for field in ("text", "kind"):
            if re.search(r"\b" + field + r"\b", line):
                context = (lines[i - 1] + "\n" + line) if i > 0 else line
                guarded[field] = "@NotBlank" in context
    assert guarded == {"text": True, "kind": True}, (
        "expected @NotBlank on both text and kind in TextIngestRequest, measured: %s"
        % guarded
    )


# --------------------------------------------------------------------------- case 6: useIngestText sends its three fields and a valid kind

def test_use_ingest_text_sends_title_text_and_a_default_kind_the_backend_accepts():
    bodies = ts_call_bodies("useIngestText", actions_source())
    assert len(bodies) == 1, "expected exactly one useIngestText, found %d" % len(bodies)
    body = bodies[0]
    assert "endpoints.knowledgeText" in body, (
        "useIngestText no longer posts to endpoints.knowledgeText"
    )
    assert '"POST"' in body, "useIngestText no longer sends POST"
    assert "title: body.title" in body, "useIngestText no longer sends title"
    assert "text: body.text" in body, "useIngestText no longer sends text"

    m = re.search(r'kind:\s*body\.kind\s*\?\?\s*"([^"]+)"', body)
    assert m, "useIngestText no longer defaults kind with a string literal"
    default_kind = m.group(1)

    kinds_src = service_source()
    km = re.search(r"KINDS\s*=\s*List\.of\((.*?)\);", kinds_src, re.DOTALL)
    assert km, "KnowledgeService.KINDS not found"
    kinds = re.findall(r'"([^"]+)"', km.group(1))
    assert kinds, "no kinds parsed from KnowledgeService.KINDS"
    assert default_kind in kinds, (
        "useIngestText defaults kind to %r, which KnowledgeService.KINDS rejects: %s"
        % (default_kind, kinds)
    )


# --------------------------------------------------------------------------- case 7: create posts the whole body

def test_the_create_note_mutation_posts_the_body_to_the_notes_endpoint():
    bodies = ts_call_bodies("useNoteMutations", actions_source())
    assert len(bodies) == 1, "expected exactly one useNoteMutations, found %d" % len(bodies)
    body = bodies[0]
    assert "api.create<KnowledgeNote>(endpoints.knowledgeNotes, body)" in body, (
        "create no longer posts the whole body to endpoints.knowledgeNotes"
    )


# --------------------------------------------------------------------------- case 8: update sends title and content to the item route

def test_the_update_note_mutation_sends_title_and_content_to_the_item_route():
    bodies = ts_call_bodies("useNoteMutations", actions_source())
    assert len(bodies) == 1, "expected exactly one useNoteMutations, found %d" % len(bodies)
    body = bodies[0]
    assert "endpoints.knowledgeNote(body.id)" in body, (
        "update no longer addresses the note by id (endpoints.knowledgeNote(body.id))"
    )
    assert "title: body.title" in body, "update no longer sends title"
    assert "content: body.content" in body, "update no longer sends content"


# --------------------------------------------------------------------------- case 9: the endpoint map names the three routes

def test_the_client_endpoint_map_names_the_three_routes():
    src = read(ENDPOINTS)
    assert 'knowledgeNotes: "/knowledge/notes"' in src, "knowledgeNotes path changed"
    assert "knowledgeNote: (id: string) =>" in src, (
        "knowledgeNote is no longer an id-addressed route"
    )
    assert "/knowledge/notes/${seg(id)}" in src, "knowledgeNote path changed"
    assert 'knowledgeText: "/knowledge/text"' in src, "knowledgeText path changed"


# --------------------------------------------------------------------------- case 10: failure paths are announced

def test_the_knowledge_mutations_announce_their_failures():
    ingest = ts_call_bodies("useIngestText", actions_source())
    assert len(ingest) == 1, "expected exactly one useIngestText"
    assert 'fail("failures.ingest")' in ingest[0], (
        "useIngestText failure toast changed"
    )

    notes = ts_call_bodies("useNoteMutations", actions_source())
    assert len(notes) == 1, "expected exactly one useNoteMutations"
    body = notes[0]
    assert 'fail("failures.noteSave")' in body, "create failure toast changed"
    assert 'fail("failures.noteUpdate")' in body, "update failure toast changed"
    assert 'fail("failures.noteDelete")' in body, "delete failure toast changed"
