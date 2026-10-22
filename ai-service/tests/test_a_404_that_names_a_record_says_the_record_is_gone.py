"""A 404 that names a record says the record is gone.

The backend answers a 404 in two different ways: the route is not mapped at
all, or the route is served and the record it reads is gone. Both arrive
as a 404 -- the status cannot tell them apart -- but the answers are not
the same, and one of them is a claim about the *product*:

* "this frontend and the backend are different versions" is true for a
  route that is not served, and false for a record that is gone. A reader
  who deleted a job and reopened it was told their build was wrong, and
  was offered a "Check again" button that cannot help.
* the record's own code names what happened, and the browser's table has
  a sentence for it in the reader's language.

So the *code* decides which 404 it is -- the code is the contract, and it
is the one part of an error that says what happened -- and this gate holds
that rule where it can be read:

* the boundary's "is the endpoint missing" predicate reads the code, not
  the status;
* the failure describer shows the table's sentence before it falls back to
  the version sentence, so a record that is gone never reads as a version
  mismatch;
* the backend has a code that means the route itself -- one code for the
  route that is not served, and a different one for every record -- so
  the browser's rule has something to name.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOUNDARY = ROOT / "frontend" / "src" / "components" / "common" / "query-boundary.tsx"
MODULE_VIEW = ROOT / "frontend" / "src" / "components" / "common" / "module-view.tsx"
FAILURE = ROOT / "frontend" / "src" / "lib" / "hooks" / "failure.ts"
CLIENT = ROOT / "frontend" / "src" / "lib" / "api" / "client.ts"
CODES = ROOT / "backend" / "src" /"main" / "java" / "com" / "careeros" / "common" / "ApiErrorCode.java"
HANDLER = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "common" / "GlobalExceptionHandler.java"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def body_of(text: str, start: str) -> str:
    """The function body that starts at `start`."""
    begin = text.index(start)
    end = text.index("\n}", begin)
    return text[begin:end]


def test_the_boundarys_missing_endpoint_rule_reads_the_code_and_not_the_status() -> None:
    """A 404 that names a record is not a route that is missing.

    The status cannot tell the two apart -- the backend sends 404 for both
    -- so a rule that reads the status alone sends a deleted record to the
    "your versions differ" screen, which is a false claim about the
    product and offers a retry that cannot work.
    """
    body = body_of(read(BOUNDARY), "export function isEndpointMissing")
    assert "error.isNotFound" not in body, (
        "the boundary decides 'the endpoint is missing' from the status alone, so a record "
        "that is gone is reported as a version mismatch: %s" % " ".join(body.split())
    )
    assert "error.code" in body, (
        "the boundary no longer reads the code, so it cannot tell a route that is not served "
        "from a record that is gone: %s" % " ".join(body.split())
    )
    assert "501" in body, (
        "a 501 still means the service does not implement the route, and the rule dropped it"
    )


def test_the_second_shell_reads_the_code_and_not_the_status() -> None:
    """A list shell that reports a gone record as an empty list is lying.

    The boundary and the list shell are the two places a 404 is decided,
    and they have to decide it the same way: a route that is not served is
    a version skew, and a record that is gone is a record that is gone --
    the reader can do something about the second one.
    """
    text = read(MODULE_VIEW)
    assert "isNotFound" not in text, (
        "the second shell decides 'the endpoint is missing' from the status alone, so a record "
        "that is gone is reported as an empty list")
    assert 'query.error.code === "NOT_FOUND"' in text, (
        "the second shell no longer reads the code, so it cannot tell a route that is not served "
        "from a record that is gone")
    assert "missingEndpointMessage()" in text, (
        "a route that is not served no longer says so: the reader is told the list is empty")


def test_the_failure_describer_shows_the_tables_sentence_before_the_version_sentence() -> None:
    """The code's sentence first; the version sentence only for a 404 we cannot name.

    The *runtime* order is the claim, not the order of the words in the file:
    a describer that reads the table's sentence and then returns the version
    sentence is wrong, and "the table's sentence appears earlier in the
    source" does not say which one the reader gets.
    """
    text = read(FAILURE)
    body = body_of(text, "export function describe")
    assert "errorCodes." in body, (
        "the describer no longer reads the code's own sentence: %s" % " ".join(body.split()))
    returns = [(i, line.strip()) for i, line in enumerate(body.split("\n")) if "return " in line]
    version = [i for i, line in returns if "missingEndpointMessage()" in line]
    table = [i for i, line in returns if "sentence" in line and "missingEndpointMessage" not in line]
    assert table, (
        "the describer no longer returns the code's own sentence: %s" % [line for _, line in returns])
    assert version, (
        "the describer no longer falls back to the version sentence: %s" % [line for _, line in returns])
    assert table[0] < version[0], (
        "the version sentence is returned before the table's, so a record that is gone reads as "
        "a version mismatch: %s" % [line for _, line in returns])


def test_the_backend_names_the_route_and_the_records_apart() -> None:
    """The browser's rule has something to name."""
    handler = read(HANDLER)
    start = handler.index("@ExceptionHandler(NoResourceFoundException.class)")
    window = handler[start: start + 400]
    assert "ApiErrorCode.NOT_FOUND" in window, (
        "the unmapped-route handler no longer answers the bare NOT_FOUND code, so the browser "
        "cannot tell a missing route from a missing record: %s" % " ".join(window.split())
    )
    codes = read(CODES)
    route = re.findall(r"^\s*([A-Z_]+)\(HttpStatus\.NOT_FOUND\)", codes, re.M)
    assert "NOT_FOUND" in route, "the enum has no code for the route that is not served"
    records = [c for c in route if c != "NOT_FOUND"]
    assert len(records) >= 10, (
        "only %d codes name a record that is gone -- the browser's rule needs the rest of them "
        "to be told apart from the route" % len(records)
    )


def test_the_browsers_own_bare_404_keeps_the_routes_own_name() -> None:
    """A 404 with no envelope is a route that did not answer -- and says so in the same name."""
    client = read(CLIENT)
    assert 'status === 404 ? "NOT_FOUND"' in client, (
        "the client no longer names a bare 404 with the route's own code, so the browser's "
        "rule cannot recognise one"
    )
