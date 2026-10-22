"""What a 404 means on this app, and who is told the wrong version of it.

``components/common/query-boundary.tsx`` states its own contract in its docstring: "the single async
contract used by every surface". The same file decides, from one boolean, whether a user reads an
error or a designed empty state with a sentence about version mismatch. Both halves of that promise
are measurable, and both are false where they matter:

* Only 5 of the 16 ``(app)`` screens route a query through the boundary. Four route the same
  pending/error/empty decision through ``components/common/module-view.tsx``, which re-implements it
  in its own JSX, and seven decide it inline from their own ``isPending``/``error`` flags. Each of the
  two shared shells claims universality in its own docstring -- "the single async contract used by
  every surface" and "the shared async list shell for every (app) resource page" -- and they answer
  the same status with opposite states, so this file pins which screens spend which.
* ``isEndpointMissing`` returns true for *any* 404 (and for a 501 no server in this repo produces),
  and ``ModuleView``'s own rule is the same status test with the opposite verdict:
  ``error.isNotFound`` sends it to the screen's "nothing here yet" hint.
  The backend answers 404 from fifteen places -- fourteen ``ApiErrorCode`` constants that mean "this
  record is not there" and one ``NoResourceFoundException`` handler that means "this route is not
  served" -- and it puts the distinguishing name in ``error.code`` on the wire. ``ApiError`` keeps
  that code; neither shell reads it. So a deleted agent run, opened at ``/activity/[id]``,
  renders the screen's "This run is gone" title under "A route this screen needs answered 404, so
  this frontend and the backend it is talking to are different versions", next to a "Check again"
  button, replacing the description and the "Back to activity" action that screen authored for
  exactly that case. Retrying cannot help: the route is served and the record is gone. And on the
  four ``ModuleView`` screens the skew that sentence was written for is reported as an empty list.

This file characterises that -- the repair belongs to whoever owns the boundary's copy, and the
screens are being edited concurrently -- and pins both ends so the fold cannot be reintroduced
silently: the enum's status table read from the Java source, the client's ``isNotFound`` read from
the TS source, and the branch order read from the boundary itself.
"""

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONT = ROOT / "frontend" / "src"
APP = FRONT / "app"
JAVA = ROOT / "backend" / "src" / "main" / "java"
PYSRC = ROOT / "ai-service" / "app"

BOUNDARY = "frontend/src/components/common/query-boundary.tsx"
MODULE_VIEW = "frontend/src/components/common/module-view.tsx"
MISSING = "frontend/src/lib/api/missing-endpoint.ts"
CLIENT = "frontend/src/lib/api/client.ts"
NORMALIZE = "frontend/src/lib/api/normalize.ts"
CODES = "backend/src/main/java/com/careeros/common/ApiErrorCode.java"
HANDLER = "backend/src/main/java/com/careeros/common/GlobalExceptionHandler.java"
RUN_DETAIL = "frontend/src/app/(app)/activity/[id]/page.tsx"

BOUNDARY_SCREENS = [
    "frontend/src/app/(app)/activity/[id]/page.tsx",
    "frontend/src/app/(app)/dashboard/page.tsx",
    "frontend/src/app/(app)/interviews/page.tsx",
    "frontend/src/app/(app)/jobs/page.tsx",
    "frontend/src/app/(app)/resumes/page.tsx",
]
# Screens that hand their query to the second shell, module-view.tsx.
MODULE_VIEW_SCREENS = [
    "frontend/src/app/(app)/activity/page.tsx",
    "frontend/src/app/(app)/applications/page.tsx",
    "frontend/src/app/(app)/companies/page.tsx",
    "frontend/src/app/(app)/knowledge/page.tsx",
    "frontend/src/app/(app)/networking/page.tsx",
]
# The remaining screens: neither shell, so they branch on their own query flags.
# The growth page joined with 10.3: its report is a mutation's answer, so it branches
# on its own `isPending` rather than either shell.
OWN_FLAG_SCREENS = [
    "frontend/src/app/(app)/companies/[id]/page.tsx",
    "frontend/src/app/(app)/copilot/page.tsx",
    "frontend/src/app/(app)/growth/page.tsx",
    "frontend/src/app/(app)/interviews/[id]/page.tsx",
    "frontend/src/app/(app)/interviews/[id]/report/page.tsx",
    "frontend/src/app/(app)/jobs/[id]/page.tsx",
    "frontend/src/app/(app)/resumes/[id]/page.tsx",
    "frontend/src/app/(app)/settings/page.tsx",
]
NF_CODES = [
    "APPLICATION_NOT_FOUND", "COMPANY_NOT_FOUND", "CONVERSATION_NOT_FOUND", "DOCUMENT_NOT_FOUND",
    "JD_NOT_FOUND", "JOB_NOT_FOUND", "MATCH_NOT_FOUND", "NOTE_NOT_FOUND", "NOT_FOUND",
    "RESUME_FILE_MISSING", "RESUME_NOT_AVAILABLE", "RESUME_NOT_FOUND", "RESUME_NOT_INGESTED",
    "RESUME_NOT_PARSED", "RESUME_NOT_TAILABLE", "RUN_NOT_FOUND", "SESSION_NOT_FOUND",
    "SOURCE_NOT_FOUND", "VERSION_NOT_FOUND",
]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def stmt(text: str, needle: str) -> str:
    hits = [line.strip() for line in text.splitlines() if needle in line]
    assert len(hits) == 1, "%r matches %d lines, so the claim does not name one statement" % (needle, len(hits))
    return hits[0]


