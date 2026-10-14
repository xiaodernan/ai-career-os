"""Every number the rate limiter advertises is written in several files, and nothing read them together.

`RateLimitFilter` counts requests against `app.ratelimit.auth-per-minute` and
`app.ratelimit.ai-per-minute`. Those two integers are restated -- never derived -- in the Java property
class, both env examples, the filter's own javadoc, `docs/SECURITY.md`, `e2e/README.md` three times, a
comment and a message in the e2e fixtures, and as the loop bounds of `RateLimitIT`, which sends exactly
the shipped ceiling and then expects a 429. Seventeen statements of two facts. The number a deployment
gets is the one `application.yml` interpolates, so that is the authority here and every other statement is
a claim about it: raise the auth ceiling and leave SECURITY.md at 10/min and the document now describes a
product that is not running, while `RateLimitIT` goes red for a reason its own name contradicts.

The same shape repeats twice more, which is why this is one gate and not three:

* the **window** -- `Duration.ofMinutes(1)` in the filter, `Retry-After: 60` in the 429 it sends, and the
  `-per-minute` spelling of both property names and both `AppProperties` fields. The header is a promise
  to a client about a duration computed elsewhere.
* the **raised ceiling the e2e suite needs** -- 100, in the README's run command, restated as a
  requirement, quoted in a sample `e2e-override.yml`, printed by the fixture when the suite stalls, and
  both demanded and warned about by `e2e/preflight.ps1`. Six authors of an operational number that has to
  stay above the shipped default, or a compliant operator fails a check that contradicts their instructions.

Two of the numbers in the shipped text are not defaults: SECURITY.md's `RATELIMIT_AUTH_PER_MINUTE=3` is a
measurement narrative and the 100s are an override. A census that read every `NAME=<digits>` in prose would
be red at HEAD about sentences that are true, so admission is by SHAPE -- which spelling in which file
claims the shipped default -- and the excluded sites are kept as a ledger with a reason, because an
exemption nobody can point at is indistinguishable from a reader that missed them silently.

Two more pairings are censused because a number alone cannot show them: the **bucket predicate** is written
twice in one method pair (`ruleFor` and the `ai` boolean), and the identity that keys the bucket is chosen
by that same boolean -- the documented "per user" rule is really `userOrIp`, which answers with the client
IP for an anonymous caller. And the **429** is authored three ways -- the filter's `setStatus(429)`,
`ApiErrorCode.RATE_LIMITED(HttpStatus.TOO_MANY_REQUESTS)`, and six prose and client claims -- so the status
an operator reads about is reconciled against the literal the server writes.

The open scan walks the **whole repository** (608 admitted files at this ref, 24 claim rows), not a list of
directories someone remembered, because a ceiling written in an unlisted file is the defect class. Two
refusals make that honest and both are proved rather than stated: directories are pruned while descending
(`node_modules`, generated trees, and the dot-directories that hold tool state and another agent's scratch
-- `.scratch/ratelimit-3.yml` restates a ceiling no deployment ships), and this file is excluded by name
because it quotes every number it reconciles, both in prose and in the fixture strings that prove the
readers. The exclusion costs something: eight rows in this file would arrive unexplained, so the count is
asserted, and the widened walk is checked against the narrower population it replaced so a pruning rule
cannot silently swallow `docs` or either env example.

The unit matters as much as the integer: `500ms` is a duration with a unit attached, and the Redis pair is
censused with the same extractors because SECURITY.md ties them to the fail-open promise -- "with the
defaults in effect a Redis outage left every endpoint unable to answer within 40s". One case asks whether an
`int`-typed reader would even have survived that value.
"""

import os
import re
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

YML = ROOT / "backend" / "src" / "main" / "resources" / "application.yml"
PROPS = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "config" / "AppProperties.java"
FILTER = (
    ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "ratelimit" / "RateLimitFilter.java"
)
ENUM = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "common" / "ApiErrorCode.java"
IT = ROOT / "backend" / "src" / "test" / "java" / "com" / "careeros" / "RateLimitIT.java"
ENV_DEV = ROOT / ".env.example"
ENV_PROD = ROOT / ".env.prod.example"
SEC = ROOT / "docs" / "SECURITY.md"
API_DOC = ROOT / "docs" / "API.md"
E2E_README = ROOT / "e2e" / "README.md"
PREFLIGHT = ROOT / "e2e" / "preflight.ps1"
FIXTURES = ROOT / "e2e" / "tests" / "fixtures.ts"
COMPOSE = ROOT / "docker-compose.yml"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
UPSTREAM_429 = ROOT / "ai-service" / "app" / "providers" / "llm" / "openai_compat.py"

# every file the census reads a number out of, in one list: the walk has to admit all of them (asserted)
# and none of them may be excusable as local state (also asserted).
CARRIERS = (YML, PROPS, FILTER, ENUM, IT, ENV_DEV, ENV_PROD, SEC, API_DOC, E2E_README, PREFLIGHT,
            FIXTURES, COMPOSE, COMPOSE_PROD, UPSTREAM_429)

# The open scan walks the repository, not a remembered list of directories: a limiter number written in
# a file nobody enumerated is exactly the defect. `walk()` prunes while descending -- see its docstring --
# and excludes this file by name, which `test_every_limiter_claim...` proves is load-bearing.
SCAN_POPULATION = (ROOT,)
# `.env.example` has suffix `.example`, not a code suffix: a file a population names and a walker refuses
# is a carrier the census would silently never read.
SCAN_SUFFIXES = {".md", ".yml", ".yaml", ".ts", ".tsx", ".ps1", ".sh", ".py", ".java", ".example"}
SKIP_DIRS = {"node_modules", ".next", "target", "dist", "__pycache__", ".venv",
             "playwright-report", "test-results", "evals"}
# The population this scan walked before it was widened. Kept as an assertion, not a comment: a pruning
# rule that quietly swallows `docs`, `e2e` or either env example has to be caught by the census itself.
BASELINE_POPULATION = (ROOT / "README.md", ROOT / "docs", ROOT / "e2e", ROOT / "scripts",
                       ENV_DEV, ENV_PROD, COMPOSE, COMPOSE_PROD, ROOT / "backend" / "src" / "main")
CENSUS = Path(__file__).resolve()
# Leading-dot files the suffix list refuses. `.env` is the operator's untracked local override and really
# does name a ceiling in a live checkout; it is not shipped text, so a census that read it would make a
# green say nothing about what deploys -- and print a local config into a test report.
LOCAL_DOTFILES = {".env"}

