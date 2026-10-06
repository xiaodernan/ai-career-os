"""Two envelope members have a declaration and a writer, but no author on the service side.

Measured from the shipped text of both planes:

* ``ApiException`` declares a constructor that takes ``List<Map<String,Object>> details``,
  and **every one of its 69 call sites in the backend passes two arguments** — so the
  per-field list a caller could fill is never filled by a service. The only callers of
  the three-argument ``ApiError.of`` are the two envelope paths inside
  ``GlobalExceptionHandler``, which forward what the framework's validation channels
  built (see #201: nothing in the browser reads that list either).
* ``ApiResponse`` is annotated ``@JsonInclude(ALWAYS)`` and its own doc states the
  ``success`` bit, while ``client.ts`` declares ``success: boolean`` as a required
  member — yet exactly two of the client's request paths consult it. The stream path
  decides whether it got an answer from the media type instead.

The argument splitter here is string-aware, and that is not decoration:
``RateLimitFilter`` passes ``"Too many requests, slow down"`` — a comma inside a
literal. A splitter that ignores quotes reads that call as three arguments and the
"no service fills the details slot" claim becomes a measurement of the scanner. The
self-check case pins both answers as a control pair.

Nothing is repaired: the declarations are the API's own, and deleting them is a
server-side decision, not a test's.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXCEPTION = "backend/src/main/java/com/careeros/common/ApiException.java"
API_ERROR = "backend/src/main/java/com/careeros/common/ApiError.java"
API_RESPONSE = "backend/src/main/java/com/careeros/common/ApiResponse.java"
HANDLER = "backend/src/main/java/com/careeros/common/GlobalExceptionHandler.java"
LIMITER = "backend/src/main/java/com/careeros/ratelimit/RateLimitFilter.java"
CLIENT = "frontend/src/lib/api/client.ts"

RATE_LIMITED_CALL = 'ApiError.of(ApiErrorCode.RATE_LIMITED, "Too many requests, slow down")'
FORWARD_CALL = "ApiError.of(ex.code(), ex.getMessage(), ex.details())"
BAD_REQUEST_CALL = "ApiError.of(code, message, details)"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def stmt(text: str, needle: str) -> str:
    hits = [line.strip() for line in text.split("\n") if needle.strip() in line]
    assert len(hits) == 1, "expected exactly one line containing %r, found %d" % (needle.strip(), len(hits))
    return hits[0]


def args(text: str, start: int) -> list[str]:
    """Split the argument list that opens at `start`, respecting quotes and nesting."""
    depth, out, cur, quote, i = 1, [], "", "", start
    while i < len(text) and depth:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if quote:
            cur += ch
            if ch == "\\":
                cur += nxt
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in "\"'`":
            quote = ch
            cur += ch
            i += 1
            continue
        if ch == "/" and nxt == "/":
            nl = text.find("\n", i)
            if nl < 0:
                break
            i = nl
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if not depth:
                break
        if ch == "," and depth == 1:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    if cur.strip():
        out.append(cur.strip())
    return out


def call_arity(text: str, opener: str) -> list[tuple[int, int]]:
    """Every `opener` call as (line number, argument count)."""
    return [(text[: m.start()].count("\n") + 1, len(args(text, m.end())))
            for m in re.finditer(re.escape(opener), text)]


def java_main() -> list[Path]:
    files = sorted((ROOT / "backend" / "src" / "main" / "java").rglob("*.java"))
    assert len(files) >= 150, "the backend walk found only %d files" % len(files)
    return files


def throw_arity() -> list[int]:
    out: list[int] = []
    for path in java_main():
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        out.extend(n for _, n in call_arity(text, "new ApiException("))
    return out


def of_arity_by_file() -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for path in java_main():
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        found = call_arity(text, "ApiError.of(")
        if found:
            out[path.name] = [n for _, n in found]
    return out


def test_no_service_ever_fills_the_exception_s_details_slot():
    exception = read(EXCEPTION)
    assert stmt(exception, "public ApiException(ApiErrorCode code, String message) {") == \
        "public ApiException(ApiErrorCode code, String message) {"
    assert stmt(exception, "public ApiException(ApiErrorCode code, String message, List<Map<String, Object>> details) {") == \
        "public ApiException(ApiErrorCode code, String message, List<Map<String, Object>> details) {", (
        "the three-argument constructor moved; re-read which callers it has")
    arities = throw_arity()
    assert len(arities) >= 60, "the throw walk found only %d sites" % len(arities)
    assert set(arities) == {2}, "a service now raises ApiException with %s argument counts" % sorted(set(arities))


def test_the_only_three_argument_envelope_author_is_the_framework_handler():
    by_file = of_arity_by_file()
    three = sorted(name for name, counts in by_file.items() if 3 in counts)
    assert three == ["GlobalExceptionHandler.java"], "%s author a details list" % three
    assert by_file["GlobalExceptionHandler.java"].count(3) == 2, (
        "the handler's three-argument calls are %s" % by_file["GlobalExceptionHandler.java"])
    assert {n for counts in by_file.values() for n in counts} == {2, 3}, (
        "ApiError.of is now called with other argument counts: %s" % by_file)


def test_the_handler_s_two_forwarding_paths_are_named_in_the_handler():
    handler = read(HANDLER)
    assert stmt(handler, FORWARD_CALL) == ".body(ApiResponse.error(%s));" % FORWARD_CALL, (
        "the ApiException path no longer forwards the exception's own details")
    assert stmt(handler, BAD_REQUEST_CALL) == ".body(ApiResponse.error(%s));" % BAD_REQUEST_CALL, (
        "badRequest no longer forwards a details list")
    assert "ex.details()" in handler, "the ApiException accessor is no longer read, so case 1's slot claim is stale"


def test_the_rate_limit_answer_is_two_arguments_even_though_its_message_holds_a_comma():
    limiter = read(LIMITER)
    assert stmt(limiter, RATE_LIMITED_CALL) == RATE_LIMITED_CALL + ");", (
        "the 429 answer moved; it is this gate's control that the argument split respects quotes")
    found = call_arity(limiter, "ApiError.of(")
    assert [n for _, n in found] == [2], "the splitter read the rate-limit call as %s" % found
    assert '"Too many requests, slow down"' in RATE_LIMITED_CALL, "the control message no longer contains a comma"
    assert 'setStatus(429)' in limiter and 'setHeader("Retry-After", "60")' in limiter, (
        "the 429 answer changed shape, so its argument count is a different fact")


def test_the_success_bit_is_written_always_and_consulted_in_two_paths():
    response = read(API_RESPONSE)
    assert stmt(response, "@JsonInclude(JsonInclude.Include.ALWAYS)") == "@JsonInclude(JsonInclude.Include.ALWAYS)"
    doc = [line.strip() for line in response.split("\n") if '{"success"' in line]
    assert len(doc) == 2 and doc[0].startswith('* Unified response envelope: {"success":true,"data":') and \
        doc[1].startswith('* {"success":false,"data":null,"error":{code,message,details[]}}'), (
        "the envelope's own doc no longer states the success bit and the details list together: %s" % doc)
    client = read(CLIENT)
    assert client.count("json.success") == 2, "the client consults the success bit %d times" % client.count("json.success")
    assert stmt(client, "if (!res.ok || !json.success || !json.data) return null;") == \
        "if (!res.ok || !json.success || !json.data) return null;", "the refresh path stopped asking the bit"
    assert stmt(client, "if (!res.ok || (json && json.success === false)) {") == \
        "if (!res.ok || (json && json.success === false)) {", "the request path stopped asking the bit"
    assert stmt(client, "if (!res.ok || !stream) {") == "if (!res.ok || !stream) {", (
        "the stream path's answer test moved; this gate claims it reads the media type, not the bit")
    assert stmt(client, "success: boolean;") == "success: boolean;", (
        "the client no longer declares the bit as required, so a missing member would not be a lie")


def test_this_gate_reads_the_files_and_its_scanner_reads_both_ways():
    for rel in (EXCEPTION, API_ERROR, API_RESPONSE, HANDLER, LIMITER, CLIENT):
        assert (ROOT / rel).exists(), "%s is not where this file reads it" % rel
    forward = read(HANDLER)
    line = forward.index(FORWARD_CALL)
    assert len(args(forward, forward.index("(", line) + 1)) == 3, (
        "the splitter no longer reads the handler's forwarding call as three arguments")
    limiter = read(LIMITER)
    assert len(args(limiter, limiter.index("(", limiter.index(RATE_LIMITED_CALL)) + 1)) == 2, (
        "the splitter no longer reads the rate-limit call as two arguments")
    assert len(throw_arity()) >= 60 and len(java_main()) >= 150
    assert "List<Map<String, Object>> details" in read(API_ERROR), "ApiError's list type moved, so case 2's shape is stale"
