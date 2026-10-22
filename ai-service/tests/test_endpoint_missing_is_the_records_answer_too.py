"""What a 404 means on this app, and who is still told the wrong version of it.

``components/common/query-boundary.tsx`` states its own contract in its docstring: "the single async
contract used by every surface". The same file decides, from one boolean, whether a user reads an
error or a designed empty state with a sentence about version mismatch. Both halves of that promise
are measurable, and this file pins them:

* Only 5 of the 24 ``(app)`` screens route a query through the boundary. Five route the same
  pending/error/empty decision through ``components/common/module-view.tsx``, which re-implements it
  in its own JSX, and fourteen decide it inline from their own ``isPending``/``error`` flags. Each of
  the two shared shells claims universality in its own docstring -- "the single async contract used
  by every surface" and "the shared async list shell for every (app) resource page" -- and they answer
  the same status with opposite states, so this file pins which screens spend which.
* ``isEndpointMissing`` reads the *code* now: the route that is not served answers ``NOT_FOUND``,
  and every record that is gone answers its own code, so the boundary no longer tells a reader
  whose job was deleted that their build is the wrong version. ``ModuleView``'s own rule is still
  the status test with the opposite verdict: ``error.isNotFound`` sends it to the screen's
  "nothing here yet" hint.
  The backend answers 404 from twenty-five places -- twenty-four ``ApiErrorCode`` constants (one
  that means "this route is not served", twenty-three that name a record) and one
  ``NoResourceFoundException`` handler that means "this route is not served" -- and it puts the
  distinguishing name in ``error.code`` on the wire. ``ApiError`` keeps that code; the second shell
  does not read it. So a deleted agent run, opened at ``/activity/[id]`` on a ``ModuleView`` screen,
  renders the screen's "This run is gone" title under "A route this screen needs answered 404, so
  this frontend and the backend it is talking to are different versions", next to a "Check again"
  button, replacing the description and the "Back to activity" action that screen authored for
  exactly that case. Retrying cannot help: the route is served and the record is gone.

This file characterises that -- the repair belongs to whoever owns the second shell's copy -- and
pins both ends so the fold cannot be reintroduced silently: the enum's status table read from the
Java source, the client's ``isNotFound`` read from the TS source, and the branch order read from
the boundary itself.
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
    "frontend/src/app/(app)/analysis/page.tsx",
    "frontend/src/app/(app)/companies/[id]/page.tsx",
    "frontend/src/app/(app)/copilot/page.tsx",
    "frontend/src/app/(app)/data/page.tsx",
    "frontend/src/app/(app)/growth/page.tsx",
    "frontend/src/app/(app)/ingestion/page.tsx",
    "frontend/src/app/(app)/interviews/[id]/page.tsx",
    "frontend/src/app/(app)/interviews/[id]/report/page.tsx",
    "frontend/src/app/(app)/jobs/[id]/page.tsx",
    "frontend/src/app/(app)/monitoring/page.tsx",
    "frontend/src/app/(app)/offers/page.tsx",
    "frontend/src/app/(app)/rate-limit/page.tsx",
    "frontend/src/app/(app)/resumes/[id]/page.tsx",
    "frontend/src/app/(app)/settings/page.tsx",
]
NF_CODES = [
    "AI_SERVICE_NOT_FOUND", "APPLICATION_NOT_FOUND", "COMPANY_NOT_FOUND", "CONTACT_NOT_FOUND",
    "CONVERSATION_NOT_FOUND", "DOCUMENT_KEY_NOT_OWNED", "DOCUMENT_NOT_FOUND", "JD_NOT_FOUND",
    "JOB_NOT_FOUND", "MATCH_NOT_FOUND", "NOTE_NOT_FOUND", "NOT_FOUND", "PROFILE_NOT_FOUND",
    "RESUME_FILE_MISSING", "RESUME_NOT_AVAILABLE", "RESUME_NOT_FOUND", "RESUME_NOT_INGESTED",
    "RESUME_NOT_PARSED", "RESUME_NOT_TAILABLE", "RESUME_VERSION_MISSING", "RUN_NOT_FOUND",
    "SESSION_NOT_FOUND", "SOURCE_NOT_FOUND", "USER_NOT_FOUND", "VERSION_NOT_FOUND",
    "VERSION_NOT_OWNED",
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
    assert len(out) == 29, "app/%s page.tsx files, not the 29 this file walks" % len(out)
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


def test_the_contract_called_single_is_used_by_five_of_the_twenty_four_app_screens():
    screens = app_screens()
    assert len(screens) == 24, "%d screens under app/(app), not 24" % len(screens)
    users = boundary_users()
    assert users == BOUNDARY_SCREENS, "the boundary is used by %s" % [u.split("app/")[-1] for u in users]
    assert stmt(read(BOUNDARY), "single async contract used by every surface") == \
        "* QueryBoundary — the single async contract used by every surface:", (
        "the file's own claim about its reach moved, so the set above needs re-measuring, not this pin"
    )
    non = [s for s in screens if s not in users]
    assert len(non) == 19, "%d screens render without the contract this file calls single" % len(non)


def test_nineteen_of_the_twenty_four_screens_decide_the_async_state_somewhere_else():
    screens = app_screens()
    b, mv = boundary_users(), module_view_users()
    assert mv == MODULE_VIEW_SCREENS, "ModuleView is spent by %s" % [u.split("app/")[-1] for u in mv]
    assert not set(b) & set(mv), "a screen spends both shells, so the split below double-counts it"
    neither = [s for s in screens if s not in b and s not in mv]
    assert neither == OWN_FLAG_SCREENS, "the screens on neither shell are %s" % [u.split("app/")[-1] for u in neither]
    flags = set(own_flag_screens())
    bare = [s for s in neither if s not in flags]
    assert bare == [], "%s render a query with no failure branch at all -- this file used to claim so" % bare
    assert len(b) + len(mv) + len(neither) == len(screens) == 24, "the three sets stopped covering the app"
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


def test_the_missing_endpoint_rule_reads_the_code_and_the_client_keeps_it():
    body = read(BOUNDARY)[read(BOUNDARY).index("export function isEndpointMissing"):]
    body = body[: body.index("\n}") + 2]
    assert stmt(body, "if (!(error instanceof ApiError))") == \
        "if (!(error instanceof ApiError)) return false;", (
        "the predicate that decides error-vs-empty changed shape; re-read which fields it consults")
    assert stmt(body, "return error.code === ") == 'return error.code === "NOT_FOUND";', (
        "the predicate no longer names the route's own code, so a record that is gone reads as a "
        "missing route again")
    assert "error.isNotFound" not in body, (
        "the predicate consults the status alone again, so a record that is gone is reported as a "
        "version mismatch: %s" % " ".join(body.split()))
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
    assert len(codes) == len(set(codes)) == 26, "the 404 table moved; this file reads 26 constants"
    assert status_of("BAD_REQUEST") and status_of("FORBIDDEN"), "the enum walk is blind -- it read no other status"
    record = [c for c in codes if c != "NOT_FOUND"]
    assert len(record) == 25, "%d of the 404 codes name a record, not a route" % len(record)
    window = handler_404()
    assert "ApiErrorCode.NOT_FOUND" in window and "Resource not found" in window, (
        "the unmapped-route handler no longer answers the bare NOT_FOUND code: %s" % window)


def test_the_501_half_of_the_predicate_has_one_producer_the_browser_never_sees():
    """The 501 exists now, and it does not mean what the boundary's 501 branch says.

    The ai-service answers 501 for exactly one thing: the PDF converter is an
    optional dependency and it is not installed. That is a fact about the
    *deployment*, not about the route -- the route is served. The Java backend
    -- the only thing the browser talks to -- translates the upstream's 501
    into its own 502, so the browser never sees a 501 at all, and the
    boundary's 501 branch is the defensive rule it was written as.
    """
    java = sorted(p.relative_to(ROOT).as_posix() for p in JAVA.rglob("*.java"))
    py = sorted(p.relative_to(ROOT).as_posix() for p in PYSRC.rglob("*.py"))
    assert len(java) >= 150 and len(py) >= 60, "the server walks read %d java, %d python files" % (len(java), len(py))
    assert status_of("NOT_FOUND"), "control: the enum scan must be able to find a status before it claims an absence"
    assert not status_of("NOT_IMPLEMENTED"), "the enum declares a 501 now, so the browser can be told one"
    hits = [rel for rel in java + py if "NOT_IMPLEMENTED" in read(rel) or re.search(r"\b501\b", read(rel))]
    assert hits == ["ai-service/app/api/features.py"], "the 501 producers moved: %s" % hits
    producer = read("ai-service/app/api/features.py")
    assert producer.count("HTTPException(501") == 1, "the producer answers 501 from more than one place"
    window = " ".join(producer[max(0, producer.index("HTTPException(501") - 600): producer.index("HTTPException(501")].split())
    assert "PDF converter is optional" in window, (
        "the 501 no longer says what it is about: %s" % window[-200:])
    client = read("backend/src/main/java/com/careeros/ai/HttpAiServiceClient.java")
    assert "NOT_IMPLEMENTED" not in client, "the backend now forwards a 501, so the browser can see one"
    # The upstream's two answers -- it did not answer, and it answered with
    # nothing -- are two codes now, and both are the 502 the browser reads.
    assert client.count('new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE, "AI service request failed")') == 3, (
        "the upstream's own status is no longer flattened into one 502 the browser can read")
    assert client.count('new ApiException(ApiErrorCode.AI_SERVICE_EMPTY_RESPONSE, "AI service returned empty body")') == 1, (
        "the empty body is no longer the same answer as the upstream not answering")
    assert stmt(read(CODES), "AI_SERVICE_UNAVAILABLE(HttpStatus.") == \
        "AI_SERVICE_UNAVAILABLE(HttpStatus.BAD_GATEWAY),", (
        "the code the upstream's 502 becomes is no longer a 502")


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
    assert ('title: "This run is gone"' in empty or 'title: t("activity.detail.runGone")' in empty) \
        and ('t("activity.detail.backToActivity")' in empty or "Back to activity" in empty), (
        "the screen's own record-gone copy moved: %s" % " ".join(empty.split())[:200])
    # The key it reads has to carry the sentence the reader needs, in the reader's language.
    locale = read("frontend/src/lib/i18n/translations.ts")
    assert 'runGone: "This run is gone"' in locale, (
        "the screen's record-gone copy lost its sentence in the locale table")
    assert 'runGone: "\u8fd9\u6b21\u8fd0\u884c\u5df2\u7ecf\u4e0d\u5728\u4e86"' in locale, (
        "the record-gone copy has no Chinese sentence, so a Chinese reader is told nothing")
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


def test_the_second_shell_reads_the_code_and_reports_a_gone_record_as_gone():
    """The fold is closed on this side too.

    The second shell used to read the status, so a 404 -- a route that is
    not served *or* a record that is gone -- landed on the screen's own
    "nothing here yet" hint. The code tells the two apart, and the shell
    reads it now: a route that is not served gets the not-live state, and
    a record that is gone gets the error surface, which shows the code's
    own sentence.
    """
    mv = read(MODULE_VIEW)
    assert stmt(mv, "404 not-live-state") == \
        "* Enforces: skeleton \u2192 content | 404 not-live-state | error+retry. No fake data.", (
        "the second shell's own statement of what it does with a 404 moved")
    assert stmt(mv, "const routeMissing =") == \
        'const routeMissing = query.error instanceof ApiError && query.error.code === "NOT_FOUND";', (
        "ModuleView's 404 rule changed shape; re-read which fields it consults")
    assert "isNotFound" not in mv, (
        "the second shell reads the status alone again, so a record that is gone is reported as "
        "an empty list")
    assert mv.index("query.isError ? (") < mv.index("routeMissing ? ("), (
        "the 404 test no longer sits inside the error branch, so it is not a verdict on failures")
    branch = mv[mv.index("routeMissing ? ("): mv.index("<ErrorState")]
    assert "missingEndpointMessage()" in branch and "common.notLiveTitle" in branch, (
        "a route that is not served no longer renders the not-live state: %s" % " ".join(branch.split())[:200])
    assert "emptyHint.title" not in branch, (
        "the not-live state shows the screen's own empty title again, so the reader is told the "
        "list is empty when the route is not served")
    assert mv[: mv.index("<ErrorState")].rstrip().endswith(") : ("), (
        "ErrorState is no longer the else arm of the same 404 test, so the claim above is a different one")
    assert "isEmptyPage" not in mv, "the two shells now share one empty test; re-read the claim below"
    assert "!query.data?.items.length" in mv, (
        "ModuleView's second implementation of 'has no rows' moved")


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
    assert len(not_found_codes()) == 26 and len(boundary_users()) == 5
    assert len(module_view_users()) == 5 and len(OWN_FLAG_SCREENS) == 14