AUTH_VAR, AI_VAR = "RATELIMIT_AUTH_PER_MINUTE", "RATELIMIT_AI_PER_MINUTE"
REDIS_TIMEOUT, REDIS_CONNECT = "REDIS_TIMEOUT", "REDIS_CONNECT_TIMEOUT"
CEILING_VARS = (AUTH_VAR, AI_VAR)
AUTH_PREFIX = "/api/v1/auth"
VAR_OF_PROP = {"auth": AUTH_VAR, "ai": AI_VAR}
VAR_OF_IDENTITY = {"client IP": AUTH_VAR, "user": AI_VAR}

# floors read off `git archive HEAD` at the ref this gate landed on, so a census cannot narrow itself:
# seventeen ceiling claims (eleven about auth, six about AI), eight timeout claims, six raised-ceiling
# sites, seven 429 claims, twenty-four shape-matched rows in the open scan, eight rows this census's own
# file would contribute, and at least this many files walked per shipped source tree (215/195/173/11/8/2).
MIN_CEILING_CARRIERS = 17
MIN_AUTH_CARRIERS = 11
MIN_AI_CARRIERS = 6
MIN_TIMEOUT_CARRIERS = 8
MIN_RAISED_SITES = 6
MIN_STATUS_SITES = 7
MIN_CLAIM_ROWS = 24
MIN_CENSUS_ROWS = 8
MIN_FILES_BY_DIR = {"backend": 170, "ai-service": 150, "frontend": 140, "docs": 9, "e2e": 6,
                    "scripts": 2}

INTERP = re.compile(r"\$\{(?P<var>[A-Z][A-Z0-9_]*)(?::(?P<dash>-)?(?P<default>[^}]*))?\}")
JAVA_INT = re.compile(r"private\s+int\s+(?P<field>\w+)\s*=\s*(?P<value>\d+)\s*;")
# the prose shapes that claim the SHIPPED default. `<VAR>=<digits>` is deliberately absent from the
# per-minute readers: that spelling belongs to env examples, to a measurement and to an operator's override.
PROSE_PER_MIN = re.compile(r"(?P<value>\d+)/min\b")
EMPTY_MEANS = re.compile(r"empty means (?P<value>\d+)\)")
DOC_IDENTITY = re.compile(r"(?P<value>\d+)/min per (?P<identity>client IP|user)\b")
JAVADOC_DEFAULT = re.compile(
    r"app\.ratelimit\.(?P<prop>auth|ai)-per-minute \(default (?P<value>\d+)/min\)")
AUTH_LIMIT_DEFAULT = re.compile(r'E2E_AUTH_LIMIT \?\? "(?P<value>\d+)"')
E2E_THRESHOLD = re.compile(r"\[int\]\$rl -ge (?P<value>\d+)")
RAISED_ASSIGN = re.compile(rf"{AUTH_VAR}[=:]\s*\\?\"?(?P<value>\d+)")
ANY_ASSIGN = re.compile(rf"(?P<var>{AUTH_VAR}|{AI_VAR})[=:]\s*\\?\"?(?P<value>\d+)")
# `ANY_ASSIGN` reads the name bare, which is how a `.env`, a compose file and a Java literal all spell
# it. A JSON document quotes the key instead, so the same figure in a notes file would slip past the
# refusal witness; this spelling is deliberately not in `ANY_ASSIGN`, because widening the census shape
# would re-classify rows in the scanned trees, and no shipped scanned format quotes a limiter key.
QUOTED_ASSIGN = re.compile(rf"\"(?P<var>{AUTH_VAR}|{AI_VAR})\"\s*:\s*\"?(?P<value>\d+)")
IT_BOUND = re.compile(r"for \(int i = 1; i <= (?P<value>\d+); i\+\+\)")
WINDOW = re.compile(r"Duration\.of(?P<unit>Seconds|Minutes|Hours)\((?P<value>\d+)\)")
RETRY_AFTER = re.compile(r'setHeader\("Retry-After", "(?P<value>\d+)"\)')
STATUS_SETTER = re.compile(r"setStatus\((?P<value>\d+)\)")
HTTP_429 = re.compile(r"\b429\b")
CODE_NAME = re.compile(r"\bRATE_LIMITED\b")
ENUM_DECL = re.compile(r"RATE_LIMITED\(HttpStatus\.(?P<name>[A-Z_]+)\)")
PER_MINUTE_NAME = re.compile(r"\b(?:auth|ai)[-_][pP]er[-_][mM]inute\b|\b(?:auth|ai)PerMinute\b")
# Directional on purpose: the AI branch must be the user id and the auth branch the client IP. A test
# that only asked whether both names appear in the line is true with the two branches swapped.
AI_THEN_IP = re.compile(r"ai\s*\?\s*userOrIp\(request\)\s*:\s*clientIp\(request\)")
MS = re.compile(r"(?P<value>\d+)ms\b")
UNIT_SECONDS = {"Seconds": 1, "Minutes": 60, "Hours": 3600}

# the shapes the open scan looks for, in the order an overlapping line is decided: `identity` is the
# SECURITY.md spelling of a `N/min` claim, so a line it matches is not also counted as a bare per-minute.
CLAIM_SHAPES = [
    ("assignment", ANY_ASSIGN),
    ("identity", DOC_IDENTITY),
    ("per-minute", PROSE_PER_MIN),
    ("empty-means", EMPTY_MEANS),
    ("fixture-default", AUTH_LIMIT_DEFAULT),
    ("threshold", E2E_THRESHOLD),
]

# Lines that state a limiter number which is NOT the shipped default, and why the census lets them stand.
# Every entry has to actually excuse a row (asserted), or it is a hiding place rather than a reason.
EXCUSED_NUMBERS = [
    {
        "site": "SECURITY.md's X-Forwarded-For measurement",
        "pattern": re.compile(r"Measured against the running stack with"),
        "reason": (
            "an experiment, not a configuration: the reviewer lowered the auth ceiling to 3 so the 429 "
            "would reproduce in five requests. Nothing deploys this figure, and the sentence says so in "
            "the same clause"),
    },
]


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _lines(text: str) -> list[str]:
    return text.split("\n")


def interpolation_default(text: str, var: str, carrier: str) -> str | None:
    """The value `${VAR:x}` (Spring) or `${VAR:-x}` (compose) carries; None when it states none."""
    for match in INTERP.finditer(text):
        if match["var"] != var:
            continue
        if match["default"] is None:
            return None
        assert not match["default"].startswith("-"), (
            f"{carrier}: {var} uses compose's `:-` and the dash survived into the default "
            f"{match['default']!r}")
        return match["default"]
    raise AssertionError(f"{carrier} no longer interpolates {var}")


