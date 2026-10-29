"""The JD controller request: the three endpoints, their DTOs, and what the browser sends.

JdController has three entry points:

1. ``POST /jds`` -- analyze a job description text. Binds ``JdRequest(rawText, jobId)`` where
   ``rawText`` is required (``@NotBlank``) and ``jobId`` is optional. The frontend calls this
   through ``useAnalyzeJd`` in ``actions.ts``, sending only ``{ rawText }``.

2. ``GET /jds/{id}`` -- retrieve a previously analyzed JD by UUID. No body; path parameter only.
   Not called directly from the app (the dialog keeps its own copy), but the route exists for
   future use.

3. ``POST /jds/suggestions`` -- get skill-gap suggestions for a resume vs a JD. Binds
   ``JdSuggestionsRequest(resumeVersionId, jdRaw)`` where ``jdRaw`` is required (``@NotBlank``).
   The frontend calls this through ``useResumeSuggestions``, sending both fields.

This gate holds the contract at both ends:

- Each DTO declares exactly the expected field names (no extra fields silently accepted).
- Every call site in the app sends exactly those names (no alias the server cannot bind).
- The ``@NotBlank`` guards are armed on ``rawText`` and ``jdRaw``.
- The mutation failure paths are announced via ``fail()``.

Nothing here runs the AI service or checks the parsed output -- that is the job of other gates.
This file only pins the *request* side of the wire.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/job/web/JdController.java"
DTOS = "backend/src/main/java/com/careeros/job/dto/JobDtos.java"
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


# --------------------------------------------------------------------------- case 1: JdRequest has exactly two fields

def test_the_jd_request_dto_declares_two_names():
    fields = java_record_fields("JdRequest", dto_source())
    assert sorted(fields) == ["jobId", "rawText"], (
        "JdRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 2: JdSuggestionsRequest has exactly two fields

def test_the_jd_suggestions_request_dto_declares_two_names():
    fields = java_record_fields("JdSuggestionsRequest", dto_source())
    assert sorted(fields) == ["jdRaw", "resumeVersionId"], (
        "JdSuggestionsRequest now has %d fields: %s" % (len(fields), fields)
    )


# --------------------------------------------------------------------------- case 3: the controller binds both POST endpoints

def test_both_post_endpoints_bind_their_request_types():
    src = controller_source()
    # POST /jds binds JdRequest
    assert "@RequestBody @Valid JdRequest" in src, "POST /jds no longer binds JdRequest"
    # POST /jds/suggestions binds JdSuggestionsRequest
    assert "@RequestBody @Valid JdSuggestionsRequest" in src, (
        "POST /jds/suggestions no longer binds JdSuggestionsRequest"
    )


# --------------------------------------------------------------------------- case 4: the @NotBlank guards are present

def test_the_rawtext_field_is_guarded_by_notblank():
    src = dto_source()
    # Find the JdRequest record and check rawText has @NotBlank
    m = re.search(r"record\s+JdRequest\s*\((.*?)\)\s*\{", src, re.DOTALL)
    assert m, "JdRequest record not found"
    body = m.group(1)
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if "rawText" in line and "String" in line:
            context = line
            if i > 0:
                context = lines[i - 1] + "\n" + context
            assert "@NotBlank" in context, (
                "rawText field lost its @NotBlank guard:\n%s" % context
            )
            break
    else:
        assert False, "rawText field not found in JdRequest"


def test_the_jdraw_field_is_guarded_by_notblank():
    src = dto_source()
    # Find the JdSuggestionsRequest record and check jdRaw has @NotBlank
    m = re.search(r"record\s+JdSuggestionsRequest\s*\((.*?)\)\s*\{", src, re.DOTALL)
    assert m, "JdSuggestionsRequest record not found"
    body = m.group(1)
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if "jdRaw" in line and "String" in line:
            context = line
            if i > 0:
                context = lines[i - 1] + "\n" + context
            assert "@NotBlank" in context, (
                "jdRaw field lost its @NotBlank guard:\n%s" % context
            )
            break
    else:
        assert False, "jdRaw field not found in JdSuggestionsRequest"


# --------------------------------------------------------------------------- case 5: useAnalyzeJd sends rawText

def test_use_analyze_jd_sends_rawtext():
    bodies = ts_call_bodies("useAnalyzeJd", actions_source())
    assert len(bodies) >= 1, "useAnalyzeJd not found in actions.ts"
    body = bodies[0]
    # useAnalyzeJd uses api.create(endpoint, data) - extract the second argument
    create_match = re.search(r"api\.create<[^>]*>\([^,]+,\s*\{(.*?)\}", body, re.DOTALL)
    assert create_match, "cannot find the api.create call in useAnalyzeJd"
    data_obj = create_match.group(1).strip()
    # Handle both shorthand { rawText } and explicit { rawText: value } forms
    if ":" not in data_obj:
        # Shorthand form: just property names separated by commas
        props = [p.strip() for p in data_obj.split(",") if p.strip()]
    else:
        # Explicit form: extract property names before colons
        props = re.findall(r"(?:^|,)\s*(\w+)\s*:", data_obj, re.M)
    unexpected = [p for p in props if p not in ("rawText",)]
    assert not unexpected, (
        "useAnalyzeJd POST data has extra fields: %s (expected only rawText)" % unexpected
    )
    assert "rawText" in props, "useAnalyzeJd no longer sends rawText in POST data"
    # Check it's sent to the correct endpoint
    assert "jdAnalyze" in body, "useAnalyzeJd no longer uses jdAnalyze endpoint"


# --------------------------------------------------------------------------- case 6: useResumeSuggestions sends jdRaw and resumeVersionId

def test_use_resume_suggestions_sends_jdraw_and_resume_version_id():
    bodies = ts_call_bodies("useResumeSuggestions", actions_source())
    assert len(bodies) >= 1, "useResumeSuggestions not found in actions.ts"
    func_body = bodies[0]
    # Check that jdRaw is sent as jdRaw: body.jdRaw
    assert "jdRaw: body.jdRaw" in func_body, "useResumeSuggestions no longer sends jdRaw in POST body"
    # Check that resumeVersionId is sent via ...field() helper
    assert 'field("resumeVersionId"' in func_body or "field('resumeVersionId'" in func_body, (
        "useResumeSuggestions no longer sends resumeVersionId in POST body"
    )
    # Check it's sent to the correct endpoint
    assert "jdSuggestions" in func_body, "useResumeSuggestions no longer uses jdSuggestions endpoint"


# --------------------------------------------------------------------------- case 7: the endpoints are named correctly

def test_the_client_endpoint_map_names_both_routes():
    src = read(ENDPOINTS)
    assert "jdAnalyze:" in src, "jdAnalyze endpoint missing from endpoints.ts"
    assert "jdSuggestions:" in src, "jdSuggestions endpoint missing from endpoints.ts"
    assert '"/jds"' in src, "jdAnalyze path changed"
    assert '"/jds/suggestions"' in src, "jdSuggestions path changed"


# --------------------------------------------------------------------------- case 8: the mutation failure paths are announced

def test_the_jd_mutations_announce_their_failures():
    # useAnalyzeJd
    bodies_analyze = ts_call_bodies("useAnalyzeJd", actions_source())
    assert len(bodies_analyze) >= 1
    body_analyze = bodies_analyze[0]
    assert "onError:" in body_analyze, "useAnalyzeJd onError handler missing"
    assert 'fail(' in body_analyze, "useAnalyzeJd onError does not call fail()"
    assert 'fail("failures.jdAnalysis")' in body_analyze, "useAnalyzeJd failure key changed"

    # useResumeSuggestions
    bodies_suggest = ts_call_bodies("useResumeSuggestions", actions_source())
    assert len(bodies_suggest) >= 1
    body_suggest = bodies_suggest[0]
    assert "onError:" in body_suggest, "useResumeSuggestions onError handler missing"
    assert 'fail(' in body_suggest, "useResumeSuggestions onError does not call fail()"
    assert 'fail("failures.suggestionsFetch")' in body_suggest, (
        "useResumeSuggestions failure key changed"
    )
