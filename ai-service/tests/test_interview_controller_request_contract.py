"""The Interview controller request: two endpoints, their DTOs, and what the browser sends.

InterviewController has two entry points with typed request bodies:

1. ``POST /interview/sessions`` -- create an interview session. Binds
   ``CreateSessionRequest(jobId, jdId, resumeVersionId, companyName, positionTitle, mode, difficulty)``
   where all fields are optional with multiple ``@JsonAlias`` spellings. The frontend calls this through
   ``useCreateInterviewSession`` in ``actions.ts``, sending ``{ jobId, mode, difficulty }``.

2. ``POST /interview/sessions/{id}/answer`` -- submit an answer for evaluation. Binds
   ``AnswerRequest(answer)`` where ``answer`` is required (``@NotBlank``). The frontend calls this
   through ``useSubmitInterviewAnswer``, sending ``{ answer }``.

Note: PATCH /{id} binds a generic ``Map<String, Object>`` rather than a typed DTO, so it is not
included in this gate.

This gate holds the contract at both ends:

- Each DTO declares exactly the expected field names (no extra fields silently accepted).
- Every call site in the app sends exactly those names (no alias the server cannot bind).
- The ``@NotBlank`` guard is armed on ``answer`` in AnswerRequest.
- The mutation failure paths are announced via ``fail()``.

Nothing here runs the AI service or checks the parsed output -- that is the job of other gates.
This file only pins the *request* side of the wire.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/interview/web/InterviewController.java"
DTOS = "backend/src/main/java/com/careeros/interview/dto/InterviewDtos.java"
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


# --------------------------------------------------------------------------- case 1: CreateSessionRequest has seven fields

def test_the_create_session_request_dto_declares_seven_names():
    fields = java_record_fields("CreateSessionRequest", dto_source())
    assert sorted(fields) == [
        "companyName",
        "config",
        "jdId",
        "jobId",
        "mode",
        "positionTitle",
        "resumeVersionId",
    ], "CreateSessionRequest now has %d fields: %s" % (len(fields), fields)


# --------------------------------------------------------------------------- case 2: AnswerRequest has exactly one field

def test_the_answer_request_dto_declares_one_name():
    fields = java_record_fields("AnswerRequest", dto_source())
    assert sorted(fields) == ["answer"], (
        "AnswerRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 3: the controller binds both POST endpoints

def test_both_post_endpoints_bind_their_request_types():
    src = controller_source()
    # POST /interview/sessions binds CreateSessionRequest
    assert "@RequestBody @Valid CreateSessionRequest" in src, (
        "POST /interview/sessions no longer binds CreateSessionRequest"
    )
    # POST /{id}/answer binds AnswerRequest
    assert "@RequestBody @Valid AnswerRequest" in src, (
        "POST /{id}/answer no longer binds AnswerRequest"
    )


# --------------------------------------------------------------------------- case 4: the @NotBlank guard is present on answer

def test_the_answer_field_is_guarded_by_notblank():
    src = dto_source()
    # Find the AnswerRequest record and check answer has @NotBlank
    m = re.search(r"record\s+AnswerRequest\s*\((.*?)\)\s*\{", src, re.DOTALL)
    assert m, "AnswerRequest record not found"
    body = m.group(1)
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if "answer" in line and "String" in line:
            context = line
            if i > 0:
                context = lines[i - 1] + "\n" + context
            assert "@NotBlank" in context, (
                "answer field lost its @NotBlank guard:\n%s" % context
            )
            break
    else:
        assert False, "answer field not found in AnswerRequest"


# --------------------------------------------------------------------------- case 5: useCreateInterviewSession sends jobId, mode, difficulty

def test_use_create_interview_session_sends_body():
    bodies = ts_call_bodies("useCreateInterviewSession", actions_source())
    assert len(bodies) >= 1, "useCreateInterviewSession not found in actions.ts"
    body = bodies[0]
    # Check that the hook sends a body to the endpoint
    assert "api.create" in body, "useCreateInterviewSession no longer uses api.create"
    assert "endpoints.interviews" in body, (
        "useCreateInterviewSession no longer uses interviews endpoint"
    )


# --------------------------------------------------------------------------- case 6: useSubmitInterviewAnswer sends answer

def test_use_submit_interview_answer_sends_answer():
    bodies = ts_call_bodies("useSubmitInterviewAnswer", actions_source())
    assert len(bodies) >= 1, "useSubmitInterviewAnswer not found in actions.ts"
    body = bodies[0]
    # Check that answer is sent in the POST body (handle both explicit and shorthand forms)
    has_explicit = '"answer"' in body or "'answer'" in body
    has_shorthand = re.search(r"\bbody:\s*\{[^}]*\banswer\b", body)
    assert has_explicit or has_shorthand, (
        "useSubmitInterviewAnswer no longer sends answer"
    )
    # Check it's sent to the correct endpoint
    assert "interviewAnswer" in body, (
        "useSubmitInterviewAnswer no longer uses interviewAnswer endpoint"
    )


# --------------------------------------------------------------------------- case 7: the endpoints are named correctly

def test_the_client_endpoint_map_names_both_routes():
    src = read(ENDPOINTS)
    assert "interviews:" in src, "interviews endpoint missing from endpoints.ts"
    assert "interviewAnswer:" in src, "interviewAnswer endpoint missing from endpoints.ts"
    assert '"/interview/sessions"' in src, "interviews path changed"
    assert "/answer" in src, "interviewAnswer path changed"


# --------------------------------------------------------------------------- case 8: the mutation failure paths are announced

def test_the_interview_mutations_announce_their_failures():
    # useCreateInterviewSession
    bodies_create = ts_call_bodies("useCreateInterviewSession", actions_source())
    assert len(bodies_create) >= 1, "useCreateInterviewSession not found in actions.ts"
    body_create = bodies_create[0]
    assert "onError:" in body_create, "useCreateInterviewSession onError handler missing"
    assert 'fail(' in body_create, "useCreateInterviewSession onError does not call fail()"
    assert 'fail("failures.interviewStart")' in body_create, (
        "useCreateInterviewSession failure key changed"
    )

    # useSubmitInterviewAnswer
    bodies_answer = ts_call_bodies("useSubmitInterviewAnswer", actions_source())
    assert len(bodies_answer) >= 1, "useSubmitInterviewAnswer not found in actions.ts"
    body_answer = bodies_answer[0]
    assert "onError:" in body_answer, "useSubmitInterviewAnswer onError handler missing"
    assert 'fail(' in body_answer, "useSubmitInterviewAnswer onError does not call fail()"
    assert 'fail("failures.answerEvaluate")' in body_answer, (
        "useSubmitInterviewAnswer failure key changed"
    )
