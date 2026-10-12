"""DEPLOYMENT.md's port tables, SECURITY.md's reach sentence and the provider lists are the files' own.

The deployment guide is read once, at the worst possible moment -- when something is already
broken and someone is trying to reach the stack. Two of its tables are pure claims about other
files, one prose sentence is a security claim about all of them, and nothing kept any of it honest.

The sentence is the reason this gate exists. SECURITY.md said "All Docker service ports bind
`127.0.0.1` (see `docker-compose.yml`) so nothing is exposed on the host network by default", and
DEPLOYMENT.md headed its table "Service endpoints (all bound to `127.0.0.1` only)". Both were true
when there was one compose file. `docker-compose.prod.yml` now republishes `backend` as
`- "8080:8080"` and `frontend` as `- "3000:3000"`, and an entry with no interface prefix is bound
by Docker on **every interface of the host** -- so the stack the guide's own Quick Start brings up
(`-f docker-compose.yml -f docker-compose.prod.yml`) answers to the network, and the reverse proxy
is not the only path in. Two shipped parsers could not see the contradiction: the env-examples
gate's `compose_host_ports()` matched the literal string `"127.0.0.1:` inside its population
regex, so a binding without the prefix is not in the census at all, and both parsers read only
`docker-compose.yml`, so the override was never in any population. The weaker copy is deleted
there rather than duplicated here: one scan per claim.

What is measured now:

* `published_bindings()` reads a compose *text* and returns (service, host port, container port,
  interface) for every entry inside a `ports:` block -- prefix-agnostic, with Docker's unprefixed
  default spelled as `0.0.0.0`. It is proved against a fixture holding both spellings and an
  `environment:` decoy, not against the shipped files: pinning "at least one open binding exists"
  would have made *closing* the exposure a gate failure.
* each ports table is reconciled with the file its heading names, in both directions, per row, and
  including the Reach column. The heading and a row floor come from the same scan, so a table that
  loses its heading cannot be reconciled against an empty row set.
* a service the docs call internal-only or not exposed must be bound to loopback in every compose
  file that publishes it.
* a documentation line that states a loopback binding in blanket words is a claim about the whole
  stack, so it is judged against every compose file and may stand only while none of them
  publishes a port another way. Table rows are exempt because the Reach column states their reach
  exactly and case two already pins them; that is also why the phrasing has to be per-file and
  unquantified in prose -- the trigger list is printed in the failure so a writer learns it once.
* the provider lists and the Redis timeout pin are unchanged.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
DOC = ROOT / "docs" / "DEPLOYMENT.md"
SECURITY_DOC = ROOT / "docs" / "SECURITY.md"
COMPOSE = ROOT / "docker-compose.yml"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
COMPOSE_FILES = (COMPOSE, COMPOSE_PROD)
# the documents a reader takes as the word on how far this stack's ports reach
REACH_DOCS = (ROOT / "README.md", DOC, SECURITY_DOC)
SETTINGS = ROOT / "ai-service" / "app" / "core" / "config.py"
APP_YML = ROOT / "backend" / "src" / "main" / "resources" / "application.yml"

# Docker binds a `HOST:CONTAINER` entry with no prefix on every interface of the host. The census
# spells that fact as an interface value; the docs have to say it in words a reader can act on.
OPEN_REACH = "every interface"
LOOPBACK_REACH = "127.0.0.1"
UNPREFIXED = "0.0.0.0"
LOOPBACK_VALUES = {"127.0.0.1", "localhost", "::1"}

DEV_TABLE = re.compile(r"^### Ports published by `docker-compose\.yml`")
PROD_TABLE = re.compile(r"^### Ports published by the production override")

MIN_TABLE_ROWS = 3

BLANKET = re.compile(r"\b(?:all|every|both|any|only|nothing|alone|exclusively)\b", re.I)
LOOPBACK_MENTION = re.compile(r"127\.0\.0\.1|\bloopback\b", re.I)
INTERNAL_MARK = re.compile(r"internal[-\s]+only|not exposed", re.I)

SERVICE_HEADER = re.compile(r"^  ([a-z][\w-]*):\s*$")
BLOCK_KEY = re.compile(r"^    ([\w-]+):")
BINDING = re.compile(
    r'^\s*-\s*"?(?:(?P<iface>[^":\s]+):)?(?P<host>\d+):(?P<container>\d+)"?\s*$'
)
HEADING = re.compile(r"^#{1,6} ")

FIXTURE = """services:
  loopback-service:
    image: example
    ports:
      - "127.0.0.1:7001:7001"
  open-service:
    ports:
      - "7002:7002"
  decoy-service:
    ports:
      - "127.0.0.1:7003:7003"
    environment:
      - "UPSTREAM=127.0.0.1:7004:7004"
    healthcheck:
      test: ["CMD", "curl", "127.0.0.1:7005"]