def env_assignment(path: Path, var: str) -> str:
    """The value an env example writes for `var` -- commented lines are advice, not values."""
    for line in _lines(read(path)):
        if line.startswith(f"{var}="):
            return line.split("=", 1)[1].strip()
    raise AssertionError(f"{path.name} no longer assigns {var} on an uncommented line")


def java_int_default(path: Path, field: str) -> int:
    """The initialiser of one named `private int` field, not of whichever field comes first.

    `AppProperties` holds five integer defaults, starting with `accessTtlMinutes = 15`, so a reader that
    took the first match would reconcile a rate limit against a token lifetime.
    """
    text = read(path)
    matches = [m for m in JAVA_INT.finditer(text) if m["field"] == field]
    assert len(matches) == 1, (
        f"{path.name}: {len(matches)} `private int {field} = n;` initialisers, want exactly 1. The "
        f"Java default is a shadow -- Spring binds the yml key -- and two of them would disagree with "
        f"each other before they disagreed with the authority")
    return int(matches[0]["value"])


def first_group(path: Path, pattern: re.Pattern, want: int = 1) -> list[re.Match]:
    """Matches of `pattern` in one file, censused: a wrong count is a claim that changed."""
    text = read(path)
    hits = list(pattern.finditer(text))
    assert len(hits) == want, (
        f"{path.relative_to(ROOT)} has {len(hits)} matches of {pattern.pattern!r} at lines "
        f"{[_line_of(text, h.start()) for h in hits]}, want {want}: {[h.group(0) for h in hits][:4]}")
    return hits


def fixture_value(pattern: re.Pattern, text: str, site: str) -> str:
    """The value one fixture string carries, refused by name when the reader finds no shape.

    These are the census's own proofs: each pattern is exercised against a spelling no shipped file uses.
    Indexing `search()` directly would make a moved shape a `TypeError`, which names neither the reader nor
    the fixture, so the absence is stated the way the shipped reads state it.
    """
    match = pattern.search(text)
    assert match is not None, (
        f"the {site} fixture no longer matches {pattern.pattern!r}: that string is this reader's only "
        f"proof, and no shipped file writes the shape it stands for")
    return match["value"]


def walk(*roots: Path) -> list[tuple[Path, str]]:
    """Every admitted text file under `roots`, with directories pruned while descending.

    The prune happens in `os.walk`, not as a filter after an `rglob`: a live checkout has `node_modules`
    and `.venv` under these roots, and enumerating them before refusing them costs minutes and reads
    thousands of files the census cannot classify. Dot-directories go the same way -- they hold tool
    state and other agents' scratch, and `.scratch/ratelimit-3.yml` in a developer's directory restates
    a ceiling no deployment ships. `test_every_limiter_claim_in_the_repository_is_classified` proves the
    refusal costs nothing the census claims to read, by re-walking the narrower population this scan used
    and requiring it to come out a subset.
    """
    out: list[tuple[Path, str]] = []
    for root in roots:
        if root.is_file():
            if root.suffix in SCAN_SUFFIXES and root != CENSUS:
                out.append((root, read(root)))
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames
                                 if d not in SKIP_DIRS and not d.startswith("."))
            for name in sorted(filenames):
                path = Path(dirpath) / name
                if path.suffix in SCAN_SUFFIXES and path != CENSUS:
                    out.append((path, read(path)))
    return out


def refused_claims() -> list[tuple[str, str]]:
    """Files the walk does not read -- wrong suffix -- that nonetheless state a limiter claim.

    Dot-directories are already pruned by the same rule the walk uses, so what surfaces here is a shipped
    tree hiding behind a suffix: the answer at this ref is one file, `.env`, named in LOCAL_DOTFILES.
    """
    out: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.suffix in SCAN_SUFFIXES or path == CENSUS:
                continue
            text = read(path)
            hit = (ANY_ASSIGN.search(text) or QUOTED_ASSIGN.search(text)
                   or PROSE_PER_MIN.search(text)
                   or DOC_IDENTITY.search(text) or E2E_THRESHOLD.search(text))
            if hit:
                out.append((str(path.relative_to(ROOT)), hit.group(0)))
    return out


def authority() -> dict[str, int]:
    """The two integers Spring binds when the deployment sets nothing -- the deciding carriers."""
    out: dict[str, int] = {}
    for var in CEILING_VARS:
        value = interpolation_default(read(YML), var, "application.yml")
        assert value and value.isdigit(), (
            f"application.yml's {var} default is {value!r}: it is the authority this whole file "
            f"derives, so an empty or non-numeric reading means every carrier below is reconciled "
            f"against a stub")
        out[var] = int(value)
    return out


def ceiling_carriers() -> list[tuple[str, str, int]]:
    """(what states it, which knob, what number) for every shipped claim about the two ceilings.

    SECURITY.md is read once, by the identity-shape reader, because its two `N/min` lines are the same
    two lines `PROSE_PER_MIN` would find -- a census that counted one file twice would report agreement
    between a document and itself.
    """
    out: list[tuple[str, str, int]] = [
        ("AppProperties' `authPerMinute` initialiser", AUTH_VAR, java_int_default(PROPS, "authPerMinute")),
        ("AppProperties' `aiPerMinute` initialiser", AI_VAR, java_int_default(PROPS, "aiPerMinute")),
    ]
    for path, label in ((ENV_DEV, ".env.example"), (ENV_PROD, ".env.prod.example")):
        for var in CEILING_VARS:
            value = env_assignment(path, var)
            assert value.isdigit(), f"{label}'s {var} states {value!r}, which is not a plain integer"
            out.append((f"{label}'s {var}", var, int(value)))
    for match in first_group(FILTER, JAVADOC_DEFAULT, want=2):
        out.append((f"RateLimitFilter's javadoc {match['prop']}-per-minute line",
                    VAR_OF_PROP[match["prop"]], int(match["value"])))
    sec_text = read(SEC)
    identities: dict[str, str] = {}
    for match in first_group(SEC, DOC_IDENTITY, want=2):
        var = VAR_OF_IDENTITY[match["identity"]]
        identities[match["identity"]] = var
        out.append((f"SECURITY.md:{_line_of(sec_text, match.start())} `{match['value']}/min per "
                    f"{match['identity']}`", var, int(match["value"])))
    assert sorted(identities) == ["client IP", "user"], (
        "SECURITY.md names the bucketed identities "
        f"{sorted(identities)}; the two ceilings are only reconcilable while the document still says "
        f"which one is per client IP and which is per user")
    for path, want in ((E2E_README, 2), (FIXTURES, 1)):
        text = read(path)
        for match in first_group(path, PROSE_PER_MIN, want=want):
            out.append((f"{path.relative_to(ROOT)}:{_line_of(text, match.start())} `{match.group(0)}`",
                        AUTH_VAR, int(match["value"])))
    match = first_group(E2E_README, EMPTY_MEANS, want=1)[0]
    out.append((f"e2e/README.md:{_line_of(read(E2E_README), match.start())} `(empty means ...)`",
                AUTH_VAR, int(match["value"])))
    match = first_group(FIXTURES, AUTH_LIMIT_DEFAULT, want=1)[0]
    out.append((f"e2e/tests/fixtures.ts:{_line_of(read(FIXTURES), match.start())} "
                f"`E2E_AUTH_LIMIT` fallback", AUTH_VAR, int(match["value"])))
    # RateLimitIT sends exactly the shipped ceiling and then expects to be limited, so its loop bounds
    # are claims about both numbers -- and they are ordered auth-then-ai by the two test methods.
    bounds = first_group(IT, IT_BOUND, want=2)
    for match, var in zip(bounds, (AUTH_VAR, AI_VAR), strict=True):
        out.append((f"RateLimitIT:{_line_of(read(IT), match.start())} `i <= "
                    f"{match['value']}` warm-up loop", var, int(match["value"])))
    return out