@lru_cache(maxsize=None)
def ts_files() -> list:
    out = sorted(p.relative_to(ROOT).as_posix() for p in FRONT.rglob("*.ts*"))
    assert len(out) >= 100, "the frontend walk found %d files" % len(out)
    return out


@lru_cache(maxsize=None)
def app_screens() -> list:
    out = sorted(p.relative_to(ROOT).as_posix() for p in APP.rglob("page.tsx"))
    assert len(out) == 23, "app/%s page.tsx files, not the 23 this file walks" % len(out)
    return [rel for rel in out if "/(app)/" in rel]


@lru_cache(maxsize=None)
def boundary_users() -> list:
    out = []
    for rel in app_screens():
        if re.search(r"<(?:QueryBoundary|SectionBoundary)\b", read(rel)):
            out.append(rel)
    return sorted(out)


@lru_cache(maxsize=None)
def module_view_users() -> list:
    return sorted(rel for rel in app_screens() if re.search(r"<ModuleView\b", read(rel)))


@lru_cache(maxsize=None)
def own_flag_screens() -> list:
    """Screens that branch on a query flag themselves, outside either shell."""
    out = []
    for rel in app_screens():
        if re.search(r"\.(?:isError|isPending|isLoading|error)\b", read(rel)):
            out.append(rel)
    return sorted(out)


def not_found_codes() -> list:
    """The enum constants the backend answers with status 404, read from the declaration itself."""
    text = read(CODES)
    out = [m.group(1) for m in re.finditer(r"^\s*([A-Z_]+)\(HttpStatus\.NOT_FOUND\)", text, re.M)]
    assert out, "the enum walk read no NOT_FOUND constants out of %s" % CODES
    return out


def handler_404() -> str:
    """The body the Spring handler answers for a route that is not mapped at all."""
    text = read(HANDLER)
    start = text.index("@ExceptionHandler(NoResourceFoundException.class)")
    window = text[start: start + 400]
    assert "HttpStatus.NOT_FOUND" in window, "the unmapped-route handler no longer answers 404: %s" % window
    return " ".join(window.split())


def status_of(status: str) -> list:
    text = read(CODES)
    return [m.group(1) for m in re.finditer(r"^\s*([A-Z_]+)\(HttpStatus\.%s\)" % status, text, re.M)]


# ------------------------------------------------------------------ cases


def test_the_contract_called_single_is_used_by_five_of_the_eighteen_app_screens():
    screens = app_screens()
    assert len(screens) == 18, "%d screens under app/(app), not 18" % len(screens)
    users = boundary_users()
    assert users == BOUNDARY_SCREENS, "the boundary is used by %s" % [u.split("app/")[-1] for u in users]
    assert stmt(read(BOUNDARY), "single async contract used by every surface") == \
        "* QueryBoundary — the single async contract used by every surface:", (
        "the file's own claim about its reach moved, so the set above needs re-measuring, not this pin"
    )
    non = [s for s in screens if s not in users]
    assert len(non) == 13, "%d screens render without the contract this file calls single" % len(non)


def test_thirteen_of_the_eighteen_screens_decide_the_async_state_somewhere_else():
    screens = app_screens()
    b, mv = boundary_users(), module_view_users()
    assert mv == MODULE_VIEW_SCREENS, "ModuleView is spent by %s" % [u.split("app/")[-1] for u in mv]
    assert not set(b) & set(mv), "a screen spends both shells, so the split below double-counts it"
    neither = [s for s in screens if s not in b and s not in mv]
    assert neither == OWN_FLAG_SCREENS, "the screens on neither shell are %s" % [u.split("app/")[-1] for u in neither]
    flags = set(own_flag_screens())
    bare = [s for s in neither if s not in flags]
    assert bare == [], "%s render a query with no failure branch at all -- this file used to claim so" % bare
    assert len(b) + len(mv) + len(neither) == len(screens) == 18, "the three sets stopped covering the app"
    assert stmt(read(MODULE_VIEW), "shared async list shell for every") == \
        "* ModuleView \u2014 the shared async list shell for every (app) resource page.", (
        "the second shell's own universality claim moved, so the 5/4/7 split above needs re-measuring")


