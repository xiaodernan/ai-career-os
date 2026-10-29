"""The origin a browser is sent to is the origin CORS allows, and no file says so once.

A page served from `http://localhost:3000` that calls `http://localhost:8080` makes a cross-origin
request, so the backend's allow-list has to name exactly that origin. Nothing about the pair is
written down in one place: `application.yml` interpolates `${APP_CORS_ORIGINS:http://localhost:3000}`,
`AppProperties.java` initialises the same literal as a Java default, `AuthService.java` carries a
third copy in the `@Value` for the password-reset base URL, `docker-compose.yml` interpolates it
again, `.env.example` states it twice, and the README, DEPLOYMENT, SECURITY, the Playwright config,
the preflight script and the prod example each send a reader's browser -- or a reader's reset link --
to it. Measured here they all agree, which is precisely why none of them had ever been checked: the
pairing has no reader.

The failure it prevents is not subtle. Two variables must name ONE origin -- the allow-list and the
base URL the reset mail links back to, which `AuthService`'s own comment says "defaults to the same
origin CORS already trusts" -- and a deployment that sets only the first gets a link the user can
open but cannot use: the page it loads is not an allowed origin, so every call it makes comes back
`Invalid CORS request` and the password reset fails silently.

So the value is derived, never typed. The authority is the default `application.yml` interpolates,
because that file always defines `app.cors.allowed-origins` and therefore decides what Spring binds --
the initialiser in `AppProperties.java` is a shadow whose edits change nothing, and it is still
reconciled here because a reader takes it for the default. Each carrier is parsed by an extractor for
the shape it is written in, and the scan behind them judges every URL-shaped claim in the shipped
text rather than only the ones this file was told about: any loopback URL naming the frontend's port
must be an allowed origin, since a browser treats `127.0.0.1` and `localhost` as different origins --
which is why `e2e/README.md`'s first trap warns a reader off it.

Two more populations have to fit inside the same bean. `docs/SECURITY.md` states the allow-list's
default origin inside its transport bullet, which makes the document a carrier like any `${...:}` --
and the one a developer reads before setting the variable -- and it lists the CORS methods and headers
as a security property, `SecurityConfig.java` decides them, and the browser is the thing that
must live inside them -- so what a browser sends is censused from the browser-side modules
under `frontend/src` and checked in both directions: allowed, or one of the four headers the Fetch
standard carries without a preflight; and
anything the allow-list admits either sent by that browser or ledgered against the server-side sender
that proves the entry is deliberate. `X-Internal-Token` is allowed although no browser sends it, and
the ledger says so, because a reader auditing what a cross-origin request may carry needs that answer
and the list alone does not give it.

The Next middleware module is the one file the header census refuses by name. It runs on the
server: the nonce and policy it writes decorate the request the Next server hands its own
renderer, and the policy the browser enforces leaves on the response. Neither is a header a
browser sends, so neither crosses a preflight. The refusal is proved rather than assumed by a
case that reads the module and checks it is still that shape, and the browser census asserts
the pair is gone from its own answer.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
BACKEND_MAIN = ROOT / "backend" / "src" / "main"
YML = BACKEND_MAIN / "resources" / "application.yml"
APP_PROPERTIES = BACKEND_MAIN / "java" / "com" / "careeros" / "config" / "AppProperties.java"
SECURITY_CONFIG = BACKEND_MAIN / "java" / "com" / "careeros" / "config" / "SecurityConfig.java"
AUTH_SERVICE = BACKEND_MAIN / "java" / "com" / "careeros" / "auth" / "service" / "AuthService.java"
FRONTEND_SRC = ROOT / "frontend" / "src"
AI_SERVICE_APP = ROOT / "ai-service" / "app"
SECURITY_DOC = ROOT / "docs" / "SECURITY.md"
ENV_DEV = ROOT / ".env.example"
ENV_PROD = ROOT / ".env.prod.example"
COMPOSE = ROOT / "docker-compose.yml"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
PLAYWRIGHT_CONFIG = ROOT / "e2e" / "playwright.config.ts"
PREFLIGHT = ROOT / "e2e" / "preflight.ps1"

# the shipped text an operator or a reader uses to aim a browser, a script or a container
TEXT_POPULATION = (ROOT / "README.md", ROOT / "docs", ROOT / "e2e", ROOT / "scripts",
                   ENV_DEV, ENV_PROD, COMPOSE, COMPOSE_PROD, BACKEND_MAIN)
SKIP_DIRS = {"node_modules", ".next", "target", "dist", "__pycache__", ".venv",
             "playwright-report", "test-results", "evals"}
# `.example` is a suffix, not a name: `Path(".env.example").suffix` is `.example`, so an entry that
# left it out dropped both env files from the open-ended scan while still naming them in the
# population -- which is how an origin written down by an operator escaped the census.
TEXT_SUFFIXES = {".md", ".yml", ".yaml", ".ts", ".tsx", ".ps1", ".sh", ".py", ".java", ".example"}

# Fetch lets a cross-origin request carry these four without a preflight, so the allow-list does
# not have to name them: https://fetch.spec.whatwg.org/#cors-safelisted-request-header
SAFELISTED_HEADERS = {"accept", "accept-language", "content-language", "content-type"}
PREFLIGHT_METHOD = "OPTIONS"

# admitted by CORS although no browser sends it: each row is reconciled with a server-side sender
SERVER_ONLY_HEADERS = {
    "x-internal-token": "shared secret the backend and ai-service present to each other",
}

# Next middleware runs on the server: the nonce and policy it writes decorate the request the Next
# server hands its own renderer, and the policy the browser enforces leaves on the response. Neither
# is a header a browser sends, so the browser census refuses this module by name --
# `test_the_middleware_headers_are_server_side_and_not_browser_traffic` proves the refusal is about
# that shape rather than a place a browser call moved into.
SERVER_MODULES = {FRONTEND_SRC / "middleware.ts"}

MIN_CARRIERS = 9
MIN_LOOPBACK_URLS = 10
MIN_HEADER_SITES = 6
MIN_METHOD_SITES = 6

INTERP = re.compile(
    r"\$\{(?P<var>[A-Z][A-Z0-9_]*)(?::(?:(?P<required>\?)|(?P<dash>-))?(?P<default>[^}]*))?\}"
)
# scheme plus loopback host plus optional port: exactly the origin, so no trailing punctuation,
# path or quote can be mistaken for part of it
LOOPBACK_ORIGIN = re.compile(r"https?://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?")
LIST_OF = re.compile(r"List\.of\((?P<args>[^)]*)\)")
QUOTED = re.compile(r"\"([^\"]*)\"")
SPRING_REF = re.compile(r"app\.web\.base-url:(?P<default>[^}\s]+)")
METHOD_LITERAL = re.compile(r"\bmethod\s*:\s*[\"'`](?P<method>[A-Za-z]+)[\"'`]")
XHR_OPEN = re.compile(r"\.open\(\s*[\"'`](?P<method>[A-Za-z]+)[\"'`]")
HEADER_SETTER = re.compile(
    r"\b\w*[Hh]eaders\s*\.\s*(?:set|append)\(\s*[\"'`](?P<name>[^\"'`]+)[\"'`]"
)
SET_REQUEST_HEADER = re.compile(r"setRequestHeader\(\s*[\"'`](?P<name>[^\"'`]+)[\"'`]")
HEADER_ASSIGN = re.compile(r"\bheaders\.(?P<name>[A-Za-z][\w-]*)\s*=")
HEADER_OBJECT = re.compile(r"\bheaders\s*:[^;{}]{0,60}\{")
REQUEST_CALL = re.compile(r"\brequest\s*(?:<[^()<>]*>)?\(")


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def origin_of(url: str) -> str:
    """`scheme://host:port` -- the unit a browser compares, so a path is not part of it."""
    match = re.match(r"(?P<scheme>https?)://(?P<host>[^/]+)", url.strip())
    assert match, f"{url!r} is not a URL an allow-list could hold"
    return f"{match['scheme']}://{match['host']}"


def origin_list(value: str) -> set[str]:
    """Split a comma-separated origin list the way the backend binds it."""
    return {origin_of(part) for part in value.split(",") if part.strip()}


def walk(*roots: Path, code_only: bool = False) -> list[tuple[Path, str]]:
    """Text of every shipped file under the given paths, generated trees and tests excluded."""
    out: list[tuple[Path, str]] = []
    for root in roots:
        for path in ([root] if root.is_file() else sorted(root.rglob("*"))):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if SKIP_DIRS & set(path.parts) or path.name == "package-lock.json":
                continue
            if code_only and (".test." in path.name or ".spec." in path.name):
                continue
            out.append((path, read(path)))
    return out


def interpolation_default(text: str, var: str, carrier: str) -> str | None:
    """The default `${VAR:x}` (Spring), `${VAR:-x}` (compose) or `${VAR:?m}` carries; None when it states none.

    One expression reads every spelling because the tools that expand them differ by one
    character: a parser that required the dash would call every default in `application.yml`
    "states nothing", and one that left it in the value would report `-http://localhost`.
    Compose's `:?` is a requirement, not a default -- the text after it is the message a
    missing value stops with -- so it reads as None, the same claim as a bare `${VAR}`.
    """
    for match in INTERP.finditer(text):
        if match["var"] != var:
            continue
        if match["required"] or match["default"] is None:
            return None
        assert not match["default"].startswith("-"), (
            f"{carrier}: {var} uses compose's `:-` and the dash survived into the default "
            f"{match['default']!r}; a container never sees a leading dash on that value")
        return match["default"]
    raise AssertionError(f"{carrier} no longer interpolates {var}")


def java_list_of(text: str, after: str, carrier: str) -> list[str]:
    """The strings in the first `List.of(...)` at or after `after`.

    Anchored on the call rather than scanning the whole file, because a Java class holds several
    `List.of` initialisers and taking the first would compare the allow-list against an unrelated
    field.
    """
    start = text.find(after)
    assert start >= 0, f"{carrier} no longer contains {after!r}"
    match = LIST_OF.search(text, start)
    assert match, f"{carrier}: no List.of(...) after {after!r}"
    return [item for item in QUOTED.findall(match["args"]) if item]


def config_string_list(call: str) -> list[str]:
    """The strings `SecurityConfig` passes to one `setAllowed...` call."""
    return java_list_of(read(SECURITY_CONFIG), f".{call}(List.of", f"SecurityConfig's .{call}")


def env_assignment(path: Path, var: str) -> str:
    """The value an env example writes for `var` -- commented lines are advice, not values."""
    for line in read(path).split("\n"):
        if line.startswith(f"{var}="):
            return line.split("=", 1)[1].strip()
    raise AssertionError(f"{path.name} no longer assigns {var} on an uncommented line")


def quoted_fallback(path: Path, pattern: str) -> str:
    """The quoted value a script or config falls back to when its variable is unset."""
    match = re.search(pattern, read(path))
    assert match, f"{path.name} no longer holds a quoted fallback this gate can read"
    return match.group(1)


def cors_authority() -> set[str]:
    """The origins Spring binds when `APP_CORS_ORIGINS` is unset -- the deciding carrier."""
    raw = interpolation_default(read(YML), "APP_CORS_ORIGINS", "application.yml")
    assert raw, "application.yml's APP_CORS_ORIGINS default is empty, so no origin is allowed"
    return origin_list(raw)


def setter_sites(name: str) -> list[tuple[str, int]]:
    """(file, line) for every `.name(...)` call in the backend's main sources."""
    return [(path.name, _line_of(text, hit.start()))
            for path, text in walk(BACKEND_MAIN)
            for hit in re.finditer(r"\." + name + r"\(", text)]


