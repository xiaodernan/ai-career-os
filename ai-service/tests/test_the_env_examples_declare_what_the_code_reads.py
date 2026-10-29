"""The env examples are the contract a reader fills in, and they had drifted both ways.

docs/DEPLOYMENT.md says `.env.example` is "the single source of truth for the full variable
list". It was not. Seven variables `backend/src/main/resources/application.yml` reads were
in no example at all -- `AI_SERVICE_BASE_URL` (how the backend reaches ai-service at all),
`RATELIMIT_AUTH_PER_MINUTE` and `RATELIMIT_AI_PER_MINUTE` (the two rate limits), and the
two Redis client timeouts the same doc's Redis paragraph names by name. Going the other
way, `.env.example` declared `AI_SERVICE_PORT`, which nothing reads -- the image hardcodes
`--port 8000` and ai-service's Settings field is `PORT` -- and `.env.prod.example` declared
`EMBEDDING_DIMENSIONS`, which is `EMBEDDING_DIM` everywhere else. A production reader who
filled in `.env.prod` faithfully set a variable no code looks at, and would have shipped
with `APP_WEB_BASE_URL` unset, which puts `http://localhost:3000` in every password-reset
email.

So both examples are read as claims and checked against the sources that would have to
honour them:

* every `${VAR}` the backend's `application.yml` reads is declared in `.env.example`;
* every variable either example declares is read somewhere -- the backend's yml and
  `@Value` sites, ai-service's pydantic Settings (field names uppercased, which is how
  pydantic-settings binds them), the compose files, the Dockerfiles, the frontend source
  and the scripts -- because a variable nothing reads is a knob that does not turn
  anything;
* the container names DEPLOYMENT.md's own commands exec into exist in the prod compose.

The port table is not measured here. It was, by a `compose_host_ports()` that matched the
literal string `"127.0.0.1:` inside its own population regex and read only
`docker-compose.yml`, so a binding written without that prefix was not in the census the
doc was compared to and the production override was never in a census at all. The weaker
copy is deleted rather than duplicated: one scan per claim, and the scan that reads both
compose files and the interface each port is bound to lives in
`test_the_deployment_doc_names_the_ports_the_compose_publishes.py`.

The read-oracle is deliberately generous: any uppercase token of three or more characters
appearing in a source file counts as read. A phantom is therefore one that appears in no
source at all, which is the only kind worth failing a doc over.

One variable is the deliberate exception: `APP_HTTP_TRUST_FORWARDED_FOR` is a
deployment-topology decision (off for a directly exposed backend, on behind a
proxy), not a knob a checkout sets, and neither example carries it. It is
ledgered by name against DEPLOYMENT.md's checklist, and the last case refuses a
row the document has stopped naming, the code has stopped reading, or an example
has started declaring, so the exemption cannot outlive its sentence.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

ENV_EXAMPLE = ROOT / ".env.example"
ENV_PROD_EXAMPLE = ROOT / ".env.prod.example"
APPLICATION_YML = ROOT / "backend" / "src" / "main" / "resources" / "application.yml"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
DEPLOYMENT = ROOT / "docs" / "DEPLOYMENT.md"
AI_SETTINGS = ROOT / "ai-service" / "app" / "core" / "config.py"

SOURCE_DIRS = ("backend/src/main", "ai-service/app", "frontend/src", "scripts", "e2e")
SOURCE_FILES = ("docker-compose.yml", "docker-compose.prod.yml", "Makefile")

# build output and installed dependencies: neither reads an environment variable
SKIP_DIRS = {"node_modules", "__pycache__", ".venv", "dist", ".next", "target",
             "playwright-report", "test-results"}

# names the prod compose derives for the app, so `.env.prod` does not restate them
COMPOSE_DERIVED = {
    "MINIO_ACCESS_KEY": "prod compose maps it from MINIO_ROOT_USER",
    "MINIO_SECRET_KEY": "prod compose maps it from MINIO_ROOT_PASSWORD",
}

# Variables application.yml reads that no env example carries on purpose: a deployment decision
# about the network the stack sits behind, not a value a checkout sets. DEPLOYMENT.md's production
# checklist is where an operator states it, and the last case below refuses a row that document has
# stopped naming.
DOC_DECLARED = {
    "APP_HTTP_TRUST_FORWARDED_FOR": (
        "off is the only safe value for a directly exposed backend, and behind a proxy the "
        "checklist turns it on; DEPLOYMENT.md carries it instead of an example"),
}


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def declared(path: Path) -> set[str]:
    """Every variable an env example declares, commented lines included."""
    return set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", read(path), re.M))


def backend_reads() -> set[str]:
    """Every `${VAR}` the backend's application.yml interpolates."""
    return set(re.findall(r"\$\{([A-Z][A-Z0-9_]+)", read(APPLICATION_YML)))