def timeout_carriers() -> list[tuple[str, str, str]]:
    """(where, which knob, what duration) for the Redis client timeouts the fail-open promise rests on."""
    out: list[tuple[str, str, str]] = []
    for path, label in ((ENV_DEV, ".env.example"), (ENV_PROD, ".env.prod.example")):
        for var in (REDIS_TIMEOUT, REDIS_CONNECT):
            out.append((f"{label}'s {var}", var, env_assignment(path, var)))
    for var in (REDIS_TIMEOUT, REDIS_CONNECT):
        out.append((f"application.yml's {var} default", var,
                    interpolation_default(read(YML), var, "application.yml")))
    sec_text = read(SEC)
    for match in first_group(SEC, MS, want=2):
        out.append((f"SECURITY.md:{_line_of(sec_text, match.start())} `{match.group(0)}`",
                    "stated in prose", f"{match['value']}ms"))
    return out


def ms_figures(path: Path, want: int) -> list[str]:
    """Every millisecond figure a file states, including the ones inside its own comments."""
    return [f"{m['value']}ms" for m in first_group(path, MS, want=want)]


def window() -> tuple[str, int, int]:
    """(unit, count, seconds) from the one `Duration.of*` the filter hands the limiter."""
    text = read(FILTER)
    hits = list(WINDOW.finditer(text))
    assert len(hits) == 1, (
        f"RateLimitFilter has {len(hits)} `Duration.of*` literals {[h.group(0) for h in hits]} at "
        f"lines {[_line_of(text, h.start()) for h in hits]}, want exactly 1: the window is the divisor "
        f"of both ceilings, so a second one means two windows")
    unit, count = hits[0]["unit"], int(hits[0]["value"])
    return unit, count, count * UNIT_SECONDS[unit]


def retry_after_seconds() -> int:
    """The `Retry-After` the filter sends with its 429 -- a duration promised to every client."""
    return int(first_group(FILTER, RETRY_AFTER, want=1)[0]["value"])


def raised_sites() -> list[tuple[str, int]]:
    """Every site that writes the number an e2e run must raise the auth ceiling to."""
    out: list[tuple[str, int]] = []
    for path in (E2E_README, FIXTURES, PREFLIGHT):
        text = read(path)
        for match in first_group(path, RAISED_ASSIGN,
                                 want={str(E2E_README): 3, str(FIXTURES): 1, str(PREFLIGHT): 1}[str(path)]):
            out.append((f"{path.relative_to(ROOT)}:{_line_of(text, match.start())}", int(match["value"])))
    match = first_group(PREFLIGHT, E2E_THRESHOLD, want=1)[0]
    out.append((f"e2e/preflight.ps1:{_line_of(read(PREFLIGHT), match.start())} `-ge` threshold",
                int(match["value"])))
    return out


def status_sites() -> list[tuple[str, int, str]]:
    """(where, which status, in what words) for every shipped claim about the over-limit answer.

    The authority is `setStatus(...)` in the filter: it is the only place the number is written into a
    response. The enum spells the same answer as `HttpStatus.TOO_MANY_REQUESTS` and is reconciled by
    name, not by number, because no file in this repository states that mapping.
    """
    out: list[tuple[str, int, str]] = []
    setter = first_group(FILTER, STATUS_SETTER, want=1)[0]
    setter_line = _line_of(read(FILTER), setter.start())
    out.append((f"RateLimitFilter:{setter_line} `setStatus(...)`",
                int(setter["value"]), "the server writes this status"))
    for path in (FILTER, API_DOC, SEC, E2E_README, FIXTURES):
        text = read(path)
        want = {str(FILTER): 2, str(API_DOC): 1, str(SEC): 1, str(E2E_README): 1,
                str(FIXTURES): 2}[str(path)]
        for match in first_group(path, HTTP_429, want=want):
            number = _line_of(text, match.start())
            if path == FILTER and number == setter_line:
                # that occurrence IS the authority above; crediting it twice would be the census
                # agreeing with itself, which is the thing this file refuses to report as agreement.
                continue
            line = _lines(text)[number - 1].strip()
            out.append((f"{path.relative_to(ROOT)}:{number}", int(match.group(0)), line[:60]))
    return out


def code_name_sites() -> list[tuple[str, int]]:
    """Every file that spells the envelope code an over-limit request carries."""
    out = []
    for path, want in ((FILTER, 2), (ENUM, 1), (IT, 2)):
        text = read(path)
        for match in first_group(path, CODE_NAME, want=want):
            out.append((f"{path.relative_to(ROOT)}:{_line_of(text, match.start())}", 1))
    return out


def claim_rows() -> list[tuple[str, int, str, int]]:
    """(file, line, shape, value) for every limiter claim the walked text makes -- the open half.

    One line is counted once per shape it matches, except a line `DOC_IDENTITY` reads: that is a `N/min`
    claim already, so crediting both shapes would let SECURITY.md agree with itself twice.
    """
    rows: list[tuple[str, int, str, int]] = []
    for path, text in walk(*SCAN_POPULATION):
        per_line: dict[int, dict[str, int]] = {}
        for name, pattern in CLAIM_SHAPES:
            for match in pattern.finditer(text):
                number = _line_of(text, match.start())
                per_line.setdefault(number, {})[name] = int(match["value"])
        for number, found in sorted(per_line.items()):
            if "identity" in found:
                found.pop("per-minute", None)
            for name, value in sorted(found.items()):
                rows.append((str(path.relative_to(ROOT)), number, name, value))
    return rows