def browser_header_sites() -> list[tuple[str, int, str]]:
    """(file, line, header) for every header name shipped browser code puts on a request.

    Four shapes are read: `bag.set("Name", ...)`, `xhr.setRequestHeader("Name", ...)`,
    `headers.Name = ...` and a `headers` object literal. Every header the app sends reaches a
    preflight through one of them, so a name outside all four is a name no request carries.
    `SERVER_MODULES` are refused by name: a module Next runs on the server cannot send a browser
    request, and the control case below pins the file to that role.
    """
    sites: list[tuple[str, int, str]] = []
    for path, text in walk(FRONTEND_SRC, code_only=True):
        if path in SERVER_MODULES:
            continue
        for pattern in (HEADER_SETTER, SET_REQUEST_HEADER, HEADER_ASSIGN):
            for hit in pattern.finditer(text):
                sites.append((path.name, _line_of(text, hit.start()), hit["name"]))
        for hit in HEADER_OBJECT.finditer(text):
            for name in object_keys(text, hit.end() - 1):
                sites.append((path.name, _line_of(text, hit.start()), name))
    return sites


def object_keys(text: str, brace: int) -> list[str]:
    """Top-level keys of the object literal that starts at `brace`, quoted or bare."""
    depth, keys, buf = 0, [], ""
    for index in range(brace, len(text)):
        char = text[index]
        if char in "{[(":
            depth += 1
            if depth == 1:
                continue  # the opening brace is the delimiter, never part of a key
        elif char in ")]}" and depth:
            depth -= 1
            if depth == 0:
                if ":" in buf:
                    keys.append(buf.split(":")[0].strip().strip("\"'"))
                break
        if depth == 1 and char == ",":
            if ":" in buf:
                keys.append(buf.split(":")[0].strip().strip("\"'"))
            buf = ""
            continue
        if depth >= 1:
            buf += char
    return [key for key in keys if re.fullmatch(r"[\w-]+", key)]


