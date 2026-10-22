"""The per-field validation list the backend writes is read by nobody in the browser.

A failed request reaches the screen as one sentence. Which sentence, and who
writes it, is measured here from the shipped text of both planes:

* the backend authors ``{code, message, details[]}`` — and for a bean-validation
  failure the ``message`` is one fixed string, ``"Request validation failed"``,
  while the field name, the reason and the rejected value go into ``details[]``
  (``GlobalExceptionHandler.fieldDetail``);
* ``client.ts`` copies ``error.details`` onto the ``ApiError`` it throws, at every
  request site it has — and then nothing in ``frontend/src`` reads it. The list is
  built, serialized, parsed and dropped;
* every copy the user can see is read from the **code's own sentence** — the
  locale table's, keyed by the code the server sent — and falls back to the
  server's wording only for a code this build does not know (``describe`` in
  ``lib/hooks/failure.ts``). The per-field list is read by nobody;
* every ``err.code`` the browser compares is a code the server declares. The
  three it compares now are ``NOT_FOUND`` (the route that is not served),
  ``INVALID_CREDENTIALS`` (the answer the credentials form reads) and
  ``RESET_TOKEN_INVALID`` (the reset link);
* ``auth-recovery.test.ts`` shows a field name inside ``message``, a shape no Java
  site composes: the shipped ``VALIDATION_FAILED`` answer never carries one.

Nothing here is repaired: the fix is in ``client.ts``, ``error-state.tsx`` and the
forms, which other sessions hold. This gate binds the claim so the fold cannot be
reintroduced by editing one plane and calling it done.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

HANDLER = "backend/src/main/java/com/careeros/common/GlobalExceptionHandler.java"
API_ERROR = "backend/src/main/java/com/careeros/common/ApiError.java"
API_RESPONSE = "backend/src/main/java/com/careeros/common/ApiResponse.java"
CODES = "backend/src/main/java/com/careeros/common/ApiErrorCode.java"
CLIENT = "frontend/src/lib/api/client.ts"
ERROR_STATE = "frontend/src/components/common/error-state.tsx"
FAILURE = "frontend/src/lib/hooks/failure.ts"
CRED_FORM = "frontend/src/components/auth/credentials-form.tsx"
RECOVERY = "frontend/src/lib/auth-recovery.ts"
RECOVERY_TEST = "frontend/src/lib/auth-recovery.test.ts"

GENERIC_MESSAGE = '"Request validation failed"'


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def stmt(text: str, needle: str) -> str:
    """The one stripped line that equals `needle`; uniqueness is the point."""
    hits = [line.strip() for line in text.split("\n") if line.strip() == needle.strip()]
    assert len(hits) == 1, "expected exactly one %r, found %d" % (needle.strip(), len(hits))
    return hits[0]


def count(text: str, needle: str) -> int:
    return text.count(needle)


def ts_files() -> list[Path]:
    files = sorted((ROOT / "frontend" / "src").rglob("*.ts*"))
    assert len(files) >= 100, "the frontend walk found %d files" % len(files)
    return files


def java_files() -> list[Path]:
    files = [p for p in (ROOT / "backend" / "src" / "main" / "java").rglob("*.java")]
    assert len(files) >= 100, "the backend walk found %d files" % len(files)
    return files


def code_comparisons() -> list[tuple[str, str]]:
    """Every (file, code-name) the browser compares against `ApiError.code` outside tests."""
    out: list[tuple[str, str]] = []
    for path in ts_files():
        if path.name.endswith(".test.ts") or path.name.endswith(".test.tsx"):
            continue
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        for line in text.split("\n"):
            for match in re.finditer(r"\.code\s*[=!]==?\s*\"([A-Z_]+)\"", line):
                out.append((str(path.relative_to(ROOT)).replace("\\", "/"), match.group(1)))
    return out


def enum_names() -> list[str]:
    return re.findall(r"^\s{4}([A-Z][A-Z0-9_]*)\(", read(CODES), re.M)


def details_readers() -> list[str]:
    """Files outside client.ts that mention a `details` member at all."""
    hits: list[str] = []
    for path in ts_files():
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if rel == CLIENT:
            continue
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        for spelling in (".details", "details?.", "['details']", '["details"]'):
            if spelling in text:
                hits.append("%s %s" % (rel, spelling))
    return hits


def test_the_validation_failure_answer_is_one_fixed_sentence_plus_a_list():
    handler = read(HANDLER)
    assert count(handler, "return badRequest(ApiErrorCode.VALIDATION_FAILED, " + GENERIC_MESSAGE) == 3, (
        "the three validation channels no longer share one message, so the generic-half claim needs re-measuring")
    detail = handler[handler.index("private static Map<String, Object> fieldDetail"):]
    keys = re.findall(r'detail\.put\("([a-zA-Z]+)"', detail)
    assert keys == ["field", "message", "rejectedValue"], "fieldDetail now writes %s" % keys
    assert stmt(read(API_ERROR), '/** Structured error payload: {code, message, details[]}. */') == \
        "/** Structured error payload: {code, message, details[]}. */", "the payload's own statement of its names moved"
    assert stmt(read(API_ERROR),
                "public static ApiError of(ApiErrorCode code, String message, List<Map<String, Object>> details) {") == \
        "public static ApiError of(ApiErrorCode code, String message, List<Map<String, Object>> details) {"
    assert "details == null ? List.of() : List.copyOf(details)" in read(API_ERROR), (
        "details is no longer copied verbatim, so the list may not reach the wire")
    assert stmt(read(API_RESPONSE),
                '* {"success":false,"data":null,"error":{code,message,details[]}}.') == \
        '* {"success":false,"data":null,"error":{code,message,details[]}}.', "the envelope doc no longer promises details[]"


def test_the_three_validation_channels_author_two_different_detail_shapes():
    handler = read(HANDLER)
    field_shape = count(handler, '"field", ')
    assert field_shape == 1 or field_shape == 2, "the field-name key is authored %d times" % field_shape
    assert 'Map.<String, Object>of("message",' in handler, (
        "the parameter channel no longer authors a message-only detail")
    assert count(handler, ".toList();") >= 3, "a details stream no longer reaches badRequest"
    assert "error.getRejectedValue()" in handler, "the rejected value is no longer authored, so case 1's key list is stale"


def envelope_throws() -> list[str]:
    """Each `new ApiError(...)` in client.ts that reads the envelope's own code.

    The construction moved into `envelopeError` when the envelope's error half was
    centralized: one site that forwards `err?.details` rather than four call sites that
    could each forget to. The finder reads `new ApiError(` rather than `throw new
    ApiError(` for the same reason -- the helper returns the error and the transports
    throw or reject it a line later.
    """
    client = read(CLIENT)
    sites: list[str] = []
    for block in client.split("new ApiError(")[1:]:
        call = block.split(");")[0]
        if "err?.code" in call:
            sites.append(call)
    return sites


def test_the_browser_carries_details_in_and_never_opens_it():
    client = read(CLIENT)
    sites = envelope_throws()
    # One rather than two: the construction is centralized in `envelopeError`, and the
    # assertion below -- that the one site forwards `err?.details` -- is what keeps the
    # details list traveling. A second site would be a copy the next refactor forgets.
    assert len(sites) == 1, "the client no longer builds an ApiError from an envelope (%d sites)" % len(sites)
    dropped = [s.strip()[:60] for s in sites if "err?.details" not in s]
    assert dropped == [], "an envelope throw stopped forwarding details: %s" % dropped
    assert stmt(client, "this.details = details;") == "this.details = details;"
    readers = details_readers()
    assert readers == [], (
        "the enumerated spellings (.details, details?., ['details'], [\"details\"]) over every "
        ".ts/.tsx under frontend/src except client.ts found a reader, so the dropped-list finding "
        "must be re-measured: %s" % readers)


def test_every_visible_copy_is_read_from_the_code_and_never_from_the_details_list():
    """The reader sees the code's own sentence; the per-field list reaches nobody.

    The sentence a reader gets comes from the *code* — the locale table has one
    for that code, in the reader's language — and the server's own wording is
    the fallback for a code this build does not know. What the reader must
    never get is the per-field list: a field name inside the message tells the
    reader about the server's own bookkeeping, not about what to do.
    """
    failure = read(FAILURE)
    block = failure[failure.index("export function describe"): failure.index("export function fail")]
    assert "translate(`errorCodes.${err.code}`)" in block, (
        "the describer no longer reads the code's own sentence: %s" % " ".join(block.split()))
    assert "err.message || fallback" in block, (
        "the describer no longer falls back to the server's own wording")
    assert ".details" not in block, "the describer opens the per-field list now"

    state = read(ERROR_STATE)
    sblock = state[state.index("const detail ="): state.index("return (")]
    assert "describe(error, \"\")" in sblock, (
        "ErrorState no longer shows the describer's sentence: %s" % " ".join(sblock.split()))
    assert "details" not in state and "status" not in state, (
        "ErrorState consults the status or the list now, so the generic-sentence claim is closing")
    assert "role=\"alert\"" in state, "the failure surface is no longer announced as an alert"

    recovery = read(RECOVERY)
    assert "return err.message;" in recovery, "the recovery describer no longer falls back to the message"
    assert ".details" not in recovery, "the recovery describer opens the per-field list now"

    # The credentials form's sentence is spelled once, in the module every
    # describer shares, so a second copy cannot drift away from the first.
    spellings = [rel.relative_to(ROOT).as_posix() for rel in ts_files()
                  if not rel.name.endswith(".test.ts") and "Incorrect email or password." in read(rel)]
    assert spellings == [RECOVERY], (
        "the credentials sentence is spelled in %s -- one home, one spelling" % spellings)
    assert "authFormErrorMessage" in read(CRED_FORM), (
        "the credentials form no longer spends the shared describer, so it re-spells the sentence")


def test_the_browser_only_compares_codes_the_server_declares():
    """A branch the browser takes on a code has to be a code the server can send."""
    pairs = code_comparisons()
    names = sorted({name for _, name in pairs})
    declared = set(enum_names())
    assert len(names) >= 3, "the browser now compares %s against the code" % names
    assert "AUTH_INVALID_CREDENTIALS" not in names, (
        "the browser compares a code the enum does not declare, so that branch can never be taken "
        "by the server's answer")
    for path, name in pairs:
        assert name in declared, "%s compares %s, which the enum does not declare" % (path, name)
    assert "NOT_FOUND" in names, "the browser no longer compares the route's own code"
    assert "RESET_TOKEN_INVALID" in names, "the reset-link branch no longer compares the code"
    assert "INVALID_CREDENTIALS" in names, "the credentials branch no longer compares the code"
    assert stmt(read(CRED_FORM), "onError: (err: unknown) => toast.error(authFormErrorMessage(err)),") == \
        "onError: (err: unknown) => toast.error(authFormErrorMessage(err)),", (
        "the credentials branch changed shape; re-read which half decides it")


def test_the_live_code_branch_answers_a_message_the_backend_actually_writes():
    recovery = read(RECOVERY)
    assert stmt(recovery, 'if (err.code === "RESET_TOKEN_INVALID") {') == 'if (err.code === "RESET_TOKEN_INVALID") {'
    assert "Invalid reset token" in recovery, "the doc no longer quotes the API's own sentence"
    auth = read("backend/src/main/java/com/careeros/auth/service/AuthService.java")
    assert count(auth, '"Invalid reset token"') == 2, "the sentence the doc quotes is no longer authored twice"
    assert 'ApiErrorCode.RESET_TOKEN_INVALID, "Reset token used or expired"' in auth, (
        "the third authored message moved, so the docstring's unknown/spent/expired claim is stale")


def test_the_field_name_in_the_message_is_a_fixture_shape_no_validation_author_writes():
    test = read(RECOVERY_TEST)
    assert stmt(test, 'const err = new ApiError("VALIDATION_FAILED", "newPassword: size must be between 8 and 72", 400);') == \
        'const err = new ApiError("VALIDATION_FAILED", "newPassword: size must be between 8 and 72", 400);', (
        "the fixture that shows a field name inside message moved")
    composed = []
    for path in java_files():
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        for line in text.split("\n"):
            if "ApiErrorCode.VALIDATION_FAILED" in line and "+" in line:
                composed.append("%s:%s" % (path.name, line.strip()))
    assert composed == [], (
        "VALIDATION_FAILED's message gained a composing author; re-read which shapes exist: %s" % composed)
    # The one site that still composes a validation sentence has a code of its
    # own, so that code means one thing and the reader gets a sentence for it.
    knowledge = read("backend/src/main/java/com/careeros/knowledge/service/KnowledgeService.java")
    assert stmt(knowledge, 'throw new ApiException(ApiErrorCode.VALIDATION_KIND_UNKNOWN, "Unknown knowledge kind: " + kind);') == \
        'throw new ApiException(ApiErrorCode.VALIDATION_KIND_UNKNOWN, "Unknown knowledge kind: " + kind);', (
        "the composing site moved, so the claim about which code carries it is stale")
    handler = read(HANDLER)
    assert handler.count(GENERIC_MESSAGE) == 3, (
        "the handler composes the validation message %d times, so the generic-half claim needs re-measuring"
        % handler.count(GENERIC_MESSAGE))
    assert "newPassword: size must be between 8 and 72" not in handler and "newPassword" not in handler, (
        "the handler names a field inside its message now, so the fixture shape may be production after all")
    assert handler.count("getField()") == 1, "the field name is read %s times in the handler" % handler.count("getField()")


def test_this_gate_reads_the_files_and_populations_it_claims():
    for rel in (HANDLER, API_ERROR, API_RESPONSE, CODES, CLIENT, ERROR_STATE, FAILURE, CRED_FORM, RECOVERY, RECOVERY_TEST):
        assert (ROOT / rel).exists(), "%s is not where this file reads it" % rel
    assert len(enum_names()) >= 30, "the enum walk found only %d names" % len(enum_names())
    assert len(code_comparisons()) >= 3, "the browser compares the code %d times" % len(code_comparisons())
    assert details_readers() == [], "the details census is no longer empty: %s" % details_readers()
    assert len(ts_files()) >= 100 and len(java_files()) >= 100
    assert (ROOT / "backend/src/main/java/com/careeros/auth/service/AuthService.java").exists()
    handler = read(HANDLER)
    assert handler.count("@ExceptionHandler") >= 8, "the handler's channel count fell below what case 1 walks"