def test_the_offline_affordance_has_been_rendered_by_nobody():
    text = read(BOUNDARY)
    assert stmt(text, "export function EndpointOffline") == \
        "export function EndpointOffline({ name, className }: { name: string; className?: string }) {", (
        "the offline hint's own signature moved, so the caller census below proves nothing")
    refs = []
    for rel in ts_files():
        n = len(re.findall(r"\bEndpointOffline\b", read(rel)))
        if n:
            refs.append((rel, n))
    assert refs == [(BOUNDARY, 1)], "EndpointOffline is spelled in %s -- the declaration itself is the only reference" % refs
    assert "isn&apos;t connected yet" in text, "the dead hint's sentence changed; the claim about it is stale"


def test_is_endpoint_missing_reads_status_only_and_the_client_keeps_the_code_it_ignores():
    body = read(BOUNDARY)[read(BOUNDARY).index("export function isEndpointMissing"):]
    body = body[: body.index("\n}") + 2]
    assert stmt(body, "return error instanceof ApiError") == \
        "return error instanceof ApiError && (error.isNotFound || error.status === 501);", (
        "the predicate that decides error-vs-empty changed shape; re-read which fields it consults")
    assert "code" not in body, "the predicate reads a code now, so the fold this file records may be closed"
    client = read(CLIENT)
    cls = client[client.index("export class ApiError"):]
    cls = cls[: cls.index("\n}")]
    assert stmt(cls, "code: string;") == "code: string;", "ApiError no longer declares a code field"
    assert stmt(cls, "this.code =") == "this.code = code;", "ApiError no longer keeps the code off the envelope"
    assert stmt(cls, "constructor(") == \
        "constructor(code: string, message: string, status: number, details?: unknown) {", (
        "the client's error no longer arrives with a code, so the fold this file records has a different cause")
    isnf = client[client.index("get isNotFound"):]
    assert stmt(isnf[: isnf.index("\n    }") + 6], "return this.status ===") == "return this.status === 404;", (
        "isNotFound consults something beyond the status now")


def test_the_backend_answers_404_for_records_and_for_routes_in_the_same_status():
    codes = not_found_codes()
    assert sorted(codes) == NF_CODES, "%d codes answer 404: %s" % (len(codes), sorted(codes))
    assert len(codes) == len(set(codes)) == 19, "the 404 table moved; this file reads 19 constants"
    assert status_of("BAD_REQUEST") and status_of("FORBIDDEN"), "the enum walk is blind -- it read no other status"
    record = [c for c in codes if c != "NOT_FOUND"]
    assert len(record) == 18, "%d of the 404 codes name a record, not a route" % len(record)
    window = handler_404()
    assert "ApiErrorCode.NOT_FOUND" in window and "Resource not found" in window, (
        "the unmapped-route handler no longer answers the bare NOT_FOUND code: %s" % window)


def test_the_501_half_of_the_predicate_has_no_producer_in_either_service():
    java = sorted(p.relative_to(ROOT).as_posix() for p in JAVA.rglob("*.java"))
    py = sorted(p.relative_to(ROOT).as_posix() for p in PYSRC.rglob("*.py"))
    assert len(java) >= 150 and len(py) >= 60, "the server walks read %d java, %d python files" % (len(java), len(py))
    assert status_of("NOT_FOUND"), "control: the enum scan must be able to find a status before it claims an absence"
    hits = [rel for rel in java + py if "NOT_IMPLEMENTED" in read(rel) or re.search(r"\b501\b", read(rel))]
    assert hits == [], "something answers 501 now: %s" % hits