def options_state_method(options: str) -> bool:
    """Does one `request(...)` options object name a method, or leave it to the default?"""
    return re.search(r"\bmethod\s*:", options) is not None


def browser_method_sites() -> list[tuple[str, int, str]]:
    """(file, line, method) for every HTTP method shipped frontend code asks for.

    `request`'s options argument defaults to `{}` (`client.ts:149`), so a call that leaves the
    method out of it -- `request(path)`, or `request(path, { params })` the way `api.get` and
    `api.list` forward at `client.ts:495-499` -- is a GET. Those call sites are censused for the
    same reason the explicit ones are: without them the allow-list's `GET` would look like an
    entry nothing in this repository uses, and the clause that fails a dead allowed method would
    be measuring only the methods someone spelled out.
    """
    sites: list[tuple[str, int, str]] = []
    for path, text in walk(FRONTEND_SRC, code_only=True):
        for hit in METHOD_LITERAL.finditer(text):
            sites.append((path.name, _line_of(text, hit.start()), hit["method"].upper()))
        for hit in XHR_OPEN.finditer(text):
            sites.append((path.name, _line_of(text, hit.start()), hit["method"].upper()))
        for hit in REQUEST_CALL.finditer(text):
            if text[: hit.start()].rstrip().endswith("function"):
                continue  # `request`'s own declaration, whose `options: T = {}` is not a call
            args = top_level_args(text, hit.end() - 1)
            if not any(options_state_method(arg) for arg in args[1:]):
                sites.append((path.name, _line_of(text, hit.start()), "GET"))
    return sites


