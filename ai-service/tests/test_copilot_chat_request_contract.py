"""The copilot chat request: the three fields the backend binds, and what the browser sends.

CopilotController has two entry points for one question: ``POST /copilot/chat`` (blocking) and
``POST /copilot/chat/stream`` (SSE). Both bind the same ``ChatRequest`` record:

* ``conversationId`` -- optional UUID; null means start a new thread.
* ``message`` -- required, 1..8000 chars; the user's turn.
* ``context`` -- optional map; extra state the client attaches.

The frontend calls these through ``useCopilotChat`` in ``actions.ts``: it tries the stream first,
falls back to the blocking endpoint on 404, and normalises the answer out of six possible key
spellings before handing a ``CopilotReply`` to the page. The mutation's own ``onSuccess`` invalidates
three query keys (conversations, messages, activity), so the UI refreshes after every turn.

This gate holds the contract at both ends:

1. The DTO declares exactly those three names (no fourth field silently accepted by Jackson).
2. Every call site in the app sends exactly those three names (no alias the server cannot bind).
3. The ``@NotBlank`` guard is armed: a blank message would be rejected before reaching the service.
4. The fallback path sends the same body shape as the primary one (no drift between the two routes).

Nothing here runs the service or checks the stored turn -- that is the job of #116 (ChatResponse
shape) and the SSE event gates (#97/#107/#173-#185). This file only pins the *request* side of the
wire: which names the handler expects, and which names the callers actually send.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/conversation/web/CopilotController.java"
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
    body = m.group(1)
    fields = []
    for line in body.splitlines():
        line = line.strip().rstrip(",")
        if not line or line.startswith("//"):
            continue
        # Strip annotations like @JsonAlias("...") and type info, keep the last word = field name
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


# --------------------------------------------------------------------------- case 1: the DTO has exactly three fields

def test_the_chat_request_dto_declares_three_names_and_no_more():
    fields = java_record_fields("ChatRequest", dto_source())
    assert sorted(fields) == ["context", "conversationId", "message"], (
        "ChatRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 2: the controller binds ChatRequest on both routes

def test_both_copilot_endpoints_bind_the_same_request_type():
    src = controller_source()
    # Both @PostMapping methods must accept @Valid ChatRequest as their body parameter
    posts = re.findall(r"@PostMapping[^)]*\)\s+public\s+\w+\s+\w+\([^)]*@RequestBody\s+@Valid\s+ChatRequest", src)
    assert len(posts) == 2, (
        "expected two @PostMapping methods binding @Valid ChatRequest, found %d:\n%s"
        % (len(posts), src)
    )


# --------------------------------------------------------------------------- case 3: the @NotBlank guard is present on message

def test_the_message_field_is_guarded_by_notblank():
    src = dto_source()
    # The guard can be on the field declaration or on the accessor method
    assert "@NotBlank" in src, "the @NotBlank guard disappeared from ConversationDtos"
    # Find the ChatRequest record and check message has the annotation
    m = re.search(r"record\s+ChatRequest\s*\((.*?)\)\s*\{", src, re.DOTALL)
    assert m, "ChatRequest record not found"
    body = m.group(1)
    # message must have @NotBlank somewhere near it (same line or previous line)
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if "message" in line and "String" in line:
            # Check this line or the line above for @NotBlank
            context = line
            if i > 0:
                context = lines[i - 1] + "\n" + context
            assert "@NotBlank" in context, (
                "message field lost its @NotBlank guard:\n%s" % context
            )
            break
    else:
        assert False, "message field not found in ChatRequest"


# --------------------------------------------------------------------------- case 4: the frontend sends exactly those three names

def test_the_stream_call_sends_the_three_dto_names():
    bodies = ts_call_bodies("useCopilotChat", actions_source())
    assert len(bodies) >= 1, "useCopilotChat not found in actions.ts"
    body = bodies[0]
    # Find the first POST body inside mutationFn (not the parameter type)
    # Look for the pattern: body: { message: ... }
    post_body_match = re.search(r"postSSE[^{]*\{[^}]*body:\s*\{(.*?)\}", body, re.DOTALL)
    if not post_body_match:
        # Fallback: find the first body object after mutationFn
        mutation_fn_match = re.search(r"mutationFn:", body)
        if mutation_fn_match:
            after_mutation = body[mutation_fn_match.start():]
            post_body_match = re.search(r"body:\s*\{(.*?)\}", after_mutation, re.DOTALL)
    assert post_body_match, "cannot find the POST body object in useCopilotChat"
    body_obj = post_body_match.group(1)
    # Check the three field names inside the body object only
    assert re.search(r'\bmessage\s*:', body_obj), (
        "the stream call no longer sends 'message'"
    )
    assert re.search(r'\bconversationId\b', body_obj), (
        "the stream call no longer sends 'conversationId'"
    )
    assert re.search(r'\bcontext\s*:', body_obj), (
        "the stream call no longer sends 'context'"
    )
    # No fourth field should appear in the body object (excluding spread and nested objects)
    props = re.findall(r"(?:^|,)\s*(\w+)\s*:", body_obj, re.M)
    unexpected = [p for p in props if p not in ("message", "conversationId", "context")]
    assert not unexpected, (
        "the stream call sends unexpected fields: %s" % unexpected
    )


def test_the_fallback_call_sends_the_same_three_names():
    bodies = ts_call_bodies("useCopilotChat", actions_source())
    assert len(bodies) >= 1
    body = bodies[0]
    # The fallback is inside the catch block; find the second api.request call
    fallback_matches = list(re.finditer(r"api\.request<[^>]*>\(\s*endpoints\.copilotChat", body))
    assert len(fallback_matches) >= 1, "fallback call to copilotChat not found"
    fallback_start = fallback_matches[0].start()
    fallback_block = body[fallback_start:]
    # Extract the body object from the fallback call
    body_obj_match = re.search(r"body:\s*\{(.*?)\}", fallback_block, re.DOTALL)
    assert body_obj_match, "cannot find the body object in the fallback call"
    body_obj = body_obj_match.group(1)
    # Check the same three names inside the body object only
    assert '"message"' in body_obj or "'message'" in body_obj or re.search(r'\bmessage\s*:', body_obj), (
        "the fallback call no longer sends 'message'"
    )
    assert "conversationId" in body_obj, (
        "the fallback call no longer sends 'conversationId'"
    )
    assert '"context"' in body_obj or "'context'" in body_obj or re.search(r'\bcontext\s*:', body_obj), (
        "the fallback call no longer sends 'context'"
    )


# --------------------------------------------------------------------------- case 5: the endpoints are named correctly

def test_the_client_endpoint_map_names_both_routes():
    src = read(ENDPOINTS)
    assert "copilotChat:" in src, "copilotChat endpoint missing from endpoints.ts"
    assert "copilotChatStream:" in src, "copilotChatStream endpoint missing from endpoints.ts"
    assert '"/copilot/chat"' in src, "copilotChat path changed"
    assert '"/copilot/chat/stream"' in src, "copilotChatStream path changed"


# --------------------------------------------------------------------------- case 6: the mutation failure path is announced

def test_the_copilot_mutation_announces_its_failure():
    bodies = ts_call_bodies("useCopilotChat", actions_source())
    assert len(bodies) >= 1
    body = bodies[0]
    # onError must call fail() with a message
    assert "onError:" in body, "onError handler missing"
    assert 'fail(' in body, "onError does not call fail()"
    assert 'fail("copilot.couldNotAnswer")' in body, "the failure key changed"