def test_the_run_a_user_opens_by_url_id_gets_the_version_sentence():
    text = read(RUN_DETAIL)
    assert stmt(text, "queryKey: [") == 'queryKey: ["activity", "run-detail", id],', (
        "the detail query's key moved; check whether its id still comes from the URL")
    assert stmt(text, "const id =") == "const id = params?.id ?? null;", "the run id no longer comes from the path"
    assert 'endpoints.activityRun(id!)' in text, "the detail query no longer asks for one run by id"
    assert RUN_DETAIL in BOUNDARY_SCREENS and re.search(r"<QueryBoundary\b", text), (
        "this screen no longer spends the contract, so the fold below is unreachable here")
    assert "notLive" not in text, "the screen authors its own not-live copy now; the fallback is no longer what it shows"
    empty = text[text.index("empty={{"):]
    empty = empty[: empty.index("\n        }}")]
    # The screen's own record-gone copy reads from the locale table for the
    # link, so the gate accepts the key it reads rather than the English copy.
    assert 'title: "This run is gone"' in empty \
        and ('t("activity.detail.backToActivity")' in empty or "Back to activity" in empty), (
        "the screen's own record-gone copy moved: %s" % " ".join(empty.split())[:200])
    boundary = read(BOUNDARY)
    assert stmt(boundary, "description={notLive?.description ??") == \
        "description={notLive?.description ?? missingEndpointMessage()}", (
        "the boundary no longer falls back to the version sentence, so this finding needs re-measuring")
    assert stmt(read(MISSING), 'const route =') == (
        'const route = path ? `${path} answered 404` : "A route this screen needs answered 404";'), (
        "the fallback's own wording moved")
    assert "different versions" in read(MISSING) and "Nothing is shown in place of the real data" in read(MISSING), (
        "the sentence this finding quotes is no longer the sentence the screen shows")
    # The retry button's label reads from the locale table now, so the gate
    # accepts the key the boundary reads rather than the English copy.
    assert 't("common.checkAgain")' in boundary or "Check again" in boundary, \
        "the retry button this finding names is spelled differently now"


def test_the_second_shell_answers_the_same_404_with_the_screen_s_own_empty_hint():
    mv = read(MODULE_VIEW)
    assert stmt(mv, "404 empty-state") == \
        "* Enforces: skeleton \u2192 content | 404 empty-state | error+retry. No fake data.", (
        "the second shell's own statement of what it does with a 404 moved")
    assert stmt(mv, "const notFound =") == \
        "const notFound = query.error instanceof ApiError && query.error.isNotFound;", (
        "ModuleView's 404 rule changed shape; re-read which fields it consults")
    assert "code" not in stmt(mv, "const notFound ="), "the second shell reads a code now, so its fold is closing too"
    assert mv.index("query.isError ? (") < mv.index("notFound ? ("), (
        "the 404 test no longer sits inside the error branch, so it is not a verdict on failures")
    branch = mv[mv.index("notFound ? ("): mv.index("<ErrorState")]
    assert "title={emptyHint.title}" in branch and "ctaHref" in branch, (
        "a 404 no longer renders the screen's designed empty hint: %s" % " ".join(branch.split())[:200])
    assert mv[: mv.index("<ErrorState")].rstrip().endswith(") : ("), (
        "ErrorState is no longer the else arm of the same 404 test, so the claim above is a different one")
    assert "isEmptyPage" not in mv, "the two shells now share one empty test; re-read the claim below"
    assert "!query.data?.items.length" in mv, (
        "ModuleView's second implementation of 'has no rows' moved")
    assert "missingEndpointMessage" not in mv and "notLive" not in mv, (
        "ModuleView gained a not-live path, so a route-absent 404 is no longer read as an empty list")


def test_this_gate_reads_the_envelope_and_the_branches_it_claims():
    boundary = read(BOUNDARY)
    order = [boundary.index(x) for x in ("if (query.isPending)", "if (query.isError)", "if (isEmptyPage(query.data))", "return children(")]
    assert order == sorted(order), "the boundary's branch order changed, so which state wins is a different claim"
    empty = boundary[boundary.index("export function isEmptyPage"): boundary.index("export interface")]
    clauses = re.findall(r"if \((.*)\)", empty)
    assert clauses == ["data == null", "Array.isArray(data)"], (
        "isEmptyPage's own clauses moved: %s" % clauses)
    assert "(data as { items?: unknown }).items" in empty, "the predicate no longer recognises the items envelope"
    assert re.search(r"^\s*items: T\[\];", read(NORMALIZE), re.M), "normalize's page type no longer states items"
    assert "items: arr.map(map)," in read(NORMALIZE), "the page builder no longer writes items"
    for rel in (BOUNDARY, MODULE_VIEW, MISSING, CLIENT, NORMALIZE, CODES, HANDLER, RUN_DETAIL):
        assert (ROOT / rel).exists(), "%s is not where this file reads it" % rel
    assert len(not_found_codes()) == 14 and len(boundary_users()) == 5
    assert len(module_view_users()) == 5 and len(OWN_FLAG_SCREENS) == 8