def top_level_args(text: str, open_at: int) -> list[str]:
    """Arguments of the call whose `(` sits at `open_at`, nested brackets folded into one."""
    depth, args, buf = 0, [], ""
    for char in text[open_at:]:
        if char in "([{":
            depth += 1
            if depth == 1:
                continue
        elif char in ")]}" and depth:
            depth -= 1
            if depth == 0:
                return args + [buf]
        elif char == "," and depth == 1:
            args.append(buf)
            buf = ""
            continue
        if depth >= 1:
            buf += char
    return args


def server_header_senders(name: str) -> list[tuple[str, int]]:
    """Where backend or ai-service source puts `name` on a request they send."""
    return [(path.name, _line_of(text, hit.start()))
            for path, text in walk(BACKEND_MAIN, AI_SERVICE_APP)
            for hit in re.finditer(r"[\"']" + re.escape(name) + r"[\"']", text, re.I)]


def cors_bullet() -> str:
    """The SECURITY.md transport bullet that states the allow-list, continuations folded in."""
    lines = read(SECURITY_DOC).split("\n")
    for index, line in enumerate(lines):
        if line.startswith("- CORS is allow-listed from"):
            out = [line]
            for follow in lines[index + 1:]:
                if follow.startswith(("- ", "## ", "### ")):
                    break
                out.append(follow)
            return " ".join(part.strip() for part in out)
    raise AssertionError("SECURITY.md no longer has the `- CORS is allow-listed from` bullet")


def doc_stated_default() -> set[str]:
    """The origin SECURITY.md states inside its `CORS is allow-listed from` bullet.

    The document says what the default *is*, not merely that a default exists, which makes it a
    carrier like any `${APP_CORS_ORIGINS:...}` -- and the one carrier a developer reads before
    setting the variable. Read from the folded bullet, so the sentence can be re-wrapped.
    """
    match = re.search(r"\(default\s+`(?P<origin>[^`]+)`\)", cors_bullet())
    assert match, (
        "SECURITY.md's transport bullet no longer states the allow-list's default in "
        "`(default `...`)', so the document's claim about the origin cannot be checked")
    return origin_list(match["origin"])


CARRIERS: list[tuple[str, object]] = [
    ("AppProperties' `allowedOrigins` initialiser",
     lambda: {origin_of(o) for o in
              java_list_of(read(APP_PROPERTIES), "allowedOrigins = List.of", "AppProperties")}),
    ("application.yml's `app.web.base-url` default",
     lambda: {origin_of(interpolation_default(
         read(YML), "APP_WEB_BASE_URL", "application.yml"))}),
    ("AuthService's `@Value` default for the reset base URL",
     lambda: {origin_of(SPRING_REF.search(read(AUTH_SERVICE)).group("default"))}),
    (".env.example's `APP_CORS_ORIGINS`",
     lambda: origin_list(env_assignment(ENV_DEV, "APP_CORS_ORIGINS"))),
    (".env.example's `APP_WEB_BASE_URL`",
     lambda: {origin_of(env_assignment(ENV_DEV, "APP_WEB_BASE_URL"))}),
    ("docker-compose.yml's `APP_CORS_ORIGINS` default",
     lambda: {origin_of(interpolation_default(
         read(COMPOSE), "APP_CORS_ORIGINS", "docker-compose.yml"))}),
    ("SECURITY.md's stated allow-list default", doc_stated_default),
    ("the Playwright config's `E2E_BASE_URL` fallback",
     lambda: {origin_of(quoted_fallback(
         PLAYWRIGHT_CONFIG, r"E2E_BASE_URL\s*\?\?\s*[\"']([^\"']+)[\"']"))}),
    ("the preflight script's `E2E_BASE_URL` fallback",
     lambda: {origin_of(quoted_fallback(PREFLIGHT, r"else\s*\{\s*'([^']+)'"))}),
]