def read_somewhere() -> set[str]:
    """Every uppercase token any source file mentions, plus ai-service's Settings fields.

    `RERANK_MODE` never appears literally: pydantic-settings binds it to the field
    `rerank_mode`, so the field names are folded in uppercased or the oracle would call
    half of ai-service's configuration unread.
    """
    tokens: set[str] = set()
    paths: list[Path] = [ROOT / name for name in SOURCE_FILES if (ROOT / name).exists()]
    for directory in SOURCE_DIRS:
        base = ROOT / directory
        if not base.exists():
            continue
        paths.extend(p for p in base.rglob("*")
                     if p.is_file() and not SKIP_DIRS & set(p.parts))
    for path in paths:
        if path.suffix in {".pyc", ".lock", ".png", ".jpg", ".ico", ".woff", ".woff2"}:
            continue
        try:
            tokens.update(re.findall(r"\b[A-Z][A-Z0-9_]{2,}\b", read(path)))
        except UnicodeDecodeError:
            continue
    settings = read(AI_SETTINGS)
    tokens.update(field.upper() for field in re.findall(r"^\s{4}(\w+):", settings, re.M))
    return tokens


def prod_containers() -> set[str]:
    return set(re.findall(r"container_name:\s*(\S+)", read(COMPOSE_PROD)))


def doc_containers() -> set[str]:
    return set(re.findall(r"careeros-[a-z-]+-prod", read(DEPLOYMENT)))


def test_every_variable_the_backend_reads_is_declared_in_the_env_example():
    missing = sorted(backend_reads() - declared(ENV_EXAMPLE) - set(DOC_DECLARED))
    assert missing == [], (
        f"application.yml reads {missing} but .env.example never declares them, and "
        f"DEPLOYMENT.md calls that file the single source of truth for the variable list")


def test_every_variable_the_backend_reads_reaches_the_production_example():
    """`.env.prod` may leave a variable out only when the prod compose supplies it."""
    missing = sorted(backend_reads() - declared(ENV_PROD_EXAMPLE) - set(COMPOSE_DERIVED)
                     - set(DOC_DECLARED))
    assert missing == [], (
        f"application.yml reads {missing} but neither .env.prod.example declares them nor "
        f"docker-compose.prod.yml sets them, so a production stack falls back to the "
        f"development default")


def test_each_doc_declared_variable_is_read_and_named_where_the_doc_says():
    """The exception list is a ledger, not a hiding place: every row is still a live variable."""
    doc = read(DEPLOYMENT)
    problems = []
    for name, reason in sorted(DOC_DECLARED.items()):
        if len(reason) <= 20:
            problems.append(f"{name}'s reason does not say where a deployment states it")
        if name not in backend_reads():
            problems.append(
                f"{name} is ledgered as doc-declared, but application.yml no longer reads it")
        if name not in doc:
            problems.append(
                f"{name} is ledgered as doc-declared, but DEPLOYMENT.md never names it")
        if name in declared(ENV_EXAMPLE) or name in declared(ENV_PROD_EXAMPLE):
            problems.append(
                f"{name} is ledgered as doc-declared, but an env example declares it now")
    assert problems == [], (
        "\n".join(problems) + "\n-- a doc-declared row has to name the document that declares it, "
        "and it stops being an exception the moment an example carries the variable")


def test_no_env_example_declares_a_variable_nothing_reads():
    read_by = read_somewhere()
    problems = []
    for path in (ENV_EXAMPLE, ENV_PROD_EXAMPLE):
        for name in sorted(declared(path) - read_by):
            problems.append(f"{path.name} declares {name}, which no source reads")
    assert problems == [], (
        "\n".join(problems) + "\n-- a knob that turns nothing is worse than a missing one: "
        "it reads as configurable and is not")


def test_the_container_names_the_docs_commands_exec_into_exist():
    missing = sorted(doc_containers() - prod_containers())
    assert missing == [], (
        f"DEPLOYMENT.md runs commands against {missing}, which docker-compose.prod.yml "
        f"does not name -- the backup and restore instructions cannot work as written")
    assert len(doc_containers()) >= 1, "the doc no longer names a prod container at all"
