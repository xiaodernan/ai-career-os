"""The three application services start when they can answer, not when they have started.

`docker compose ps` prints `running` for a container that started and never answered, and only
postgres, redis and minio carried a healthcheck. So `--profile app up -d` handed the browser a
frontend whose backend was still booting, and a backend whose ai-service was still importing its
app: the first requests of a fresh clone met a 502, or a stack that was "up" and half dead.
`depends_on` alone orders starts; only a healthcheck makes the order mean "answers".

What is measured now, in both compose files:

* every application service carries a healthcheck that fetches an HTTP route on the container's
  own loopback;
* the port in that URL is a container port the service publishes -- a probe aimed at a port
  nobody maps answers something else, or nothing, and its verdict says nothing about this app;
* every dependency of an application service is the long form with `condition: service_healthy`,
  so a start is gated on an answer rather than a process;
* the path in the probe is the route DEPLOYMENT.md's Monitoring Endpoints table names, so the
  guide and the probe cannot describe different things.

The parsers are exercised against fixtures, not only against the shipped files: a gate that can
only say "the files are good" turns closing a problem into a failure one edit later. The fixture
pair carries one stack that waits and one that fails each way, so the same function is shown both
green and red. The data stores are decoys in the clean fixture: `pg_isready` and `mc ready local`
are not HTTP probes, and the gate must not demand they become one.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
COMPOSE = ROOT / "docker-compose.yml"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
DOC = ROOT / "docs" / "DEPLOYMENT.md"

APP_SERVICES = ("ai-service", "backend", "frontend")
DOC_LABELS = {"Backend": "backend", "AI Service": "ai-service", "Frontend": "frontend"}

SERVICES_HEADING = re.compile(r"^services:\s*$")
SERVICE = re.compile(r"^  ([a-z][\w-]*):\s*$")
KEY = re.compile(r"^    ([\w-]+):\s*(.*)$")
ENTRY = re.compile(r"^      ([\w-]+):\s*(.*)$")
LIST_ENTRY = re.compile(r"^      - ([a-z][\w-]*)\s*$")
CONDITION = re.compile(r"^        condition:\s*(\S+)\s*$")
BINDING = re.compile(
    r'^\s*-\s*"?(?:(?P<iface>[^":\s]+):)?(?P<host>\d+):(?P<container>\d+)"?\s*$'
)
LOOPBACK_URL = re.compile(
    r"https?://(?:127\.0\.0\.1|localhost):(?P<port>\d+)(?P<path>/[^'\"\s]*)?"
)
MONITOR_ROW = re.compile(r"^\|\s*(Backend|AI Service|Frontend)\s*\|\s*`GET\s+([^`\s]+)")

CLEAN = """services:
  ai-service:
    image: example
    ports:
      - "127.0.0.1:8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "urllib.request.urlopen('http://127.0.0.1:8000/health')"]
    depends_on:
      postgres:
        condition: service_healthy
  backend:
    image: example
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/api/v1/health"]
    depends_on:
      postgres:
        condition: service_healthy
  frontend:
    image: example
    ports:
      - "3000:3000"
    healthcheck:
      test: ["CMD", "node", "-e", "fetch('http://127.0.0.1:3000/')"]
    depends_on:
      backend:
        condition: service_healthy
  postgres:
    image: example
  minio:
    image: example
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]

volumes:
  pgdata:
"""

BROKEN = """services:
  ai-service:
    image: example
    ports:
      - "127.0.0.1:8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "urllib.request.urlopen('http://127.0.0.1:9000/health')"]
  backend:
    image: example
    ports:
      - "8080:8080"
    depends_on:
      - postgres
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/api/v1/health"]
  frontend:
    image: example
    ports:
      - "3000:3000"
  postgres:
    image: example

volumes:
  pgdata:
"""

ROUTES = {"ai-service": "/health", "backend": "/api/v1/health", "frontend": "/"}


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def service_blocks(text: str) -> dict[str, dict[str, list[str]]]:
    """service -> top-level key -> the lines under that key, for one compose text.

    Only the `services:` section is read: `volumes:`' children sit at the same indent as a
    service header, and reading them would invent services that no compose command starts.
    """
    out: dict[str, dict[str, list[str]]] = {}
    inside = False
    service: str | None = None
    key: str | None = None
    for line in text.split("\n"):
        if SERVICES_HEADING.match(line):
            inside, service, key = True, None, None
            continue
        if not inside:
            continue
        if line and not line.startswith(" "):
            break
        header = SERVICE.match(line)
        if header:
            service, key = header.group(1), None
            out[service] = {}
            continue
        if service is None:
            continue
        field = KEY.match(line)
        if field:
            key = field.group(1)
            out[service][key] = []
            continue
        if key is not None:
            out[service][key].append(line)
    return out


def dependencies(block: dict[str, list[str]]) -> dict[str, str | None]:
    """dependency -> its condition, or None when the entry is the short list form."""
    out: dict[str, str | None] = {}
    current: str | None = None
    for line in block.get("depends_on", []):
        entry = ENTRY.match(line)
        if entry:
            current = entry.group(1)
            out[current] = None
            continue
        listed = LIST_ENTRY.match(line)
        if listed:
            current = listed.group(1)
            out[current] = None
            continue
        condition = CONDITION.match(line)
        if condition and current:
            out[current] = condition.group(1)
    return out


def probes(block: dict[str, list[str]]) -> list[tuple[int, str]]:
    """(port, path) for each loopback HTTP URL the healthcheck's test names."""
    body = "\n".join(block.get("healthcheck", []))
    return [
        (int(found["port"]), found["path"] or "/")
        for found in LOOPBACK_URL.finditer(body)
    ]