def test_the_origin_parsers_read_both_interpolation_spellings_and_a_colon_bearing_default():
    """Proves the primitives on shapes this repository does not currently contain.

    A default that carries `://` and a port cannot be read by splitting the interpolation on the
    first colon -- that yields `http` -- and compose's `:-` differs from Spring's `:` by one
    character. Exercised only against the shipped files, these parsers would be holding up the
    census by accident, and a reader who re-spelled one default would find the census reconciling
    an empty set.
    """
    spring = "    allowed-origins: ${APP_CORS_ORIGINS:http://box.example:3000}"
    compose = "      APP_CORS_ORIGINS: ${APP_CORS_ORIGINS:-http://box.example:3000}"
    assert interpolation_default(spring, "APP_CORS_ORIGINS", "spring fixture") == \
        "http://box.example:3000", (
        "Spring's `${VAR:default}` read came back wrong: splitting the interpolation on the first "
        "colon yields `http`, and every carrier in application.yml is then compared as a stub")
    assert interpolation_default(compose, "APP_CORS_ORIGINS", "compose fixture") == \
        "http://box.example:3000", "compose's `:-` must not survive into the value"
    assert interpolation_default("A: ${APP_CORS_ORIGINS}", "APP_CORS_ORIGINS", "bare") is None, (
        "a bare `${VAR}` states no default and must read as None; treating it as an empty string "
        "would let the production arm that forbids a default pass on a file that has one")
    assert interpolation_default("A: ${APP_CORS_ORIGINS:-}", "APP_CORS_ORIGINS", "empty") == "", (
        "`${VAR:-}` states an empty default, which is a different claim from stating none, and the "
        "two have to be told apart by the reader")
    assert interpolation_default(
        "A: ${APP_CORS_ORIGINS:?fill .env.prod and pass --env-file .env.prod}",
        "APP_CORS_ORIGINS", "required") is None, (
        "compose's `${VAR:?message}` is a requirement, not a default: reading `?message` as the "
        "value would make the production arm that forbids a default fail on the strongest "
        "spelling the compose file can use")
    assert origin_list("https://a.example, https://b.example") == \
        {"https://a.example", "https://b.example"}, (
        "a comma-separated allow-list is more than one origin, and the split has to keep both")
    assert origin_of("http://box.example:3000/reset?token=x") == "http://box.example:3000", (
        "a browser compares scheme, host and port only, so a path or query must not become part of "
        "the origin an allow-list is said to admit")
    assert origin_of("http://box.example:3000/") == "http://box.example:3000", (
        "a trailing slash is not part of an origin; keeping it would make one origin look like two")
    assert {m.group(0) for m in LOOPBACK_ORIGIN.finditer(
        'see "127.0.0.1:3000:3000" and http://localhost:3000/x and http://localhost:30000'
    )} == {"http://localhost:3000", "http://localhost:30000"}, (
        "the scan must need a scheme (a compose port mapping is not a URL) and must not read "
        "`30000` as port `3000`")


def test_the_java_list_reader_chooses_the_field_it_was_asked_for():
    """The reader that makes the shadow default comparable -- proved, not assumed."""
    two_lists = (
        'class Bag {\n'
        '  private List<String> first = List.of("http://one.example:1");\n'
        '  private List<String> second = List.of(\n'
        '      "GET", "POST",\n      "DELETE");\n')
    assert java_list_of(two_lists, "first = List.of", "fixture") == ["http://one.example:1"], (
        "the reader took a List.of from somewhere else in the file, so the allow-list it reports "
        "belongs to another field")
    assert java_list_of(two_lists, "second = List.of", "fixture") == \
        ["GET", "POST", "DELETE"], "a multi-line List.of was truncated or mis-sorted"
    assert java_list_of(two_lists, "second =", "fixture") == ["GET", "POST", "DELETE"], (
        "anchoring on `second =` instead of the call must still find the same field's list")
    try:
        java_list_of("private String lonely = \"x\";", "lonely = ", "fixture")
    except AssertionError as error:
        assert "no List.of" in str(error)
    else:
        raise AssertionError("a field with no List.of() read as an empty allow-list")


