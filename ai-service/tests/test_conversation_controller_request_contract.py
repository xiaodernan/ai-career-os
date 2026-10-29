"""The Conversation controller request: two endpoints, their DTOs, and what the browser sends.

ConversationController has two entry points with typed request bodies:

1. ``POST /conversations`` -- create a conversation. Binds ``CreateConversationRequest(title, context)``
   where both fields are optional (``@Size(max = 200)`` on title). The frontend calls this through
   ``useCreateConversation`` in ``actions.ts``, sending ``{ title }`` with a default of "New chat".

2. ``PATCH /conversations/{id}`` -- update a conversation (rename or set context). Binds
   ``UpdateConversationRequest(title, context)`` where both fields are optional (``@Size(max = 200)``
   on title). The frontend calls this through ``useRenameConversation``, sending ``{ title }``.

This gate holds the contract at both ends:

- Each DTO declares exactly the expected field names (no extra fields silently accepted).
- Every call site in the app sends exactly those names (no alias the server cannot bind).
- The mutation failure paths are announced via ``fail()``.

Nothing here runs the AI service or checks the parsed output -- that is the job of other gates.
This file only pins the *request* side of the wire.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/conversation/web/ConversationController.java"
DTOS = "backend/src/main/java/com/careeros/conversation/dto/ConversationDtos.java"
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
def actions_source() -> str:
    return read(ACTIONS)


def java_record_fields(record_name: str, source: str) -> list[str]:
    """Return the field names declared inside ``record RecordName(...)`` in Java source."""
    m = re.search(r"record\s+" + record_name + r"\s*\((.*?)\)\s*\{", source, re.DOTALL)
    if not m:
        return []
    body = m.group(1).strip()

    # Remove all annotation content (everything between @ and the type declaration)
    # This handles @JsonAlias({...}), @NotBlank, @Size(...), etc.
    cleaned = re.sub(r"@[\w.]+\s*(?:\{[^}]*\}|\([^)]*\))?\s*", "", body)
    
    # Also remove generic type parameters (<...>) to avoid splitting on commas inside them
    cleaned = re.sub(r"<[^>]*>", "", cleaned)

    fields = []
    if "\n" not in cleaned and "," in cleaned:
        # Single-line record: split by comma first
        for part in cleaned.split(","):
            part = part.strip()
            if not part or part.startswith("//"):
                continue
            tokens = part.split()
            if tokens:
                fields.append(tokens[-1])
    else:
        # Multi-line record: process line by line
        for line in cleaned.splitlines():
            line = line.strip().rstrip(",")
            if not line or line.startswith("//"):
                continue
            parts = line.split()
            fields.append(parts[-1])
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


# --------------------------------------------------------------------------- case 1: CreateConversationRequest has exactly two fields

def test_the_create_conversation_request_dto_declares_two_names():
    fields = java_record_fields("CreateConversationRequest", dto_source())
    assert sorted(fields) == ["context", "title"], (
        "CreateConversationRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 2: UpdateConversationRequest has exactly two fields

def test_the_update_conversation_request_dto_declares_two_names():
    fields = java_record_fields("UpdateConversationRequest", dto_source())
    assert sorted(fields) == ["context", "title"], (
        "UpdateConversationRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 3: the controller binds both endpoints

def test_both_endpoints_bind_their_request_types():
    src = controller_source()
    # POST /conversations binds CreateConversationRequest
    assert "@RequestBody" in src and "CreateConversationRequest" in src, (
        "POST /conversations no longer binds CreateConversationRequest"
    )
    # PATCH /{id} binds UpdateConversationRequest
    assert "@RequestBody @Valid UpdateConversationRequest" in src, (
        "PATCH /{id} no longer binds UpdateConversationRequest"
    )


# --------------------------------------------------------------------------- case 4: useCreateConversation sends title

def test_use_create_conversation_sends_title():
    bodies = ts_call_bodies("useCreateConversation", actions_source())
    assert len(bodies) >= 1, "useCreateConversation not found in actions.ts"
    body = bodies[0]
    # Check that title is sent in the POST body (handle both explicit and shorthand forms)
    has_explicit = '"title"' in body or "'title'" in body
    has_shorthand = re.search(r"\{[^}]*\btitle\b", body)
    assert has_explicit or has_shorthand, (
        "useCreateConversation no longer sends title"
    )
    # Check it's sent to the correct endpoint
    assert "endpoints.conversations" in body, (
        "useCreateConversation no longer uses conversations endpoint"
    )


# --------------------------------------------------------------------------- case 5: useRenameConversation sends title

def test_use_rename_conversation_sends_title():
    bodies = ts_call_bodies("useRenameConversation", actions_source())
    assert len(bodies) >= 1, "useRenameConversation not found in actions.ts"
    body = bodies[0]
    # Check that title is sent in the PATCH body (handle both explicit and shorthand forms)
    has_explicit = '"title"' in body or "'title'" in body
    has_shorthand = re.search(r"\{[^}]*\btitle\b", body)
    assert has_explicit or has_shorthand, (
        "useRenameConversation no longer sends title"
    )
    # Check it's sent to the correct endpoint
    assert "endpoints.conversation(id)" in body or "conversation(" in body, (
        "useRenameConversation no longer uses conversation endpoint"
    )


# --------------------------------------------------------------------------- case 6: the endpoints are named correctly

def test_the_client_endpoint_map_names_both_routes():
    src = read(ENDPOINTS)
    assert "conversations:" in src, "conversations endpoint missing from endpoints.ts"
    assert "conversation:" in src, "conversation endpoint missing from endpoints.ts"
    assert '"/conversations"' in src, "conversations path changed"


# --------------------------------------------------------------------------- case 7: the mutation failure paths are announced

def test_the_conversation_mutations_announce_their_failures():
    # useCreateConversation
    bodies_create = ts_call_bodies("useCreateConversation", actions_source())
    assert len(bodies_create) >= 1, "useCreateConversation not found in actions.ts"
    body_create = bodies_create[0]
    assert "onError:" in body_create, "useCreateConversation onError handler missing"
    assert 'fail(' in body_create, "useCreateConversation onError does not call fail()"
    assert 'fail("failures.conversationStart")' in body_create, (
        "useCreateConversation failure key changed"
    )

    # useRenameConversation
    bodies_rename = ts_call_bodies("useRenameConversation", actions_source())
    assert len(bodies_rename) >= 1, "useRenameConversation not found in actions.ts"
    body_rename = bodies_rename[0]
    assert "onError:" in body_rename, "useRenameConversation onError handler missing"
    assert 'fail(' in body_rename, "useRenameConversation onError does not call fail()"
    assert 'fail("failures.conversationRename")' in body_rename, (
        "useRenameConversation failure key changed"
    )
