"""The resume-version controller's request contract: one query parameter, two readers.

``ResumeVersionController`` is the first controller in this gate family with **no request
bodies at all** -- both routes are reads, and the whole request contract is the query
parameter the list route binds:

1. ``GET /resume-versions`` -- ``@RequestParam("resumeId") UUID resumeId``, explicitly
   named and required (no ``required = false``, no ``defaultValue``). The frontend reaches
   it through ``fetchResumeVersions(resumeId)`` in ``resources.ts``, which sends the key as
   a shorthand ``{ resumeId }`` object to ``endpoints.resumeVersions``.

2. ``GET /resume-versions/{id}`` -- an unnamed ``@PathVariable`` whose parameter name must
   stay the template's variable name. ``endpoints.resumeVersion`` (singular) maps the path,
   and a census over ``frontend/src`` shows it ships with **zero clients** -- the route is
   served but never fetched.

This gate pins the join that no earlier gate reads: the Java ``@RequestParam`` literal and
the JS object key are the same string, so a rename on either side alone fails here. It does
NOT re-pin what earlier gates already hold: the ``/api/v1`` + member path join (#192's
mapper-ship gate), the ``["resume", resumeId, "versions"]`` query key and the detail
screen's ``useResumeVersions(id)`` call (#197), or the mapper's per-item reads (#122/#192).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/resume/web/ResumeVersionController.java"
RESOURCES = "frontend/src/lib/hooks/resources.ts"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"
PAGE = "frontend/src/app/(app)/resumes/[id]/page.tsx"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


# --------------------------------------------------------------------------- helpers

@lru_cache(maxsize=1)
def controller_source() -> str:
    return read(CONTROLLER)


@lru_cache(maxsize=1)
def resources_source() -> str:
    return read(RESOURCES)


def ts_call_bodies(fn_name: str, source: str) -> list[str]:
    """Return the text of every top-level ``export function fn_name(...) { ... }`` block."""
    blocks = []
    pattern = (
        r"export\s+(?:async\s+)?function\s+" + fn_name + r"\s*\([^)]*\)\s*(?::\s*[^{;]+)?\s*\{"
    )
    for m in re.finditer(pattern, source):
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


def braced_arg_after(source: str, marker: str) -> str:
    """Return the balanced ``{...}`` block starting at the first ``{`` after ``marker``."""
    i = source.find(marker)
    assert i != -1, "marker not found: %s" % marker
    start = source.index("{", i)
    depth = 0
    for j in range(start, len(source)):
        ch = source[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start : j + 1]
    raise AssertionError("unbalanced braces after %s" % marker)


def object_literal_keys(block: str) -> list[str]:
    """Property names of an object literal, including shorthand entries.

    The lookahead accepts end-of-block so a lone shorthand ``{ key }`` -- no ``:``, no
    trailing comma -- still reads as one key.
    """
    inner = block[1:-1]
    return re.findall(r"(?:^|,)\s*([A-Za-z_$][\w$]*)\s*(?=:|,|$)", inner)


# --------------------------------------------------------------------------- case 1: two reads, no bodies

def test_the_versions_controller_carries_two_reads_and_no_request_bodies():
    src = controller_source()
    assert src.count("@RequestBody") == 0, (
        "ResumeVersionController grew a request body; the rest of this gate only covers "
        "the query-parameter wire"
    )
    assert src.count("@RequestParam") == 1, (
        "expected exactly one @RequestParam binding, found %d" % src.count("@RequestParam")
    )
    assert src.count("@PathVariable") == 1, (
        "expected exactly one @PathVariable binding, found %d" % src.count("@PathVariable")
    )
    assert src.count("@GetMapping") == 2, (
        "expected both routes to be GETs, found %d @GetMapping" % src.count("@GetMapping")
    )


# --------------------------------------------------------------------------- case 2: the required UUID binding

def test_the_list_route_binds_resume_id_as_a_required_uuid_query_parameter():
    src = controller_source()
    m = re.search(r"@RequestParam\(([^)]*)\)\s*(\w+)\s+(\w+)", src)
    assert m, "no single-line @RequestParam binding left in ResumeVersionController"
    args, typ, _param = m.groups()
    name = re.search(r'"([^"]+)"', args)
    assert name, "the query parameter binds no explicit name literal: @RequestParam(%s)" % args
    assert "required" not in args, (
        "the binding declares a requiredness modifier, so a missing resumeId stops being a "
        "400: @RequestParam(%s)" % args
    )
    assert "defaultValue" not in args, (
        "the binding declares a defaultValue, so a missing resumeId silently queries "
        "something else: @RequestParam(%s)" % args
    )
    assert typ == "UUID", (
        "the query parameter drifted from UUID to %s; a non-UUID resumeId now reaches the "
        "service as text" % typ
    )


# --------------------------------------------------------------------------- case 3: the key join

def test_the_client_key_and_the_controller_name_are_the_same_literal():
    src = controller_source()
    m = re.search(r"@RequestParam\(([^)]*)\)", src)
    assert m, "ResumeVersionController no longer declares a @RequestParam binding"
    name = re.search(r'"([^"]+)"', m.group(1))
    assert name, "the @RequestParam binding names nothing explicitly: %s" % m.group(1)
    java_key = name.group(1)

    bodies = ts_call_bodies("fetchResumeVersions", resources_source())
    assert len(bodies) == 1, "expected exactly one fetchResumeVersions, found %d" % len(bodies)
    block = braced_arg_after(bodies[0], "endpoints.resumeVersions, ")
    js_keys = object_literal_keys(block)
    assert js_keys == [java_key], (
        "the query wire drifted: the browser sends %s to /resume-versions, the controller "
        "binds %r" % (js_keys, java_key)
    )


# --------------------------------------------------------------------------- case 4: the fetch call's shape

def test_the_fetch_call_is_one_get_on_the_versions_member_with_the_shorthand_key():
    bodies = ts_call_bodies("fetchResumeVersions", resources_source())
    assert len(bodies) == 1, "expected exactly one fetchResumeVersions, found %d" % len(bodies)
    assert "api.get<unknown>(endpoints.resumeVersions, { resumeId })" in bodies[0], (
        "fetchResumeVersions no longer issues one GET with the shorthand resumeId key:\n%s"
        % bodies[0]
    )


# --------------------------------------------------------------------------- case 5: the hook's enabled guard

def test_the_versions_hook_is_disabled_until_a_resume_id_exists():
    bodies = ts_call_bodies("useResumeVersions", resources_source())
    assert len(bodies) == 1, "expected exactly one useResumeVersions, found %d" % len(bodies)
    body = bodies[0]
    assert "enabled: Boolean(resumeId)" in body, (
        "useResumeVersions lost its enabled guard and can now fire with a null id:\n%s" % body
    )
    assert "queryFn: () => fetchResumeVersions(resumeId!)" in body, (
        "useResumeVersions no longer fetches through fetchResumeVersions(resumeId!)"
    )


# --------------------------------------------------------------------------- case 6: the panel's failure affordance

def test_the_detail_screen_shows_a_failed_versions_read_and_offers_a_retry():
    page = read(PAGE)
    assert "versionsQ.isError ? (" in page, (
        "the versions panel no longer branches on its own query's failure; a 500 would "
        "render as 'No stored versions yet'"
    )
    assert "error={versionsQ.error}" in page, (
        "the versions panel no longer forwards the query's error to its ErrorState"
    )
    assert "onRetry={() => void versionsQ.refetch()}" in page, (
        "the versions panel's retry no longer refetches the versions query"
    )


# --------------------------------------------------------------------------- case 7: user-scoped forwarding

def test_the_controller_forwards_the_user_scope_and_the_bound_ids():
    src = controller_source()
    assert "return resumes.listVersions(user.id(), resumeId);" in src, (
        "list no longer forwards (user.id(), resumeId); the resume scope or the auth "
        "scope moved"
    )
    assert "return resumes.versionMeta(user.id(), id);" in src, (
        "get no longer forwards (user.id(), id); the resume scope or the auth scope moved"
    )


# --------------------------------------------------------------------------- case 8: the path-variable name

def test_the_item_route_takes_its_path_variable_from_the_template():
    src = controller_source()
    tmpl = re.search(r'@GetMapping\("/\{(\w+)\}"\)', src)
    assert tmpl, 'no single-segment @GetMapping("/{var}") template in the controller'
    bound = re.search(r'@PathVariable(?:\(\s*(?:value\s*=\s*)?"([^"]+)"\s*\))?\s+\w+\s+(\w+)', src)
    assert bound, "no @PathVariable parameter in the controller"
    effective = bound.group(1) or bound.group(2)
    assert effective == tmpl.group(1), (
        "the path template names {%s} but the binding reads `%s`" % (tmpl.group(1), effective)
    )


# --------------------------------------------------------------------------- case 9: the client-free singular route

def test_the_single_version_route_ships_with_no_client():
    root = ROOT / "frontend" / "src"
    files = sorted(list(root.rglob("*.ts")) + list(root.rglob("*.tsx")))
    assert len(files) >= 100, (
        "the census walked %d files; the floor is 100, so this is a walk bug, not an "
        "absence" % len(files)
    )
    hits = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(r"resumeVersion\b", text):
            hits.append((p.relative_to(ROOT).as_posix(), text.count("\n", 0, m.start()) + 1))
    assert len(hits) == 1, (
        "the singular endpoint member resumeVersion has %d references; if a real client "
        "appeared, pin it instead of re-freezing this census:\n%s" % (len(hits), hits)
    )
    where, line = hits[0]
    assert where == "frontend/src/lib/api/endpoints.ts", (
        "the only resumeVersion reference moved to %s:%d" % (where, line)
    )
    assert "resumeVersion: (id: string) => `/resume-versions/${seg(id)}`," in read(ENDPOINTS), (
        "the member's own template changed; if it gained a client, re-home this census"
    )