def test_the_cors_lists_the_gate_reads_are_the_ones_security_config_ships():
    """A floor under the census: the two lists have members, and each is called once."""
    methods = config_string_list("setAllowedMethods")
    headers = config_string_list("setAllowedHeaders")
    assert len(methods) >= 4 and len(headers) >= 2, (
        f"setAllowedMethods reads {methods} and setAllowedHeaders reads {headers}; the census "
        f"below compares a document against these, so a stub here empties every claim above it")
    assert PREFLIGHT_METHOD in methods, (
        f"setAllowedMethods {methods} does not admit {PREFLIGHT_METHOD}, which is the method every "
        f"preflight uses -- no cross-origin request from the app could complete")


def test_every_carrier_that_states_the_browser_origin_names_the_one_cors_allows():
    authority = cors_authority()
    assert len(CARRIERS) >= MIN_CARRIERS, (
        f"the carrier census holds {len(CARRIERS)} entries, fewer than the {MIN_CARRIERS} the "
        f"shipped files state, so this case would be reconciling a stub")
    problems = []
    for label, state in CARRIERS:
        try:
            stated = state()
        except (AssertionError, AttributeError) as error:
            problems.append(f"{label}: could not be read ({error})")
            continue
        if not stated:
            problems.append(f"{label} parses to no origin at all")
        elif stated != authority:
            problems.append(f"{label} states {sorted(stated)}, the allow-list default is "
                            f"{sorted(authority)}")
    assert problems == [], (
        "the origin a browser is sent to is decided in more than one file and they disagree --\n"
        + "\n".join(problems)
        + f"\n-- the deciding value is application.yml's APP_CORS_ORIGINS default "
          f"{sorted(authority)}; a reset link from an origin outside that list loads but "
          f"cannot call the API")


def test_nothing_in_the_shipped_text_sends_a_browser_to_another_origin_on_that_port():
    """The census of origin claims no extractor was told about, keyed on the port.

    Two clauses stand in front of the count because the count cannot see its own population: a file
    named in `TEXT_POPULATION` that `walk` refuses to read, and a file the population covers whose
    suffix no one has thought of yet, both read as an empty scan rather than as a missing carrier.
    """
    ports = {origin.rsplit(":", 1)[-1] for origin in cors_authority()}
    allowed = cors_authority()
    rows, problems, seen = [], [], set()
    for path, text in walk(*TEXT_POPULATION):
        seen.add(str(path.relative_to(ROOT)))
        for hit in LOOPBACK_ORIGIN.finditer(text):
            if hit.group(0).rsplit(":", 1)[-1] not in ports:
                continue
            origin = hit.group(0)
            rows.append((str(path.relative_to(ROOT)), _line_of(text, hit.start()), origin))
            if origin not in allowed:
                problems.append(f"{path.relative_to(ROOT)} names {origin}")
    named = {str(p.relative_to(ROOT)) for p in TEXT_POPULATION if p.is_file()}
    skipped = sorted(named - seen)
    assert skipped == [], (
        f"{skipped} is named in this scan's own population and yields no text: walk() admits a file "
        f"by suffix, so one suffix missing from TEXT_SUFFIXES removes a carrier the census still "
        f"claims to cover")
    blind = []
    for root in TEXT_POPULATION:
        for path in ([root] if root.is_file() else sorted(root.rglob("*"))):
            if (path.is_file() and path.suffix not in TEXT_SUFFIXES
                    and not (SKIP_DIRS & set(path.parts))
                    and LOOPBACK_ORIGIN.search(read(path))):
                blind.append(str(path.relative_to(ROOT)))
    assert blind == [], (
        f"{sorted(blind)} state a loopback origin and are not in the scan: the census is only as "
        f"complete as the suffix list that admits files, so an extension this repository has not "
        f"thought of is a hole rather than an absence")
    assert len(rows) >= MIN_LOOPBACK_URLS, (
        f"the loopback scan found {len(rows)} URLs on port {'/'.join(sorted(ports))} across "
        f"{[str(p.relative_to(ROOT)) for p in TEXT_POPULATION]} -- a scan that reads nothing "
        f"clears nothing")
    assert problems == [], (
        f"the allow-list admits {sorted(allowed)}, but {sorted(set(problems))} is written in the "
        f"shipped text -- a browser treats those hosts as different origins, which is why "
        f"e2e/README.md's first trap tells a reader to use `localhost`, not `127.0.0.1`")