# -- cases --------------------------------------------------------------------
def test_the_number_readers_parse_shapes_this_repository_does_not_yet_hold():
    """Proves the extractors on inputs the shipped files do not contain.

    Every one of these readers is currently exercised only against values that happen to be short and
    correctly spelled. A reader that is right by accident fails the first time an operator types
    `RATELIMIT_AUTH_PER_MINUTE=1000` or writes a compose-style `:-` default, and the census then
    reconciles a stub without noticing.
    """
    assert interpolation_default("    auth-per-minute: ${RATELIMIT_AUTH_PER_MINUTE:1000}",
                                 AUTH_VAR, "spring fixture") == "1000", (
        "a four-digit ceiling read back wrong: the census would compare every carrier against a "
        "truncated authority")
    assert interpolation_default("      RATELIMIT_AUTH_PER_MINUTE: ${RATELIMIT_AUTH_PER_MINUTE:-25}",
                                 AUTH_VAR, "compose fixture") == "25", (
        "compose's `:-` and Spring's `:` are one character apart and this repository currently "
        "interpolates only the Spring spelling")
    assert interpolation_default("      RATELIMIT_AUTH_PER_MINUTE: ${RATELIMIT_AUTH_PER_MINUTE}",
                                 AUTH_VAR, "bare fixture") is None, (
        "a variable with no default states nothing, which is not the same as an empty default")
    assert interpolation_default("      RATELIMIT_AUTH_PER_MINUTE: ${RATELIMIT_AUTH_PER_MINUTE:-}",
                                 AUTH_VAR, "empty fixture") == "", (
        "an explicit empty default is a value the deployment chose, not an absent one")

    hit = JAVADOC_DEFAULT.search(
        "*  - /api/v1/auth/** : per client IP, app.ratelimit.auth-per-minute (default 5/min)")
    assert hit and hit["prop"] == "auth" and hit["value"] == "5", (
        f"the javadoc reader must find a ceiling it has never seen "
        f"({hit.group(0) if hit else None!r})")
    prose = "the limit is 12/min per client IP, and (empty means 12)"
    assert [m["value"] for m in DOC_IDENTITY.finditer(prose)] == ["12"], (
        "the doc reader is keyed on `N/min per <identity>`; a re-wrapped bullet is still a claim")
    assert fixture_value(EMPTY_MEANS, prose, "`(empty means N)`") == "12", (
        "the `(empty means N)` shape is a default claim")
    assert fixture_value(RAISED_ASSIGN, f"{AUTH_VAR}=1000", "raised-ceiling") == "1000", (
        "a raised ceiling with four digits is still the raised ceiling")
    assert fixture_value(AUTH_LIMIT_DEFAULT, '`${process.env.E2E_AUTH_LIMIT ?? "12"}/min per IP.',
                         "`E2E_AUTH_LIMIT` fallback") == "12", (
        "the fixture's fallback is a claim about the default, and it can be re-typed")
    assert fixture_value(IT_BOUND, "for (int i = 1; i <= 7; i++) {", "warm-up bound") == "7", (
        "the integration test's warm-up bound is a number the limiter depends on")

    # the trap this reader exists for: AppProperties' first `private int` is not a limiter field.
    first = JAVA_INT.search(read(PROPS))
    assert first is not None, (
        f"AppProperties no longer holds a `{JAVA_INT.pattern!r}` initialiser, so the named-field "
        f"reader's trap -- that the file's first integer default is a token lifetime, not a ceiling -- "
        f"cannot be shown against it")
    assert first["field"] != "authPerMinute", (
        f"AppProperties' first integer default is now `{first['field']} = {first['value']}`; the "
        f"named-field reader was proved against a file whose first match was a token lifetime, so if "
        f"that stops being true this census has to be re-read rather than trusted")
    assert java_int_default(PROPS, "authPerMinute") != int(first["value"]), (
        "a reader that took the first `private int` would reconcile a rate limit against whichever "
        "field happens to come first")


def test_the_two_ceilings_have_one_authority_and_every_other_statement_agrees():
    """The yml default decides; the rest restate it, and a restatement that drifts is a bug report.

    Read the other way this census would be a tautology: comparing each carrier with the value the same
    file just returned proves nothing, so the authority comes from `application.yml` alone and each
    carrier is parsed by an extractor written for the shape it is written in.
    """
    caps = authority()
    carriers = ceiling_carriers()
    assert len(carriers) >= MIN_CEILING_CARRIERS, (
        f"the ceiling census read {len(carriers)} carriers, below the {MIN_CEILING_CARRIERS} the "
        f"shipped files state: a census that reads nothing reconciles a stub")
    per_var = {var: sum(1 for _l, v, _n in carriers if v == var) for var in CEILING_VARS}
    assert per_var[AUTH_VAR] >= MIN_AUTH_CARRIERS and per_var[AI_VAR] >= MIN_AI_CARRIERS, (
        f"the ceiling census splits {per_var} between the two knobs, wanting at least "
        f"{MIN_AUTH_CARRIERS} auth and {MIN_AI_CARRIERS} ai claims: one ceiling covered by a single "
        f"stray match is a census that can pass on a coincidence")
    problems = [
        f"{label} states {value}, the shipped default for {var} is {caps[var]}"
        for label, var, value in carriers
        if value != caps[var]
    ]
    assert not problems, (
        f"the rate limit is decided in more than one file and they disagree -- {'; '.join(problems)} "
        f"-- the authority is application.yml's `${{RATELIMIT_AUTH_PER_MINUTE}}` / "
        f"`${{RATELIMIT_AI_PER_MINUTE}}` default, because that file always defines `app.ratelimit.*` "
        f"and therefore decides what Spring binds; a reader who follows the stale statement sets a "
        f"ceiling they did not choose, and `RateLimitIT` fails for a reason its own method name "
        f"contradicts")


