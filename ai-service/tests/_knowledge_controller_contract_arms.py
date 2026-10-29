"""Mutation arms for the Knowledge controller request contract gate.

Each arm mutates one clause of the contract and predicts which tests should go red.
All predictions are frozen before running, so a mismatch is itself evidence.

Read/write are byte-faithful (``newline=""``): the working tree is shared with other
sessions, so an arm must be undone by re-writing the captured bytes, never by
``git checkout``.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/knowledge/web/KnowledgeController.java"
DTOS = "backend/src/main/java/com/careeros/knowledge/dto/KnowledgeDtos.java"
ACTIONS = "frontend/src/lib/hooks/actions.ts"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"


def read(rel: str) -> str:
    with open(ROOT / rel, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(rel: str, text: str) -> None:
    with open(ROOT / rel, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def _scoped_replace(src: str, record_name: str, old: str, new: str) -> str:
    """Replace ``old`` with ``new`` only inside ``record Name(...)``'s header."""
    m = re.search(r"record\s+" + record_name + r"\s*\((.*?)\)\s*\{", src, re.DOTALL)
    assert m, "%s record not found" % record_name
    body = m.group(1)
    assert old in body, "%r not found inside %s" % (old, record_name)
    new_body = body.replace(old, new)
    return src[: m.start(1)] + new_body + src[m.end(1):]


# --------------------------------------------------------------------------- Arms

def arm_remove_notblank_from_note_content() -> dict:
    """Drop @NotBlank from NoteRequest.content -- the guard test should fail."""
    old = read(DTOS)
    new = old.replace("@NotBlank String content", "String content")
    assert new != old, "@NotBlank String content not found"
    write(DTOS, new)
    return {
        "name": "remove @NotBlank from NoteRequest.content",
        "predicted_red": ["test_the_note_content_field_is_guarded_by_notblank"],
        "description": "content remains declared but unguarded; census still sees the field",
    }


def arm_rename_content_to_body_in_note_request() -> dict:
    """Rename content->body in NoteRequest -- census and guard tests should fail."""
    new = _scoped_replace(read(DTOS), "NoteRequest", "String content", "String body")
    write(DTOS, new)
    return {
        "name": "rename content to body in NoteRequest",
        "predicted_red": [
            "test_the_note_request_dto_declares_three_names",
            "test_the_note_content_field_is_guarded_by_notblank",
        ],
        "description": "field name changed; census finds [body, tags, title], guard finds no content",
    }


def arm_rename_kind_to_channel_in_text_ingest() -> dict:
    """Rename kind->channel in TextIngestRequest -- census and guard tests should fail."""
    new = _scoped_replace(read(DTOS), "TextIngestRequest", "String kind", "String channel")
    write(DTOS, new)
    return {
        "name": "rename kind to channel in TextIngestRequest",
        "predicted_red": [
            "test_the_text_ingest_request_dto_declares_four_names",
            "test_the_ingest_text_and_kind_fields_are_guarded_by_notblank",
        ],
        "description": "hook still sends kind; backend would silently drop it; guard map loses kind",
    }


def arm_rename_title_to_subject_in_text_ingest() -> dict:
    """Rename title->subject in TextIngestRequest -- the census test should fail."""
    new = _scoped_replace(read(DTOS), "TextIngestRequest", "String title", "String subject")
    write(DTOS, new)
    return {
        "name": "rename title to subject in TextIngestRequest",
        "predicted_red": ["test_the_text_ingest_request_dto_declares_four_names"],
        "description": "only the census keys on title; the guards cover text/kind",
    }


def arm_remove_valid_from_text_ingest_binding() -> dict:
    """Remove @Valid from the TextIngestRequest binding -- the controller test should fail."""
    old = read(CONTROLLER)
    new = old.replace("@RequestBody @Valid TextIngestRequest", "@RequestBody TextIngestRequest")
    assert new != old, "@Valid not found on TextIngestRequest binding"
    write(CONTROLLER, new)
    return {
        "name": "remove @Valid from TextIngestRequest binding",
        "predicted_red": ["test_the_controller_binds_note_request_on_both_routes_and_ingest_once"],
        "description": "ingest binding count drops from 1 to 0",
    }