def test_the_reset_link_default_and_the_allow_list_default_are_one_origin():
    """`AuthService`'s comment is a claim about two files, and it had no reader."""
    source = read(AUTH_SERVICE)
    assert "same origin CORS already trusts" in source, (
        "AuthService no longer states that the reset base URL defaults to the CORS origin; the "
        "pairing still has to hold, so re-home the sentence rather than delete this case")
    authority = cors_authority()
    yml_web = origin_of(interpolation_default(read(YML), "APP_WEB_BASE_URL", "application.yml"))
    value_web = origin_of(SPRING_REF.search(source).group("default"))
    assert {yml_web, value_web} == authority, (
        f"the reset-link defaults are {sorted({yml_web, value_web})} but the allow-list default is "
        f"{sorted(authority)}: a stack started without APP_WEB_BASE_URL mails a link to an origin "
        f"CORS rejects, and the page cannot submit the new password")
    for path in (ENV_DEV, ENV_PROD):
        allowed = origin_list(env_assignment(path, "APP_CORS_ORIGINS"))
        link = origin_of(env_assignment(path, "APP_WEB_BASE_URL"))
        assert link in allowed, (
            f"{path.name} sets the reset base URL to {link}, outside its own APP_CORS_ORIGINS "
            f"{sorted(allowed)} -- the reader who copies this file gets the broken reset mail")


def test_the_security_docs_method_and_header_lists_are_the_cors_configuration_own():
    bullet = cors_bullet()
    methods = re.search(r"methods `([^`]+)`", bullet)
    headers = re.findall(r"`([A-Za-z][\w-]*)`", bullet.split("headers")[-1])
    assert methods and headers, (
        f"SECURITY.md's transport bullet {bullet!r} no longer states the methods and headers as "
        f"lists, so a reader has nothing for SecurityConfig to be checked against")
    documented_methods = [part.strip() for part in methods.group(1).split("/")]
    allowed_methods = config_string_list("setAllowedMethods")
    allowed_headers = config_string_list("setAllowedHeaders")
    problems = []
    if {m.upper() for m in documented_methods} != {m.upper() for m in allowed_methods}:
        problems.append(f"methods: doc {sorted(documented_methods)} vs config "
                        f"{sorted(allowed_methods)}")
    if {h.lower() for h in headers} != {h.lower() for h in allowed_headers}:
        problems.append(f"headers: doc {sorted(headers)} vs config {sorted(allowed_headers)}")
    for name, documented, decided in (("methods", documented_methods, allowed_methods),
                                      ("headers", headers, allowed_headers)):
        if len(documented) != len(set(documented)):
            problems.append(f"{name}: SECURITY.md lists one name twice")
        if len(decided) != len(set(decided)):
            problems.append(f"{name}: SecurityConfig allows one name twice")
    assert problems == [], (
        "the allow-list is a security property and only the bean decides it --\n"
        + "\n".join(problems)
        + "\n-- the bullet's `only` is a claim about the whole list, so both ends have to be "
          "complete, not merely overlapping")


def test_each_cors_allow_list_is_written_by_one_author():
    for call in ("setAllowedOrigins", "setAllowedMethods", "setAllowedHeaders"):
        sites = setter_sites(call)
        assert sites, f"nothing in backend/src/main calls .{call}() any more"
        assert len(sites) == 1, (
            f"{call} is called at {sites}: two authors of one allow-list means a reader can fix "
            f"one file and still have a browser refused")
        assert sites[0][0] == "SecurityConfig.java", (
            f"{call} is decided in {sites[0]}, not SecurityConfig.java -- which is the file "
            f"SECURITY.md and this gate read")


def test_every_header_the_browser_sends_is_allowed_and_every_allowed_header_has_a_sender():
    sites = browser_header_sites()
    assert len(sites) >= MIN_HEADER_SITES, (
        f"the header census read {len(sites)} sites under frontend/src, fewer than "
        f"{MIN_HEADER_SITES}: a census that finds nothing lets the allow-list drift unseen")
    sent = {name.lower() for _f, _n, name in sites}
    allowed = {name.lower() for name in config_string_list("setAllowedHeaders")}
    unallowed = sorted(sent - allowed - SAFELISTED_HEADERS)
    assert unallowed == [], (
        f"frontend/src puts {unallowed} on a request and setAllowedHeaders {sorted(allowed)} does "
        f"not admit it, so the preflight fails and the caller sees a silent failure -- the trap "
        f"e2e/README.md warns about. The census: {sorted(sites)}")
    admitted_elsewhere = sorted(allowed - sent - SAFELISTED_HEADERS)
    assert admitted_elsewhere == sorted(SERVER_ONLY_HEADERS), (
        f"the allow-list admits {admitted_elsewhere}, which no browser sends and which the ledger "
        f"{sorted(SERVER_ONLY_HEADERS)} does not explain -- an unexplained entry is a cross-origin "
        f"surface nobody is accountable for")
    for name, reason in sorted(SERVER_ONLY_HEADERS.items()):
        assert len(reason) > 20, f"{name}'s ledger reason has to say who sends it"
        senders = server_header_senders(name)
        assert senders, (
            f"{name} is ledgered as server-to-service ({reason!r}) but no backend or ai-service "
            f"source puts that header on a request, so the reason is a story")


