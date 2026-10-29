"""The production command feeds compose the file the guide tells the reader to fill.

`docker-compose.prod.yml` interpolates eight values -- the database triple, the Redis password,
the MinIO root pair, the CORS allow-list and the API base the browser bundle inlines -- and until
this unit every one of them was written as a bare `${VAR}`. Compose resolves a bare interpolation
to the empty string when nothing sets it, and nothing did: the production procedure copies
`.env.prod.example` to `.env.prod` and starts the stack, while compose reads `${...}` at parse
time from the process environment and the project-directory `.env` -- a file the procedure never
creates.

The `env_file: .env.prod` entries inside the ai-service and backend blocks look like they cover
this and do not. `env_file:` fills a container's environment after the project renders; the
interpolation happens before it. And the `environment:` entries that carry the interpolations
override the `env_file:` values, so on a fresh host the empty interpolation wins over a filled
secret: postgres boots on an empty password, redis runs `--requirepass ""`, minio takes an empty
root pair, the backend's allow-list is empty and its MinIO keys are blank, and the frontend's
bundle is built against an empty API base. The stack comes up; it is just open and broken in the
ways the documentation says it is not.

Two halves, one contract. Every one of the eight is now `${VAR:?message}` -- compose refuses to
render the project and prints the message, which names the file and the flag -- and every shipped
command that names the override passes `--env-file .env.prod`. What this gate measures:

* the scanner reads all three compose spellings (`${VAR}`, `${VAR:-default}`, `${VAR:?message}`)
  on a fixture, because a parser that only knew the bare form would read an empty population;
* the shipped override interpolates exactly the eight required variables, each with a message
  that names the file and the flag, and nothing is left bare or defaulted -- a production value
  with a default is a value nobody chose;
* `.env.prod.example` declares all eight on uncommented, non-empty lines: it is the file the
  Quick Start tells the reader to copy and fill;
* every documented command that names the override carries `--env-file .env.prod` -- the Quick
  Start, the Rolling Updates, the compose file's own usage header and the RUNBOOK restore
  recipes, where each command must also name the override at all, because a bare `docker compose`
  inside a production restore drives the development project;
* both ops scripts build their compose argv with the file when `COMPOSE_FILE` names the
  override, so the nightly backup and the weekly drill render the project they follow names.

The command walker is proved on lines rather than trusted: the fixture below shows it flags a
command that omits the flag and passes one that carries it, and that it reads only fenced
command lines -- the RUNBOOK's explanatory prose names `docker compose` without being one.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
DOC = ROOT / "docs" / "DEPLOYMENT.md"
RUNBOOK = ROOT / "docs" / "RUNBOOK.md"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
ENV_PROD = ROOT / ".env.prod.example"
SCRIPTS = (ROOT / "scripts" / "backup.sh", ROOT / "scripts" / "restore_drill.sh")

ENV_FILE_FLAG = "--env-file .env.prod"
OVERLAY = "docker-compose.prod.yml"

# the production values compose must not invent: each is either a credential, the database's
# identity, the one origin the browser may call, or the base that origin is inlined from
REQUIRED = {
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "MINIO_ROOT_USER",
    "MINIO_ROOT_PASSWORD",
    "APP_CORS_ORIGINS",
    "NEXT_PUBLIC_API_BASE_URL",
}

INTERP = re.compile(r"\$\{(?P<var>[A-Z][A-Z0-9_]*)(?::(?P<flag>[?-])?(?P<rest>[^}]*))?\}")
HEADING = re.compile(r"^#{1,6} ")
FENCE = "```"
ASSIGNMENT = re.compile(r"^(?P<name>[A-Z][A-Z0-9_]*)=(?P<value>.*)$", re.M)
USAGE = re.compile(r"^# Usage: (?P<command>.*)$", re.M)


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def interpolations(text: str) -> list[tuple[str, str | None, str]]:
    """(variable, flag, rest) for each `${...}`; flag is None, `-` (default) or `?` (required).

    Comment lines are read out first: a compose comment is not interpolated, and this file's
    own header explains the `${VAR:?message}` spelling in words that would otherwise census
    as a required variable named VAR.
    """
    live = "\n".join(
        line for line in text.split("\n") if not line.lstrip().startswith("#")
    )
    return [
        (match["var"], match["flag"], match["rest"] or "")
        for match in INTERP.finditer(live)
    ]


def section(text: str, heading: str) -> list[tuple[int, str]]:
    """(line number, line) between one heading and the next heading of any level.

    Headings inside a fence are shell comments (`# 1. Copy ...`), not section ends: the
    region has to survive the code block it exists to read.
    """
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line.strip() == heading]
    assert len(starts) == 1, (
        f"no exactly-one `{heading}` heading in the document (found {len(starts)}), so the "
        f"commands under it would be reconciled against an empty region")
    out: list[tuple[int, str]] = []
    inside = False
    for index in range(starts[0] + 1, len(lines)):
        line = lines[index]
        if line.strip().startswith(FENCE):
            inside = not inside
        elif not inside and HEADING.match(line):
            break
        out.append((index + 1, line))
    return out


def fenced_lines(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """The lines inside the region's ``` fences -- commands, not the prose that mentions them."""
    out: list[tuple[int, str]] = []
    inside = False
    for number, line in lines:
        if line.strip().startswith(FENCE):
            inside = not inside
            continue
        if inside:
            out.append((number, line))
    return out