def container_ports(block: dict[str, list[str]]) -> set[int]:
    """The container half of every binding the service publishes."""
    return {
        int(binding["container"])
        for line in block.get("ports", [])
        if (binding := BINDING.match(line))
    }


def documented_health_routes() -> dict[str, str]:
    """service -> the GET route DEPLOYMENT.md's Monitoring Endpoints table names for it."""
    routes: dict[str, str] = {}
    for line in read(DOC).split("\n"):
        row = MONITOR_ROW.match(line)
        if row:
            routes[DOC_LABELS[row.group(1)]] = row.group(2)
    return routes


def problems(text: str, routes: dict[str, str]) -> list[str]:
    """Every way one compose text lets an application service start before it answers."""
    found: list[str] = []
    blocks = service_blocks(text)
    for service in APP_SERVICES:
        block = blocks.get(service)
        if block is None:
            found.append(
                f"{service} is not a service this file declares, so nothing waits for it"
            )
            continue
        found_probes = probes(block)
        if len(found_probes) != 1:
            found.append(
                f"{service} has {len(found_probes)} loopback HTTP healthcheck probes, not one, "
                f"so compose proves a process started rather than an app answering"
            )
        else:
            port, path = found_probes[0]
            published = container_ports(block)
            if port not in published:
                found.append(
                    f"{service}'s probe asks port {port} but the service publishes "
                    f"{sorted(published) if published else 'no container port'}"
                )
            expected = routes.get(service)
            if expected is None:
                found.append(f"DEPLOYMENT.md names no health route for {service}")
            elif path != expected:
                found.append(
                    f"{service}'s probe fetches {path} but DEPLOYMENT.md names {expected}"
                )
        for dependency, condition in dependencies(block).items():
            if condition != "service_healthy":
                found.append(
                    f"{service} waits on {dependency} with condition "
                    f"{condition or 'none'} instead of service_healthy"
                )
    return found


def test_both_compose_files_wait_for_an_answer_on_the_route_the_guide_names():
    routes = documented_health_routes()
    assert set(APP_SERVICES) <= set(routes), (
        f"DEPLOYMENT.md's Monitoring Endpoints table yields {routes} for the application "
        f"services; each of {list(APP_SERVICES)} has to state its health route, or the probes "
        f"below are judged against a route no document promises"
    )
    failures: list[str] = []
    for path in (COMPOSE, COMPOSE_PROD):
        for problem in problems(read(path), routes):
            failures.append(f"{path.name}: {problem}")
    assert failures == [], (
        "an application service can start before it answers --\n"
        + "\n".join(failures)
        + "\n-- `running` is not a health claim; probe the route, on a published port, "
          "before a dependent service is allowed to start"
    )


def test_the_gate_is_green_on_a_stack_that_waits_and_says_which_rule_each_broken_one_broke():
    assert problems(CLEAN, ROUTES) == [], (
        "the clean fixture -- three probed app services, long-form dependencies, and a data "
        "store whose healthcheck is not an HTTP probe -- must pass the gate, or the gate is "
        "grading something other than what its refusal messages say"
    )
    assert problems(BROKEN, ROUTES) == [
        "ai-service's probe asks port 9000 but the service publishes [8000]",
        "backend waits on postgres with condition none instead of service_healthy",
        "frontend has 0 loopback HTTP healthcheck probes, not one, so compose proves a "
        "process started rather than an app answering",
    ], (
        "a probe on an unpublished port, a short-form dependency and an unprobed app service "
        "each have to be refused by name; a gate that stays green on this fixture cannot "
        "stand between a half-started stack and the first request"
    )


def test_the_shipped_files_are_the_population_this_gate_grades():
    for path in (COMPOSE, COMPOSE_PROD):
        blocks = service_blocks(read(path))
        assert set(APP_SERVICES) <= set(blocks), (
            f"{path.name} no longer declares every application service ({sorted(blocks)}), so "
            f"the gate would be policing a stack smaller than the one the guide describes"
        )
        probed = [service for service in APP_SERVICES if probes(blocks[service])]
        assert probed == list(APP_SERVICES), (
            f"{path.name} gives a healthcheck to {probed}; when no application service is "
            f"probed the case above is vacuously green"
        )
    assert len(documented_health_routes()) == len(APP_SERVICES)