def test_the_java_default_is_a_shadow_and_still_says_what_spring_would_bind():
    """`AppProperties` initialises the same two integers, and every reader assumes it is the default.

    It is not: `application.yml` defines `app.ratelimit.auth-per-minute` and `ai-per-minute`, so Spring
    binds the yml and the field initialiser only answers when the key is absent. A shadow whose edits
    change nothing is still a statement a developer reads, which is why it is reconciled rather than
    deleted -- and why the census above refuses to let it be the authority.
    """
    caps = authority()
    keys = re.findall(r"^    (auth-per-minute|ai-per-minute): \$\{([A-Z_]+):", read(YML), re.M)
    assert sorted(keys) == [("ai-per-minute", AI_VAR), ("auth-per-minute", AUTH_VAR)], (
        f"application.yml interpolates the ratelimit keys {keys}; without both, the yml stops being the "
        f"authority and this file is comparing two claims to nothing")
    assert "app.ratelimit" not in read(YML), (
        "application.yml spells the two ceilings as nested keys under `ratelimit:`; if the dotted "
        "path ever appears here, the javadoc's `app.ratelimit.*` names are no longer a description of "
        "a different spelling but the same text, and a reader grepping the yml for them gets a "
        "different answer than Spring binds")
    assert "app.ratelimit" in read(FILTER), (
        "RateLimitFilter's javadoc no longer names the property path the yml implements, so the "
        "operator-facing name for the ceilings has moved and the census above reads a file nobody "
        "documents")

    for field, var in (("authPerMinute", AUTH_VAR), ("aiPerMinute", AI_VAR)):
        shadow = java_int_default(PROPS, field)
        assert shadow == caps[var], (
            f"AppProperties' {field} initialiser is {shadow} while Spring would bind {caps[var]}: a "
            f"reader copying the Java file, or running the bean without the yml, gets a different "
            f"product -- and the javadoc, the env examples and SECURITY.md all describe the yml")


def test_the_window_the_limiter_counts_and_the_header_it_sends_are_one_duration():
    """`Duration.ofMinutes(1)`, `Retry-After: 60` and the `-per-minute` names are one clock.

    The header is the only thing a client has to go on: a window that changed without it would tell a
    caller to come back in a minute while the limiter let it through in half a minute, or -- the worse
    direction -- keep it waiting twice as long as it is actually blocked.
    """
    unit, count, seconds = window()
    retry = retry_after_seconds()
    assert retry == seconds, (
        f"RateLimitFilter counts a {unit.lower()} window of {count} ({seconds}s) but answers "
        f"`Retry-After: {retry}`: the header is a promise to every client about a duration the limiter "
        f"computes elsewhere, and nothing else in the response says how long to wait")
    names = PER_MINUTE_NAME.findall(read(YML) + read(PROPS))
    assert len(names) >= 4, (
        f"only {len(names)} `-per-minute`/`PerMinute` spellings are left in application.yml and "
        f"AppProperties: the ceilings are named for their window, so if the window is no longer a "
        f"minute the names lie about the unit")
    assert unit == "Minutes", (
        f"the limiter counts {unit}({count}) while both knobs are named `auth-per-minute` and "
        f"`ai-per-minute` and every document says `/min` -- either rename the properties and the "
        f"prose, or count minutes")


def test_the_bucket_a_request_lands_in_is_chosen_by_the_predicate_that_names_it():
    """`doFilterInternal` and `ruleFor` decide auth-vs-AI from the same prefix, twice.

    Two authors of one predicate is the drift: `ruleFor` admits a path, `doFilterInternal` then picks
    the limit and the identity by its own test, and if only one of them changes the AI ceiling is applied
    to an auth bucket (or the reverse) while every rule name still reads correct.
    """
    text = read(FILTER)
    lines = _lines(text)
    prefix_test = f'startsWith("{AUTH_PREFIX}"'
    hits = first_group(FILTER, re.compile(re.escape(prefix_test)), want=2)
    authors = sorted(lines[_line_of(text, h.start()) - 1].strip() for h in hits)
    assert authors == [f'boolean ai = !uri.{prefix_test});',
                       f'if (uri.{prefix_test})) {{'], (
        f"the auth prefix is tested on {authors}: the two authors have to stay the admitting rule "
        f"(`ruleFor`) and the flag that picks the ceiling and the identity "
        f"(`doFilterInternal`); a third one, or either rewritten, means a request's bucket is decided "
        f"by something other than the rule that admits it")
    ai_line = next(line for line in lines if "boolean ai =" in line)
    assert f'!uri.startsWith("{AUTH_PREFIX}")' in ai_line, (
        f"`{ai_line.strip()}` no longer derives the AI flag as the negation of the auth prefix: the "
        f"same test appears twice in this class and only `ruleFor` is covered by RateLimitFilterTest")
    identity_line = next((line for line in lines if "String identity = ai ?" in line), None)
    assert identity_line is not None, (
        "RateLimitFilter no longer selects the bucket key's identity from the same `ai` flag, so the "
        "ceiling and the identity it is counted against can disagree without any name reading wrong")
    assert AI_THEN_IP.search(identity_line) is not None, (
        f"the identity is chosen by `{identity_line.strip()}`, which no longer pairs the AI flag with "
        f"the user id and the auth flag with the client IP")
    key_line = next((line for line in lines if 'String key = "ratelimit:"' in line), None)
    assert key_line is not None and "ai ?" in key_line and 'auth:' in key_line, (
        f"the Redis key prefix is now written by `{(key_line or '').strip()}`: SECURITY.md's "
        f"measurement counts `ratelimit:auth:*` keys, so the key spelling is a claim too")

    javadoc = lines[_line_of(text, first_group(FILTER, JAVADOC_DEFAULT, want=2)[1].start()) - 1]
    assert "falls back to IP" in javadoc, (
        f"the javadoc line that declares the AI ceiling is `{javadoc.strip()}`: it used to say the "
        f"per-user rule falls back to the client IP, which is what `userOrIp` actually does")
    fallback = text[text.index("private static String userOrIp"):text.index("static String clientIp")]
    assert "return clientIp(request);" in fallback, (
        "`userOrIp` no longer answers with the client IP when there is no authenticated user, so the "
        "documented fallback and the AI bucket's key have parted: an anonymous caller's budget is now "
        "shared per IP, or the request crashes before the limiter")

    doc = read(SEC)
    identities = {m["identity"] for m in DOC_IDENTITY.finditer(doc)}
    assert identities == {"client IP", "user"}, (
        f"SECURITY.md names {sorted(identities)}; the filter buckets auth by client IP and AI by user "
        f"id, so a document that drops one of them describes a limiter with one rule")
    pairs = {(m["identity"], m["value"]) for m in DOC_IDENTITY.finditer(doc)}
    caps = authority()
    assert ("client IP", str(caps[AUTH_VAR])) in pairs and ("user", str(caps[AI_VAR])) in pairs, (
        f"SECURITY.md pairs the identities with {sorted(pairs)} while the filter counts "
        f"{caps[AUTH_VAR]}/min per client IP and {caps[AI_VAR]}/min per user: swapped numbers read "
        f"correct in both directions and are wrong in both")