def compose_commands(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """(line number, line) for every fenced line in the region that runs `docker compose`.

    Substitutions count: `docker run --volumes-from \"$(docker compose ps -q minio)\"` drives a
    compose project inside a docker command, and a restore that resolves the wrong project's
    container restores the wrong stack.
    """
    return [(number, line) for number, line in lines if "docker compose" in line]


def commands_missing_the_env_file(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """The commands that name the override without handing compose the file it interpolates."""
    return [
        (number, line) for number, line in lines
        if OVERLAY in line and ENV_FILE_FLAG not in line
    ]


def commands_missing_the_overlay(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """The commands that run against whatever project the shell's default happens to be."""
    return [(number, line) for number, line in lines if OVERLAY not in line]


def test_the_interpolation_scanner_reads_all_three_compose_spellings():
    fixture = (
        "# a comment: ${COMMENTED:?compose never interpolates this}\n"
        "services:\n"
        "  box:\n"
        "    environment:\n"
        "      A: ${BARE}\n"
        "      B: ${DEFAULTED:-http://box.example:3000}\n"
        "      C: ${REQUIRED:?fill .env.prod and pass --env-file .env.prod}\n"
    )
    assert interpolations(fixture) == [
        ("BARE", None, ""),
        ("DEFAULTED", "-", "http://box.example:3000"),
        ("REQUIRED", "?", "fill .env.prod and pass --env-file .env.prod"),
    ], (
        "the scanner no longer tells the three compose spellings apart, or it read a comment as "
        "a value: a bare `${VAR}` is the empty-string shape this gate exists to refuse, a `:-` "
        "value is a stated default, a `:?` value is a requirement whose text is the failure "
        "message, and prose is neither")


def test_the_command_walker_flags_the_missing_flag_and_reads_only_commands():
    omitted = "docker compose -f docker-compose.yml -f docker-compose.prod.yml build"
    carried = (
        "docker compose -f docker-compose.yml -f docker-compose.prod.yml "
        f"{ENV_FILE_FLAG} build"
    )
    assert commands_missing_the_env_file([(1, omitted)]) == [(1, omitted)], (
        "a production command without the flag was not flagged: the shipped scan below would "
        "pass every command by reading none of them")
    assert commands_missing_the_env_file([(1, carried)]) == [], (
        "a command that carries the flag was flagged; the shipped scan would never be green")
    region = [
        (1, "```bash"),
        (2, omitted),
        (3, FENCE),
        (4, "A bare `docker compose` on this host drives the development project."),
    ]
    assert compose_commands(fenced_lines(region)) == [(2, omitted)], (
        "the walker read a prose line as a command, or missed the fenced one: the RUNBOOK "
        "explains the rule in sentences that contain the same words")


def test_every_interpolation_in_the_override_is_a_required_value():
    found = interpolations(read(COMPOSE_PROD))

    unmarked = [(var, flag, rest) for var, flag, rest in found if flag != "?"]
    assert unmarked == [], (
        f"docker-compose.prod.yml still interpolates {unmarked} without a `:?` marker: compose "
        f"renders a bare or defaulted value as whatever the file says -- usually the empty "
        f"string -- and the `environment:` entry carrying it then overrides the filled "
        f"`env_file:` value instead of failing")

    required = {var for var, _flag, _rest in found if var in REQUIRED}
    assert required == REQUIRED, (
        f"the override marks {sorted(required)} required; the production values compose must "
        f"not invent are {sorted(REQUIRED)} -- a new one has to be in both this set and "
        f".env.prod.example, and a dropped one is a value production would render empty")

    thin = [
        var for var, flag, rest in found
        if flag == "?" and (ENV_FILE_FLAG not in rest or ".env.prod" not in rest)
    ]
    assert thin == [], (
        f"{thin} are required but their messages do not name `.env.prod` and the "
        f"`{ENV_FILE_FLAG}` flag: an operator who meets one at start-up is holding the exact "
        f"instruction that fixes it, or holding nothing")


def test_the_file_the_command_names_declares_every_required_value():
    declared = {
        match["name"]: match["value"].strip()
        for match in ASSIGNMENT.finditer(read(ENV_PROD))
    }
    missing = sorted(REQUIRED - declared.keys())
    assert missing == [], (
        f".env.prod.example does not declare {missing}, so the Quick Start's "
        f"`cp .env.prod.example .env.prod` produces a file the required `${VAR:?}` entries "
        f"still refuse")
    empty = sorted(var for var in REQUIRED if not declared[var])
    assert empty == [], (
        f".env.prod.example assigns {empty} an empty value; `${VAR:?}` treats empty as missing, "
        f"so a reader who only fills what looks blank still meets a refusal at start-up")


def test_every_documented_production_command_feeds_the_file():
    problems: list[str] = []

    quick = compose_commands(fenced_lines(section(read(DOC), "### Quick Start (Production)")))
    assert len(quick) >= 1, (
        "DEPLOYMENT.md's production Quick Start no longer holds a compose command; the flag "
        "scan below would be judging an empty set")
    problems += [f"DEPLOYMENT.md:{n} runs {line.strip()!r} without {ENV_FILE_FLAG}"
                 for n, line in commands_missing_the_env_file(quick)]

    rolling = compose_commands(fenced_lines(section(read(DOC), "### Rolling Updates")))
    assert len(rolling) >= 4, (
        f"the Rolling Updates block now holds {len(rolling)} compose commands, fewer than the "
        f"build plus three restarts the procedure is")
    problems += [f"DEPLOYMENT.md:{n} runs {line.strip()!r} without {ENV_FILE_FLAG}"
                 for n, line in commands_missing_the_env_file(rolling)]

    restore = compose_commands(fenced_lines(section(read(RUNBOOK), "## Restoring by hand")))
    assert len(restore) >= 6, (
        f"RUNBOOK.md's by-hand restore now holds {len(restore)} compose commands, fewer than "
        f"the two recipes' stops, starts, exec and container lookup")
    problems += [f"RUNBOOK.md:{n} runs {line.strip()!r} without {ENV_FILE_FLAG}"
                 for n, line in commands_missing_the_env_file(restore)]
    problems += [f"RUNBOOK.md:{n} leaves {line.strip()!r} aimed at the shell's default project"
                 for n, line in commands_missing_the_overlay(restore)]

    usage = USAGE.search(read(COMPOSE_PROD))
    assert usage, "docker-compose.prod.yml no longer carries its `# Usage:` line"
    if ENV_FILE_FLAG not in usage["command"]:
        problems.append(
            f"docker-compose.prod.yml's usage line is {usage['command'].strip()!r}, which a "
            f"reader copies verbatim and which cannot render the file's own requirements")

    assert problems == [], (
        "\n".join(problems)
        + "\n-- a production command that does not hand compose the file renders every required "
          "value empty before the stack starts, and an empty interpolation overrides the "
          "`env_file:` secrets it was meant to stand beside")


def script_invocations(source: str) -> list[str]:
    """The lines of a script that run compose, its own header comments excluded."""
    return [
        line for line in source.split("\n")
        if "docker compose" in line and not line.lstrip().startswith("#")
    ]


def test_each_ops_script_hands_compose_the_file_when_the_override_is_named():
    for script in SCRIPTS:
        source = read(script)
        assert "COMPOSE=(docker compose)" in source, (
            f"{script.name} no longer builds its compose argv in one place, so there is no "
            f"guarantee every call follows the same flags")
        assert "*docker-compose.prod.yml*) COMPOSE+=(--env-file .env.prod) ;;" in source, (
            f"{script.name} does not hand compose `.env.prod` when COMPOSE_FILE names the "
            f"override; the prod project cannot render without it, and this script runs at "
            f"04:10 where the failure is a page, not a sentence")
        invocations = script_invocations(source)
        assert invocations == ["COMPOSE=(docker compose)"], (
            f"{script.name} runs compose at {invocations}; the initialiser is the only "
            f"allowed call, because a direct one skips the flags the array adds")
        assert '"${COMPOSE[@]}" ps -q postgres' in source, (
            f"{script.name} must resolve the postgres container through the array so the prod "
            f"project renders")