"""


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def published_bindings(text: str) -> list[tuple[str, int, int, str]]:
    """(service, host port, container port, interface) for each `ports:` entry in one compose text.

    Only entries inside a `ports:` block count: a service's `environment:` list can hold a value
    shaped exactly like a binding, and reading it would invent a published port.
    """
    rows: list[tuple[str, int, int, str]] = []
    service = None
    in_ports = False
    for line in text.split("\n"):
        header = SERVICE_HEADER.match(line)
        if header:
            service, in_ports = header.group(1), False
            continue
        key = BLOCK_KEY.match(line)
        if key:
            in_ports = key.group(1) == "ports"
            continue
        binding = BINDING.match(line) if in_ports and service else None
        if binding:
            rows.append(
                (
                    service,
                    int(binding["host"]),
                    int(binding["container"]),
                    binding["iface"] or UNPREFIXED,
                )
            )
    return rows


def reach_of(interface: str) -> str:
    """What an interface value means for how far a published port reaches."""
    return LOOPBACK_REACH if interface in LOOPBACK_VALUES else OPEN_REACH


def published_reach(path: Path) -> set[tuple[str, int, str]]:
    """(service, host port, reach) for every binding one compose file publishes."""
    return {
        (service, host, reach_of(interface))
        for service, host, _container, interface in published_bindings(read(path))
    }


def open_bindings() -> list[tuple[str, str, int]]:
    """(file, service, host port) for each binding that is not loopback-only, in either file."""
    return sorted(
        (
            path.name,
            service,
            host,
        )
        for path in COMPOSE_FILES
        for service, host, _container, interface in published_bindings(read(path))
        if interface not in LOOPBACK_VALUES
    )


def table_rows(text: str, heading: re.Pattern[str], label: str) -> list[tuple[str, int, str]]:
    """(service, host port, reach cell) for the pipe table under one heading, up to the next heading."""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if heading.match(line)]
    assert len(starts) == 1, (
        f"DEPLOYMENT.md no longer has exactly one {label} table heading (found {len(starts)}), "
        f"so {label} published ports would be reconciled against a row set read from nowhere")
    rows: list[tuple[str, int, str]] = []
    for line in lines[starts[0] + 1:]:
        if HEADING.match(line):
            break
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not re.fullmatch(r"[a-z][\w-]*", cells[0]) or not cells[1].isdigit():
            continue
        rows.append((cells[0], int(cells[1]), cells[2]))
    assert len(rows) >= MIN_TABLE_ROWS, (
        f"the {label} port table yielded {len(rows)} rows, fewer than the {MIN_TABLE_ROWS} "
        f"the published bindings require, so the reconciliation below would be judging a stub")
    return rows


def documented_reach(cell: str) -> str:
    """Normalize a Reach cell to the census's vocabulary; anything else stays as written and mismatches."""
    return OPEN_REACH if "interface" in cell.lower() else cell


def loopback_lines() -> list[tuple[str, int, str]]:
    """(file, line number, text) for prose that mentions a loopback binding, pipe rows excluded."""
    out: list[tuple[str, int, str]] = []
    for path in REACH_DOCS:
        for number, line in enumerate(read(path).split("\n"), start=1):
            if line.lstrip().startswith("|"):
                continue
            if LOOPBACK_MENTION.search(line):
                out.append((path.name, number, line.strip()))
    return out