def test_the_raised_ceiling_the_suite_needs_is_the_number_preflight_demands():
    """100 is written six times, and an operator who obeys one of them must satisfy all of them.

    `RATELIMIT_AUTH_PER_MINUTE=100` is not cosmetic: a full e2e run registers an account per test and the
    product's own ceiling would stall it. The README's command, its "required, not cosmetic" line, the
    sample override, the failure text the fixture prints, preflight's threshold and preflight's own WARN
    advice have to be one number, or a compliant operator fails a check that contradicts their
    instructions.
    """
    sites = raised_sites()
    assert len(sites) >= MIN_RAISED_SITES, (
        f"the raised ceiling has {len(sites)} sites, below the {MIN_RAISED_SITES} the shipped e2e text "
        f"writes: a census of an absent population agrees with everything")
    values = {value for _label, value in sites}
    assert len(values) == 1, (
        f"the e2e raise is written as {sorted(values)} across {[label for label, _ in sites]}: follow "
        f"one instruction, fail another -- preflight PASSes at its own threshold and the suite still "
        f"stalls")
    raised = values.pop()
    caps = authority()
    assert raised > caps[AUTH_VAR], (
        f"the e2e text raises the auth ceiling to {raised}, which is not above the shipped default "
        f"{caps[AUTH_VAR]}: the override would be decoration and the suite would fail on its own "
        f"product's protection")


def test_the_base_compose_does_not_name_the_knob_the_e2e_override_exists_for():
    """`e2e/README.md` explains the override by claiming the base compose omits it -- so check that.

    A doc claim about an ABSENCE is the easiest claim in the repository to outlive: the day someone adds
    `RATELIMIT_AUTH_PER_MINUTE` to `docker-compose.yml`, the override file's `environment:` still wins,
    the README's paragraph becomes wrong, and the trap it warns about gets re-learned by hand.
    """
    for path in (COMPOSE, COMPOSE_PROD):
        compose = read(path)
        for var in CEILING_VARS:
            assert var not in compose, (
                f"{path.name} now names {var}, which e2e/README.md states the base compose does not "
                f"name -- either the README's override recipe is obsolete or the compose file sets a "
                f"ceiling the e2e profile then silently outranks")
    readme = read(E2E_README)
    assert f"the base compose does not name `{AUTH_VAR}`" in readme, (
        "the README no longer states the absence this case checks, so the check has lost its subject "
        "and the override file's reason for existing is unstated")


def test_the_redis_timeouts_the_fail_open_promise_rests_on_are_one_pair():
    """`500ms` is censused like the ceilings, and it is not an integer.

    SECURITY.md's fail-open bullet depends on these two values: with the previous defaults a Redis outage
    left every endpoint unable to answer within 40 seconds, which locked out exactly the users failing
    open exists to serve. A reader typed `int` would have raised on `500ms` instead of reporting a drift,
    so the duration keeps its unit all the way through.
    """
    carriers = timeout_carriers()
    assert len(carriers) >= MIN_TIMEOUT_CARRIERS, (
        f"the timeout census read {len(carriers)} carriers, below the {MIN_TIMEOUT_CARRIERS} the "
        f"shipped files state")
    by_var: dict[str, set[str]] = {}
    for _label, var, value in carriers:
        assert value, f"{_label} read an empty {var}"
        by_var.setdefault(var, set()).add(value)
    for var, values in by_var.items():
        assert len(values) == 1, (
            f"{var} is read as {sorted(values)} by the carriers of it: one knob stated two ways has no "
            f"single value to reconcile the prose against, and the pair comparison below could only "
            f"pick one of the two at random")
    knobs = {var: next(iter(values)) for var, values in by_var.items() if var != "stated in prose"}
    assert sorted(knobs) == sorted([REDIS_TIMEOUT, REDIS_CONNECT]), (
        f"the timeout census only recognises {sorted(knobs)}: both knobs have to be stated by the "
        f"env examples and application.yml or the fail-open promise has no measured subject")
    assert len({*knobs.values()}) == 1, (
        f"the two client timeouts are {knobs} while .env.example writes 'Both are "
        f"{next(iter(knobs.values()))} on purpose': the comment is a claim about the pair, so a split "
        f"between them makes one of the two statements false")
    for path, want in ((YML, 3), (ENV_DEV, 3), (ENV_PROD, 2), (SEC, 2)):
        figures = ms_figures(path, want)
        assert set(figures) == set(knobs.values()), (
            f"{path.name} states {sorted(set(figures))} while the shipped timeouts are "
            f"{sorted(set(knobs.values()))}: a figure inside a comment or a document is still a number "
            f"a reader repeats")
    prose = by_var.get("stated in prose", set())
    assert prose, (
        "SECURITY.md no longer states a millisecond figure, so the document has stopped promising the "
        "prompt fail-open branch this census exists to keep honest")
    doc = read(SEC)
    assert "Fails open" in doc and "40s" in doc, (
        "the fail-open promise itself moved: this case reconciles a duration against a claim about "
        "what that duration is for, so both have to stay in the document")
    with pytest.raises(ValueError, match="invalid literal"):
        int(knobs[REDIS_TIMEOUT])


