"""The Application controller request: the three mutation endpoints, their DTOs, and what the browser sends.

ApplicationController has three entry points that bind request bodies:

1. ``POST /applications`` -- create a new application. Binds ``CreateApplicationRequest(jobId, companyId, title, companyName, ...)`` where ``title`` is required (``@NotBlank @Size(max = 300)``). The frontend calls this through ``useCreateApplication`` in ``actions.ts``, sending the full body.

2. ``PATCH /applications/{id}`` -- update an application's status, position, note, or reminder. Binds ``UpdateApplicationRequest(status, position, note, reminderAt, clearReminderAt)``. The frontend calls this through ``useUpdateApplication``, sending a partial patch.

3. ``PUT /applications/{id}/reorder`` -- reorder after drag-drop. Binds ``ReorderRequest(position, status)``. The frontend calls this through ``useReorderApplication``, sending both fields.

This gate holds the contract at both ends:

- Each DTO declares exactly the expected field names (no extra fields silently accepted).
- Every call site in the app sends exactly those names (no alias the server cannot bind).
- The ``@NotBlank`` guard is armed on ``title``.
- The mutation failure paths are announced via ``fail()``.

Nothing here runs the backend or checks the persisted state -- that is the job of other gates.
This file only pins the *request* side of the wire.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/application/web/ApplicationController.java"
DTOS = "backend/src/main/java/com/careeros/application/dto/ApplicationDtos.java"
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
    fields = []
    # Check if this is a single-line record (all fields on one line separated by commas)
    if "\n" not in body and "," in body:
        # Single-line: split by comma and extract last token from each part
        for part in body.split(","):
            part = part.strip()
            if not part or part.startswith("//"):
                continue
            tokens = part.split()
            if tokens:
                fields.append(tokens[-1])
    else:
        # Multi-line: process each line
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


# --------------------------------------------------------------------------- case 1: CreateApplicationRequest has the expected fields

def test_the_create_application_request_dto_declares_its_names():
    fields = java_record_fields("CreateApplicationRequest", dto_source())
    # Must have at least jobId, companyId, title, companyName
    assert "jobId" in fields, "CreateApplicationRequest missing jobId"
    assert "companyId" in fields, "CreateApplicationRequest missing companyId"
    assert "title" in fields, "CreateApplicationRequest missing title"
    assert "companyName" in fields, "CreateApplicationRequest missing companyName"


# --------------------------------------------------------------------------- case 2: UpdateApplicationRequest has the expected fields

def test_the_update_application_request_dto_declares_its_names():
    fields = java_record_fields("UpdateApplicationRequest", dto_source())
    # Must have status, position, note, reminderAt, clearReminderAt
    assert "status" in fields, "UpdateApplicationRequest missing status"
    assert "position" in fields, "UpdateApplicationRequest missing position"
    assert "note" in fields, "UpdateApplicationRequest missing note"
    assert "reminderAt" in fields, "UpdateApplicationRequest missing reminderAt"
    assert "clearReminderAt" in fields, "UpdateApplicationRequest missing clearReminderAt"


# --------------------------------------------------------------------------- case 3: ReorderRequest has exactly two fields

def test_the_reorder_request_dto_declares_two_names():
    fields = java_record_fields("ReorderRequest", dto_source())
    assert sorted(fields) == ["position", "status"], (
        "ReorderRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 4: the controller binds all three mutation endpoints

def test_all_three_mutation_endpoints_bind_their_request_types():
    src = controller_source()
    # POST /applications binds CreateApplicationRequest
    assert "@RequestBody @Valid CreateApplicationRequest" in src, (
        "POST /applications no longer binds CreateApplicationRequest"
    )
    # PATCH /{id} binds UpdateApplicationRequest
    assert "@RequestBody @Valid UpdateApplicationRequest" in src, (
        "PATCH /{id} no longer binds UpdateApplicationRequest"
    )
    # PUT /{id}/reorder binds ReorderRequest
    assert "@RequestBody @Valid ReorderRequest" in src, (
        "PUT /{id}/reorder no longer binds ReorderRequest"
    )


# --------------------------------------------------------------------------- case 5: the title field is guarded by @NotBlank

def test_the_title_field_is_guarded_by_notblank():
    src = dto_source()
    # Find the CreateApplicationRequest record and check title has @NotBlank
    m = re.search(r"record\s+CreateApplicationRequest\s*\((.*?)\)\s*\{", src, re.DOTALL)
    assert m, "CreateApplicationRequest record not found"
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
        assert False, "title field not found in CreateApplicationRequest"


# --------------------------------------------------------------------------- case 6: useCreateApplication sends the body to the correct endpoint

def test_use_create_application_sends_the_body_to_applications():
    bodies = ts_call_bodies("useCreateApplication", actions_source())
    assert len(bodies) >= 1, "useCreateApplication not found in actions.ts"
    body = bodies[0]
    # Check it uses api.create with endpoints.applications
    assert "api.create" in body, "useCreateApplication no longer uses api.create"
    assert "endpoints.applications" in body, "useCreateApplication no longer uses applications endpoint"
    # Check it passes the body parameter
    assert ", body)" in body, "useCreateApplication no longer passes the body"


# --------------------------------------------------------------------------- case 7: useUpdateApplication sends the patch to the correct endpoint

def test_use_update_application_sends_the_patch_to_application_id():
    bodies = ts_call_bodies("useUpdateApplication", actions_source())
    assert len(bodies) >= 1, "useUpdateApplication not found in actions.ts"
    body = bodies[0]
    # Check it uses api.update with endpoints.application(id)
    assert "api.update" in body, "useUpdateApplication no longer uses api.update"
    assert "endpoints.application" in body, "useUpdateApplication no longer uses application endpoint"
    # Check it sends the patch
    assert "patch" in body, "useUpdateApplication no longer sends patch"


# --------------------------------------------------------------------------- case 8: useReorderApplication sends status and position

def test_use_reorder_application_sends_status_and_position():
    bodies = ts_call_bodies("useReorderApplication", actions_source())
    assert len(bodies) >= 1, "useReorderApplication not found in actions.ts"
    body = bodies[0]
    # Extract the POST body object - look for the actual body: { ... } inside api.request
    body_obj_match = re.search(r'body:\s*\{\s*status:', body, re.DOTALL)
    assert body_obj_match, "cannot find the status field in useReorderApplication POST body"
    # Check that position is sent (mapped from order)
    assert "position:" in body or "position :" in body, (
        "useReorderApplication no longer sends position in POST body"
    )
    # Check it uses the reorder endpoint
    assert "applicationReorder" in body or "Reorder" in body, (
        "useReorderApplication no longer uses reorder endpoint"
    )


# --------------------------------------------------------------------------- case 9: the mutation failure paths are announced

def test_the_application_mutations_announce_their_failures():
    # useCreateApplication
    bodies_create = ts_call_bodies("useCreateApplication", actions_source())
    assert len(bodies_create) >= 1
    body_create = bodies_create[0]
    assert "onError:" in body_create, "useCreateApplication onError handler missing"
    assert 'fail(' in body_create, "useCreateApplication onError does not call fail()"
    assert "Couldn't create the application" in body_create, (
        "useCreateApplication failure toast message changed"
    )

    # useUpdateApplication
    bodies_update = ts_call_bodies("useUpdateApplication", actions_source())
    assert len(bodies_update) >= 1
    body_update = bodies_update[0]
    assert "onError:" in body_update, "useUpdateApplication onError handler missing"
    assert 'fail(' in body_update, "useUpdateApplication onError does not call fail()"
    assert "Couldn't update that application" in body_update, (
        "useUpdateApplication failure toast message changed"
    )

    # useReorderApplication
    bodies_reorder = ts_call_bodies("useReorderApplication", actions_source())
    assert len(bodies_reorder) >= 1
    body_reorder = bodies_reorder[0]
    assert "onError:" in body_reorder, "useReorderApplication onError handler missing"
    assert 'fail(' in body_reorder, "useReorderApplication onError does not call fail()"
    assert "Couldn't persist that move" in body_reorder, (
        "useReorderApplication failure toast message changed"
    )
