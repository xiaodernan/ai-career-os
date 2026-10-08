"""DEPLOYMENT.md's port table and provider lists are the compose file's and the settings' own.

The deployment guide is read once, at the worst possible moment -- when something is
already broken and someone is trying to reach the stack. Two of its tables are pure
claims about other files, and neither had anything keeping it honest.

The port table names a host port per service. Those numbers live in
`docker-compose.yml`, one per `ports:` entry, and the whole point of the table is that a
reader should not have to open the compose file to learn them. Nothing stopped the two
from diverging: a port moves in compose to dodge a clash, the table keeps the old number,
and the next person spends an afternoon on a connection refused that the doc promised
would work. The same table also claims which port is MinIO's *console* rather than its
API, which is the difference between reaching the S3 endpoint and reaching the web UI.

The provider lists are the other half. `LLM_PROVIDER` and `EMBEDDING_PROVIDER` are
enumerated in `ai-service/app/core/config.py`, where a new provider is one edit away from
shipping without the doc hearing about it -- and a reader who configures a provider the
doc never mentioned gets a `ConfigError` at boot with nothing to point at.

So both are read out of the files that decide them and reconciled with the doc.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
DOC = ROOT / "docs" / "DEPLOYMENT.md"
COMPOSE = ROOT / "docker-compose.yml"
SETTINGS = ROOT / "ai-service" / "app" / "core" / "config.py"
APP_YML = ROOT / "backend" / "src" / "main" / "resources" / "application.yml"

CONTAINER_PREFIX = "careeros-"
MINIMUM_SERVICES = 6


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def published_ports() -> dict[str, set[int]]:
    """Every host port each compose service publishes, keyed by container name."""
    out: dict[str, set[int]] = {}
    service = None
    for line in read(COMPOSE).split("\n"):
        header = re.match(r"^  ([a-z][\w-]*):\s*$", line)
        if header:
            service = header.group(1)
            continue
        named = re.match(r"\s+container_name:\s*(\S+)", line)
        if named:
            service = named.group(1)
            out.setdefault(service, set())
            continue
        binding = re.search(r'-\s*"[^"]*?(\d+):(\d+)"', line)
        if binding and service:
            out.setdefault(service, set()).add(int(binding.group(1)))
    return out


def port_table() -> dict[str, int]:
    """The `| service | host port |` rows of the deployment guide."""
    out = {}
    for line in read(DOC).split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if (
            len(cells) < 2
            or not cells[0]
            or cells[0].startswith("---")
            or cells[0] == "Service"
        ):
            continue
        if re.fullmatch(r"\d+", cells[1]):
            out[cells[0]] = int(cells[1])
    return out


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


def compose_service_for(doc_name: str, published: dict[str, set[int]]) -> str:
    """The compose container serving the doc's service name.

    The doc writes `ai-service` where the compose file names the container
    `careeros-ai`, so the match is on the first segment rather than on equality.
    """
    stem = doc_name.split("-")[0]
    owners = [
        name
        for name in published
        if name.startswith(CONTAINER_PREFIX)
        and name[len(CONTAINER_PREFIX) :].startswith(stem)
    ]
    assert owners, f"no compose service publishes anything for {doc_name!r}"
    return owners[0]


def test_every_port_the_table_names_is_a_port_the_compose_publishes():
    published = published_ports()
    table = port_table()
    assert len(table) >= MINIMUM_SERVICES, f"only {len(table)} port rows parsed"
    wrong = {}
    for service, port in sorted(table.items()):
        if port not in published[compose_service_for(service, published)]:
            wrong[service] = (
                port,
                sorted(published[compose_service_for(service, published)]),
            )
    assert wrong == {}, (
        "DEPLOYMENT.md's port table disagrees with docker-compose.yml: "
        + ", ".join(
            f"{name} says {port} but compose publishes {actual}"
            for name, (port, actual) in wrong.items()
        )
    )


def test_the_console_port_the_doc_names_is_published_too():
    """MinIO's console is a second port, and the doc is the only place that says so."""
    minio = published_ports()[CONTAINER_PREFIX + "minio"]
    claimed = re.search(r"minio\s*\|\s*\d+\s*\|.*?console on (\d+)", read(DOC))
    assert claimed, "DEPLOYMENT.md no longer says which port is MinIO's console"
    assert int(claimed.group(1)) in minio, (
        f"DEPLOYMENT.md sends readers to port {claimed.group(1)} for the MinIO console, "
        f"but compose publishes {sorted(minio)} for careeros-minio"
    )


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