def test_the_answer_an_over_limit_request_gets_has_one_spelling_across_the_stack():
    """The 429 and the `RATE_LIMITED` code are written three ways: the server, the enum, the prose.

    `setStatus(429)` is the number a client keys on, `ApiErrorCode.RATE_LIMITED(HttpStatus.TOO_MANY_REQUESTS)`
    is the number the envelope's owner declares, and five shipped sentences plus the e2e fixture's
    detection tell a reader what to expect. Nothing in the repository maps the enum name back to 429, so
    the literals are reconciled against each other and the enum is reconciled by name.
    """
    sites = status_sites()
    assert len(sites) >= MIN_STATUS_SITES, (
        f"the 429 census read {len(sites)} sites, below the {MIN_STATUS_SITES} that ship: the answer "
        f"an over-limit request gets would have fewer authors than the ceiling has")
    numbers = {value for _label, value, _words in sites}
    assert numbers == {429}, (
        f"the over-limit status is written as {sorted(numbers)} across "
        f"{[label for label, _v, _w in sites]}: a client that branches on 429 -- which the e2e fixture "
        f"does -- would read a rate limit as some other failure")
    names = code_name_sites()
    assert len(names) == 5, (
        f"`RATE_LIMITED` appears at {len(names)} sites {[label for label, _ in names]}, want 5 (the "
        f"filter's javadoc and its `ApiError.of`, the enum's declaration, and RateLimitIT's two "
        f"envelope assertions): the code is the machine-readable half of the answer")
    decl = first_group(ENUM, ENUM_DECL, want=1)[0]
    assert decl["name"] == "TOO_MANY_REQUESTS", (
        f"ApiErrorCode.RATE_LIMITED now declares HttpStatus.{decl['name']}, while the filter writes "
        f"setStatus(429) and every document says 429: no file in this repository states the mapping "
        f"from that name to a number, so the two authors have to be read together")
    assert "429 rate-limited" in read(API_DOC), (
        "docs/API.md's envelope table no longer pairs 429 with rate limiting, so the status the "
        "limiter sends has lost the client-facing sentence that explains it")
    upstream = read(UPSTREAM_429)
    assert re.search(r"r\.status_code == 429 or r\.status_code >= 500", upstream), (
        "the one shipped 429 that is NOT this status is `openai_compat`'s retry on the provider's "
        "answer; this census excludes it by name, so if that line moves the exclusion has to be "
        "re-read rather than silently widened")


def test_every_limiter_claim_in_the_repository_is_classified_and_the_walk_reaches_it():
    """The open-ended half: every rate-limit claim the repository holds is a carrier, an override or excused.

    The census above is a list of shapes in files someone enumerated. This scan applies the same shapes to
    the whole repository, so a ceiling written in a document nobody listed is still read. Refusing to read
    something is allowed exactly twice -- the generated trees and dot-directories `walk()` prunes, and this
    census's own file -- and every refusal is proved to cost nothing the scan claims: the narrower
    population this census replaced must come out a subset, each named carrier must be admitted, the
    per-tree file counts must stay near what ships, and this file's rows must genuinely be unexplainable.
    """
    caps = authority()
    raised = {value for _label, value in raised_sites()}
    defaults = {caps[AUTH_VAR], caps[AI_VAR]}
    rows = claim_rows()
    seen = {path for path, _text in walk(*SCAN_POPULATION)}
    lost = sorted(str(p.relative_to(ROOT)) for p in {p for p, _t in walk(*BASELINE_POPULATION)} - seen)
    assert not lost, (
        f"{lost} was read by the population this scan replaced and is not read now: the widening was "
        f"supposed to add coverage, and a prune rule that swallows a shipped tree turns the census into a "
        f"report about fewer files than its own docstring claims")
    unread = sorted(str(p.relative_to(ROOT)) for p in CARRIERS if p not in seen)
    assert not unread, (
        f"{unread} is a file this gate reads a number out of, yet walk() does not admit it: a carrier "
        f"named in CARRIERS and refused by SCAN_SUFFIXES (or swallowed by a prune rule) means the census "
        f"reconciles a claim against text it never opened")
    clash = LOCAL_DOTFILES & {p.name for p in CARRIERS}
    assert not clash, (
        f"{sorted(clash)} is both a shipped carrier and a name the scan excuses as the operator's local "
        f"config: the whitelist is for what a deployment owns, and a shipped example in it is a hiding "
        f"place with a plausible reason attached")
    per_dir: dict[str, int] = {}
    for path in seen:
        top = str(path.relative_to(ROOT)).split(os.sep)[0]
        per_dir[top] = per_dir.get(top, 0) + 1
    thin = {d: (per_dir.get(d, 0), want) for d, want in MIN_FILES_BY_DIR.items()
            if per_dir.get(d, 0) < want}
    assert not thin, (
        f"the walk reads {thin} as (found, floor) per shipped source tree: a census that walks the "
        f"repository and reads almost none of it agrees with everything, so the floors are measured from "
        f"the walked files at this ref rather than from a total that moves with every commit")
    hidden = [r for r in refused_claims() if Path(r[0]).name not in LOCAL_DOTFILES]
    assert not hidden, (
        f"{hidden} state a limiter claim in a file the suffix list refuses: the census is only as "
        f"complete as SCAN_SUFFIXES, so a new shipped text format has to be admitted there -- or named in "
        f"LOCAL_DOTFILES with the reason it is not shipped")
    assert len(rows) >= MIN_CLAIM_ROWS, (
        f"the scan read {len(rows)} claim rows, below the {MIN_CLAIM_ROWS} that ship: a scan that reads "
        f"nothing clears nothing")

    census_text = read(CENSUS)
    self_rows = [(_line_of(census_text, match.start()), shape, int(match["value"]))
                 for shape, pattern in CLAIM_SHAPES for match in pattern.finditer(census_text)]
    self_unexplained = [r for r in self_rows if r[2] not in defaults and r[2] not in raised]
    assert len(self_unexplained) >= MIN_CENSUS_ROWS, (
        f"this census's own file now states only {len(self_unexplained)} rows the classifier cannot "
        f"explain (want {MIN_CENSUS_ROWS}): the exclusion of CENSUS is justified by it quoting ceilings it "
        f"reconciles and by the reader fixtures it carries -- if that has stopped being true, delete the "
        f"exclusion instead of keeping a refusal that hides nothing")

    unexplained, excused = [], []
    for file, number, shape, value in rows:
        if value in defaults:
            continue
        if value in raised:
            continue
        hits = [e for e in EXCUSED_NUMBERS if e["pattern"].search(_lines(read(ROOT / file))[number - 1])]
        if hits:
            excused.append((file, number, value, hits[0]["site"]))
        else:
            unexplained.append(f"{file}:{number} states {value} as a {shape}")
    assert not unexplained, (
        f"{unexplained} state a limiter number that is neither a shipped default, nor the e2e raise, "
        f"nor excused by the ledger: a figure in shipped text that no mechanism explains is exactly "
        f"what this scan is for. If the row is a narrative rather than a configuration, add it to "
        f"EXCUSED_NUMBERS with the sentence that makes it a narrative; if it is a configuration, it has "
        f"to agree with application.yml")
    covered = {site for _f, _n, _v, site in excused}
    dead = [e["site"] for e in EXCUSED_NUMBERS if e["site"] not in covered]
    assert not dead, (
        f"the ledger entries {dead} excuse nothing: an exemption no row matches is a place a number "
        f"could hide, and its reason is no longer a reason about this repository")
    assert len(excused) >= 1, (
        f"the scan excuses {len(excused)} rows; the shipped text contains at least SECURITY.md's "
        f"measurement, so a scan that classifies everything as a default has narrowed itself")