def arm_unbind_one_note_request_route() -> dict:
    """Remove @Valid from the FIRST NoteRequest binding -- count should drop to 1."""
    old = read(CONTROLLER)
    new = old.replace("@RequestBody @Valid NoteRequest", "@RequestBody NoteRequest", 1)
    assert new != old, "@Valid not found on NoteRequest bindings"
    write(CONTROLLER, new)
    return {
        "name": "remove @Valid from one of the two NoteRequest bindings",
        "predicted_red": ["test_the_controller_binds_note_request_on_both_routes_and_ingest_once"],
        "description": "presence alone would survive; the count==2 clause is the discriminator",
    }


def arm_change_ingest_failure_message() -> dict:
    """Change useIngestText's failure key -- the announcement test should fail."""
    old = read(ACTIONS)
    new = old.replace('fail("failures.ingest")', 'fail("failures.ingestCrashed")')
    assert new != old, "ingest failure key not found"
    write(ACTIONS, new)
    return {
        "name": "change useIngestText failure key",
        "predicted_red": ["test_the_knowledge_mutations_announce_their_failures"],
        "description": "fail() still called, but the key the toast resolves changed",
    }


def arm_rename_update_body_key_content_to_text() -> dict:
    """Send the update under key text instead of content -- the update test should fail."""
    old = read(ACTIONS)
    new = old.replace("content: body.content", "text: body.content")
    assert new != old, "update content key not found"
    write(ACTIONS, new)
    return {
        "name": "rename update body key content->text",
        "predicted_red": [
            "test_the_update_note_mutation_sends_title_and_content_to_the_item_route"
        ],
        "description": "backend NoteRequest binds content; key text would be silently dropped",
    }


def arm_change_default_kind_to_unlisted_value() -> dict:
    """Default kind to 'notes' -- not in the backend whitelist; the ingest test should fail."""
    old = read(ACTIONS)
    new = old.replace('body.kind ?? "note"', 'body.kind ?? "notes"')
    assert new != old, "kind default not found"
    write(ACTIONS, new)
    return {
        "name": "default ingest kind to an unlisted value",
        "predicted_red": [
            "test_use_ingest_text_sends_title_text_and_a_default_kind_the_backend_accepts"
        ],
        "description": "default_kind 'notes' is not in KnowledgeService.KINDS",
    }


def arm_repoint_create_to_text_endpoint() -> dict:
    """Post the create to the ingest endpoint -- the create test should fail."""
    old = read(ACTIONS)
    new = old.replace(
        "api.create<KnowledgeNote>(endpoints.knowledgeNotes, body)",
        "api.create<KnowledgeNote>(endpoints.knowledgeText, body)",
    )
    assert new != old, "create call not found"
    write(ACTIONS, new)
    return {
        "name": "re-point create note to the text endpoint",
        "predicted_red": ["test_the_create_note_mutation_posts_the_body_to_the_notes_endpoint"],
        "description": "body unchanged, route wrong; only the create test names the route",
    }


def arm_change_knowledge_text_path() -> dict:
    """Change the knowledgeText path in the endpoint map -- the map test should fail."""
    old = read(ENDPOINTS)
    new = old.replace('knowledgeText: "/knowledge/text"', 'knowledgeText: "/knowledge/texts"')
    assert new != old, "knowledgeText path not found"
    write(ENDPOINTS, new)
    return {
        "name": "change knowledgeText path in the endpoint map",
        "predicted_red": ["test_the_client_endpoint_map_names_the_three_routes"],
        "description": "path drifts from the Spring route POST /knowledge/text",
    }


ARMS = [
    arm_remove_notblank_from_note_content,
    arm_rename_content_to_body_in_note_request,
    arm_rename_kind_to_channel_in_text_ingest,
    arm_rename_title_to_subject_in_text_ingest,
    arm_remove_valid_from_text_ingest_binding,
    arm_unbind_one_note_request_route,
    arm_change_ingest_failure_message,
    arm_rename_update_body_key_content_to_text,
    arm_change_default_kind_to_unlisted_value,
    arm_repoint_create_to_text_endpoint,
    arm_change_knowledge_text_path,
]