def test_the_middleware_headers_are_server_side_and_not_browser_traffic():
    """The one file the header census refuses, pinned to the role the refusal names."""
    path = FRONTEND_SRC / "middleware.ts"
    assert SERVER_MODULES == {path}, (
        f"the refusal list is {sorted(p.name for p in SERVER_MODULES)}; it was written for Next's "
        f"middleware module, and a second entry needs its own case rather than a wider net")
    text = read(path)
    assert re.search(r"export (?:function|const) middleware\b", text), (
        "the refused module no longer exports Next's middleware entry point, so nothing proves "
        "Next is the thing that runs it")
    assert "NextResponse.next(" in text, (
        "the refused module no longer hands a decorated request to Next's renderer, so the "
        "server-side reading of its headers is a story")
    names = {hit["name"].lower() for hit in HEADER_SETTER.finditer(text)}
    assert {"x-nonce", "content-security-policy"} <= names, (
        f"the refused module sets {sorted(names)}, not the CSP nonce pair this refusal was written "
        f"for; re-read the refusal rather than widen it")
    assert not re.search(r"\bfetch\s*\(|XMLHttpRequest|setRequestHeader\(", text), (
        "the refused module sends a browser-shaped request now, so a header it sets does reach a "
        "preflight and the refusal would hide one the allow-list has to admit")
    sent = {name.lower() for _f, _n, name in browser_header_sites()}
    assert not ({"x-nonce", "content-security-policy"} & sent), (
        "the browser census still reports the middleware's nonce pair as a header a browser sends, "
        "so the refusal above is no longer in effect")


def test_the_browser_stays_inside_the_allowed_methods_and_no_allowed_method_is_dead():
    sites = browser_method_sites()
    assert len(sites) >= MIN_METHOD_SITES, (
        f"the method census read {len(sites)} sites, fewer than {MIN_METHOD_SITES}: a browser "
        f"asking for a method the bean never allowed is what this case exists to catch")
    used = {method.upper() for _f, _n, method in sites}
    allowed = {method.upper() for method in config_string_list("setAllowedMethods")}
    missing = sorted(used - allowed)
    assert missing == [], (
        f"frontend/src sends {missing}, which setAllowedMethods {sorted(allowed)} does not admit")
    unused = sorted(allowed - used - {PREFLIGHT_METHOD})
    assert unused == [], (
        f"setAllowedMethods admits {unused}, which no shipped browser code uses and which is not "
        f"the preflight method -- a reader auditing SECURITY.md would take a wider list than the "
        f"app needs as intentional. Used: {sorted(used)} from {sorted(sites)}")


def test_the_production_stack_carries_the_origin_from_its_own_file():
    """The override must pass the origin and must not default it -- each half fails differently."""
    prod = read(COMPOSE_PROD)
    assert re.search(r"^\s*APP_CORS_ORIGINS:", prod, re.M), (
        "docker-compose.prod.yml no longer passes APP_CORS_ORIGINS, so the backend falls back to "
        "application.yml's development default and a production site quietly allows localhost")
    assert interpolation_default(prod, "APP_CORS_ORIGINS", "docker-compose.prod.yml") is None, (
        "docker-compose.prod.yml now defaults APP_CORS_ORIGINS, so a stack whose .env.prod omits "
        "the variable runs an allow-list nobody chose instead of failing on the missing one")
    prod_origins = origin_list(env_assignment(ENV_PROD, "APP_CORS_ORIGINS"))
    authority = cors_authority()
    assert len(prod_origins) >= 2, (
        f".env.prod.example now lists {sorted(prod_origins)}; the membership test below is only "
        f"worth running against an allow-list wider than a single origin")
    assert not (prod_origins & authority), (
        f".env.prod.example's APP_CORS_ORIGINS {sorted(prod_origins)} still names a development "
        f"origin from {sorted(authority)}, which is the origin the shipped code defaults to")