def internal_only_services() -> dict[str, list[str]]:
    """service -> the doc lines that call it internal-only or not exposed.

    Matched tolerantly because the guide writes `AI service` in its checklist and `ai-service`
    in its table, and the compose service name is the only identity either can be checked against.
    """
    services = sorted({row[0] for path in COMPOSE_FILES
                       for row in published_bindings(read(path))})
    hits: dict[str, list[str]] = {}
    for path in REACH_DOCS:
        for number, line in enumerate(read(path).split("\n"), start=1):
            if not INTERNAL_MARK.search(line):
                continue
            for service in services:
                pattern = re.escape(service).replace(r"\-", "[- ]")
                if re.search(pattern, line, re.I):
                    hits.setdefault(service, []).append(f"{path.name}:{number}")
    return hits


def provider_list(env_var: str) -> set[str]:
    """The values the doc says a provider variable accepts, as backticked tokens."""
    for line in read(DOC).split("\n"):
        if f"`{env_var}`" not in line:
            continue
        tokens = re.findall(r"`([^`]+)`", line)
        if env_var in tokens and len(tokens) > 1:
            return set(tokens) - {env_var}
    raise AssertionError(f"DEPLOYMENT.md no longer enumerates {env_var}")


def settings_list(field: str) -> set[str]:
    """The values `config.py` says the same variable accepts."""
    text = read(SETTINGS)
    match = re.search(
        r"^\s*" + field + r":\s*str\s*=\s*\"[^\"]*\"\s*#\s*(.+)$", text, re.M
    )
    assert match, f"config.py no longer comments the accepted {field} values"
    return {
        token.strip() for token in re.split(r"[|,]", match.group(1)) if token.strip()
    }


def test_the_binding_parser_reads_both_binding_spellings():
    rows = published_bindings(FIXTURE)

    prefixed = [row for row in rows if row[0] == "loopback-service"]
    assert prefixed == [("loopback-service", 7001, 7001, "127.0.0.1")], (
        f"a `\"127.0.0.1:7001:7001\"` entry census-reads as {prefixed}: the parser must keep the "
        f"interface it is written with, or a loopback binding and an open one collapse into the "
        f"same row")

    unprefixed = [row for row in rows if row[0] == "open-service"]
    assert unprefixed == [("open-service", 7002, 7002, UNPREFIXED)], (
        f"a `\"7002:7002\"` entry census-reads as {unprefixed}, and Docker binds an entry with no "
        f"interface prefix on every interface of the host -- spelling that default is the whole "
        f"point of the reach column")

    outside = [row for row in rows if row[0] == "decoy-service"]
    assert outside == [("decoy-service", 7003, 7003, "127.0.0.1")], (
        f"a service whose `ports:` block is followed by an `environment:` entry shaped like a "
        f"binding reads as {outside}: only entries inside the `ports:` block are published ports")


def test_each_ports_table_is_the_binding_table_of_the_file_it_names():
    problems: list[str] = []
    for label, heading, path in (
        ("development", DEV_TABLE, COMPOSE),
        ("production override", PROD_TABLE, COMPOSE_PROD),
    ):
        rows = table_rows(read(DOC), heading, label)
        published = published_reach(path)
        keys = {(service, host) for service, host, _reach in published}
        for service, host, cell in sorted(rows):
            if (service, host) not in keys:
                problems.append(
                    f"{label}: the table names {service} {host}, which {path.name} "
                    f"does not publish at all")
                continue
            actual = sorted(r for s, h, r in published if (s, h) == (service, host))
            if documented_reach(cell) not in actual:
                problems.append(
                    f"{label}: the table says {service} {host} reaches {cell}, "
                    f"but {path.name} binds it on {actual}")
        documented = {(service, host) for service, host, _cell in rows}
        for service, host, reach in sorted(published):
            if (service, host) not in documented:
                problems.append(
                    f"{label}: {path.name} publishes {service} {host} on {reach} and "
                    f"the table has no row for it")
    assert problems == [], (
        "DEPLOYMENT.md's port tables and the compose files disagree --\n"
        + "\n".join(problems)
        + "\n-- the table is the reader's only map of which port reaches how far")


