"""The Resume controller request: three endpoints, their DTOs, and what the browser sends.

ResumeController has three entry points with request bodies:

1. ``POST /resumes`` -- create a resume. Binds ``CreateResumeRequest(title, plaintext)`` where
   ``title`` is required (``@NotBlank @Size(max=200)``) and ``plaintext`` is optional with multiple
   ``@JsonAlias`` spellings. The frontend calls this through screens that POST directly to the
   endpoint (not through a named hook in actions.ts).

2. ``PATCH /resumes/{id}`` -- update a resume. Binds ``UpdateResumeRequest(title)`` where
   ``title`` is optional (``@Size(min=1, max=200)``). No named hook in actions.ts; used by edit
   screens.

3. ``POST /resumes/{id}/set-current`` -- set the current version. Binds
   ``SetCurrentVersionRequest(versionId)`` where ``versionId`` is required with
   ``@JsonAlias({"version_id"})``. The frontend calls this through ``useSetCurrentResume`` in
   ``actions.ts``, sending ``{ versionId }`` via the ``field()`` helper.

This gate holds the contract at both ends:

- Each DTO declares exactly the expected field names (no extra fields silently accepted).
- Every call site in the app sends exactly those names (no alias the server cannot bind).
- The ``@NotBlank`` guard is armed on ``title`` in CreateResumeRequest.
- The mutation failure paths are announced via ``fail()``.

Nothing here runs the AI service or checks the parsed output -- that is the job of other gates.
This file only pins the *request* side of the wire.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/resume/web/ResumeController.java"
DTOS = "backend/src/main/java/com/careeros/resume/dto/ResumeDtos.java"
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


# --------------------------------------------------------------------------- case 1: CreateResumeRequest has exactly two fields

def test_the_create_resume_request_dto_declares_two_names():
    fields = java_record_fields("CreateResumeRequest", dto_source())
    assert sorted(fields) == ["plaintext", "title"], (
        "CreateResumeRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 2: UpdateResumeRequest has exactly one field

def test_the_update_resume_request_dto_declares_one_name():
    fields = java_record_fields("UpdateResumeRequest", dto_source())
    assert sorted(fields) == ["title"], (
        "UpdateResumeRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 3: SetCurrentVersionRequest has exactly one field

def test_the_set_current_version_request_dto_declares_one_name():
    fields = java_record_fields("SetCurrentVersionRequest", dto_source())
    assert sorted(fields) == ["versionId"], (
        "SetCurrentVersionRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 4: the controller binds all three POST/PATCH endpoints

def test_all_three_endpoints_bind_their_request_types():
    src = controller_source()
    # POST /resumes binds CreateResumeRequest
    assert "@RequestBody @Valid CreateResumeRequest" in src, (
        "POST /resumes no longer binds CreateResumeRequest"
    )
    # PATCH /{id} binds UpdateResumeRequest
    assert "@RequestBody @Valid UpdateResumeRequest" in src, (
        "PATCH /{id} no longer binds UpdateResumeRequest"
    )
    # POST /{id}/set-current binds SetCurrentVersionRequest
    assert "@RequestBody @Valid SetCurrentVersionRequest" in src, (
        "POST /{id}/set-current no longer binds SetCurrentVersionRequest"
    )


# --------------------------------------------------------------------------- case 5: the @NotBlank guard is present on title

def test_the_title_field_is_guarded_by_notblank_in_create():
    src = dto_source()
    # Find the CreateResumeRequest record and check title has @NotBlank
    m = re.search(r"record\s+CreateResumeRequest\s*\((.*?)\)\s*\{", src, re.DOTALL)
    assert m, "CreateResumeRequest record not found"
    body = m.group(1)
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if "title" in line and "String" in line:
            context = line
            if i > 0:
                context = lines[i - 1] + "\n" + context
            assert "@NotBlank" in context, (
                "title field lost its @NotBlank guard:\n%s" % context
            )
            break
    else:
        assert False, "title field not found in CreateResumeRequest"


# --------------------------------------------------------------------------- case 6: useSetCurrentResume sends versionId

def test_use_set_current_resume_sends_version_id():
    bodies = ts_call_bodies("useSetCurrentResume", actions_source())
    assert len(bodies) >= 1, "useSetCurrentResume not found in actions.ts"
    body = bodies[0]
    # Check that versionId is sent in the POST body
    assert 'field("versionId"' in body or "field('versionId'" in body, (
        "useSetCurrentResume no longer sends versionId"
    )
    # Check it's sent to the correct endpoint
    assert "resumeSetCurrent" in body, (
        "useSetCurrentResume no longer uses resumeSetCurrent endpoint"
    )


# --------------------------------------------------------------------------- case 7: the endpoints are named correctly

def test_the_client_endpoint_map_names_all_routes():
    src = read(ENDPOINTS)
    assert "resumeUpload:" in src, "resumeUpload endpoint missing from endpoints.ts"
    assert "resumeParse:" in src, "resumeParse endpoint missing from endpoints.ts"
    assert "resumeSetCurrent:" in src, "resumeSetCurrent endpoint missing from endpoints.ts"
    assert '"/resumes/upload"' in src, "resumeUpload path changed"
    assert "/parse" in src, "resumeParse path changed"
    assert "/set-current" in src, "resumeSetCurrent path changed"


# --------------------------------------------------------------------------- case 8: the mutation failure paths are announced

def test_the_resume_mutations_announce_their_failures():
    # useSetCurrentResume
    bodies = ts_call_bodies("useSetCurrentResume", actions_source())
    assert len(bodies) >= 1, "useSetCurrentResume not found in actions.ts"
    body = bodies[0]
    assert "onError:" in body, "useSetCurrentResume onError handler missing"
    assert 'fail(' in body, "useSetCurrentResume onError does not call fail()"
    assert 'fail("failures.versionSwitch")' in body, (
        "useSetCurrentResume failure key changed"
    )