def test_the_doc_labels_which_minio_port_is_the_console():
    """MinIO's console is a second port, and the doc is the only place that says what it is."""
    published = published_bindings(read(COMPOSE))
    minio = {host for service, host, _c, _i in published if service == "minio"}
    claimed = re.search(r"minio\s*\|\s*\d+\s*\|.*?console on (\d+)", read(DOC))
    assert claimed, "DEPLOYMENT.md no longer says which port is MinIO's console"
    assert int(claimed.group(1)) in minio, (
        f"DEPLOYMENT.md sends readers to port {claimed.group(1)} for the MinIO console, "
        f"but compose publishes {sorted(minio)} for the minio service")


def test_what_the_docs_call_internal_only_is_bound_to_loopback():
    internal = internal_only_services()
    assert internal, (
        "no document calls any compose service internal-only or not exposed, so this case would "
        "be judging an empty set while the claim it exists to police -- an internal service "
        "published on every interface -- goes unmeasured")
    exposed = [
        (path.name, service, host, reach_of(interface))
        for path in COMPOSE_FILES
        for service, host, _container, interface in published_bindings(read(path))
        if service in internal and interface not in LOOPBACK_VALUES
    ]
    named = {service: sorted(lines) for service, lines in sorted(internal.items())}
    assert exposed == [], (
        f"the docs call {named} internal-only, but {exposed} is published with no interface "
        f"prefix, so a network peer can reach what the documentation says is private")


def test_a_blanket_loopback_sentence_is_a_claim_about_every_compose_file():
    mentions = loopback_lines()
    files_seen = {name for name, _number, _line in mentions}
    assert {"DEPLOYMENT.md", "SECURITY.md"} <= files_seen, (
        f"the reach scan read {[p.name for p in REACH_DOCS]} and found loopback prose only in "
        f"{sorted(files_seen)} -- a document whose reach paragraphs were never read cannot be "
        f"cleared by this case, so the floor names the documents the claim lives in")
    blanket = [hit for hit in mentions if BLANKET.search(hit[2])]
    problems = []
    if blanket:
        published = open_bindings()
        if published:
            for name, number, line in blanket:
                problems.append(
                    f"{name}:{number} says {line!r} while {published} is reachable "
                    f"on every interface in another file")
    assert problems == [], (
        "\n".join(problems)
        + "\n-- blanket words (all, every, both, any, only, nothing, alone, exclusively) beside a "
          "loopback mention promise the whole stack, so state a per-file fact in the port tables' "
          "Reach column instead, or phrase the sentence without a quantifier")


def test_the_provider_lists_are_the_ones_the_settings_accept():
    for env_var, field in (
        ("LLM_PROVIDER", "llm_provider"),
        ("EMBEDDING_PROVIDER", "embedding_provider"),
    ):
        documented, accepted = provider_list(env_var), settings_list(field)
        assert documented == accepted, (
            f"DEPLOYMENT.md lists {sorted(documented)} for {env_var} but config.py accepts "
            f"{sorted(accepted)} -- a reader configuring a provider the doc omits gets a "
            f"ConfigError at boot with nothing to point at"
        )


def test_the_redis_timeout_the_doc_pins_is_the_one_the_backend_defaults_to():
    claimed = re.search(r"pinned to (\d+)ms", read(DOC))
    assert claimed, "DEPLOYMENT.md no longer states the Redis client timeout it pins"
    yml = read(APP_YML)
    for knob in ("REDIS_TIMEOUT", "REDIS_CONNECT_TIMEOUT"):
        found = re.search(r"\$\{" + knob + r":(\d+)ms\}", yml)
        assert found, f"application.yml no longer defaults {knob}"
        assert int(found.group(1)) == int(claimed.group(1)), (
            f"DEPLOYMENT.md says the Redis timeout is pinned to {claimed.group(1)}ms but "
            f"application.yml defaults {knob} to {found.group(1)}ms"
        )
