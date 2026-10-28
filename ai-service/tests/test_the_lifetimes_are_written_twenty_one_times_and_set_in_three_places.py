"""How long each credential lives is written down twenty times and set in three places.

`application.yml` interpolates `JWT_ACCESS_TTL_MINUTES:15` and `JWT_REFRESH_TTL_DAYS:30`. Those two
integers are restated -- never derived -- in the Java property class, both env examples, `docs/SECURITY.md`,
`docs/API.md`, `docs/architecture.md`, the token-pair DTO's own javadoc, and the setters of
`TokenRotationReuseTest`. The third lifetime is different in kind: a password-reset token's window is
`AuthService.RESET_TOKEN_TTL`, a `private static final Duration` with no property, no env knob and no yml
key, and it is promised to a human being in three sentences she reads -- the mail body ("within 30
minutes"), the API table ("good for 30 minutes") and the reset screen's comment ("past its 30 minutes").
Change the constant and all three become lies about the server; none of them is a configuration.

Twenty-one statements of three facts, and the dangerous part is that two of the three facts share the
numeral 30: a refresh token lives 30 DAYS and a reset token lives 30 MINUTES. Every reader in this gate
therefore binds a value to a unit and compares the pair, never the integer alone -- and because the three
lifetimes are pairwise distinct *in seconds*, the pair identifies which credential a sentence is about.

Three asymmetries are censused rather than smoothed over, because each is a decision someone made:
the **shadow** -- `AppProperties` initialises the same two integers in Java, which Spring overwrites when
the yml binds them, so the Java value is a claim about a default rather than a default; the **seconds** --
`TokenPairResponse.accessExpiresInSeconds` is the only place the 15 minutes reach a client, produced by
`JwtService.accessTtlSeconds()` from `Duration.ofMinutes(...)` with no literal anywhere in between, and
then read by nobody: the frontend's own token type declares `expiresIn`, which no producer emits and no
component reads, so the browser learns the lifetime only by being rejected (the file is another session's,
so the drift is pinned open here rather than fixed); and the **test restatement** -- a unit test can set
the two configurable lifetimes but not the reset one, which is why three setter calls exist across two
test files and none of them names a reset window.

The open scan walks the whole repository with the same extractors, so a lifetime written in a document
nobody listed is still read. Its admission rule is a *shape* test, not a ledger: a duration is a claim
when the line it sits on names a credential, and the credential it is charged to is the word nearest the
figure. Measured at the ref this gate lands on, that admits eight rows and excludes thirty-nine
narratives (a 14-day staleness window, a 22-day reminder cadence, a 24-minute suite note, cache TTLs) --
too many to hand-list, which is why none of them is listed. Two clauses hold the rule honest instead: no
excluded row may carry one of the three shipped lifetime pairs (a "30 days" that names no credential is a
sentence a reader can misattribute, so it is refused), and the one spelling the census refuses outright --
compact `Ns` -- is refused only because none of its 64 rows carries a shipped lifetime in seconds.
"""

import os
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

YML = ROOT / "backend" / "src" / "main" / "resources" / "application.yml"
PROPS = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "config" / "AppProperties.java"
AUTH_SVC = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "auth" / "service" / "AuthService.java"
JWT_SVC = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "auth" / "service" / "JwtService.java"
TOKEN_SVC = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "auth" / "service" / "TokenService.java"
PAIR_DTO = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "auth" / "dto" / "TokenPairResponse.java"
RESET_TEST = (
    ROOT / "backend" / "src" / "test" / "java" / "com" / "careeros" / "auth" / "service" / "TokenRotationReuseTest.java"
)
JWT_TEST = (
    ROOT / "backend" / "src" / "test" / "java" / "com" / "careeros" / "auth" / "service" / "JwtServiceTest.java"
)
ENV_DEV = ROOT / ".env.example"
ENV_PROD = ROOT / ".env.prod.example"
SEC = ROOT / "docs" / "SECURITY.md"
API_DOC = ROOT / "docs" / "API.md"
ARCH = ROOT / "docs" / "architecture.md"
RECOVERY_TS = ROOT / "frontend" / "src" / "lib" / "auth-recovery.ts"
CLIENT_TS = ROOT / "frontend" / "src" / "lib" / "api" / "client.ts"
TYPES_TS = ROOT / "frontend" / "src" / "lib" / "api" / "types.ts"
FRONTEND = ROOT / "frontend"
AUTH_MAIN = (ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "auth")

CARRIERS = (YML, PROPS, AUTH_SVC, JWT_SVC, TOKEN_SVC, PAIR_DTO, RESET_TEST, JWT_TEST, ENV_DEV,
            ENV_PROD, SEC, API_DOC, ARCH, RECOVERY_TS, CLIENT_TS, TYPES_TS)

ACCESS_KNOB, REFRESH_KNOB = "JWT_ACCESS_TTL_MINUTES", "JWT_REFRESH_TTL_DAYS"

SCAN_POPULATION = (ROOT,)
SCAN_SUFFIXES = {".md", ".yml", ".yaml", ".ts", ".tsx", ".ps1", ".sh", ".py", ".java", ".example"}
SKIP_DIRS = {"node_modules", ".next", "target", "dist", "__pycache__", ".venv",
             "playwright-report", "test-results", "evals"}
CENSUS = Path(__file__).resolve()

# floors read off `git archive HEAD` at the ref this gate lands on, so a census cannot narrow itself.
MIN_LIFETIME_ROWS = 28
MIN_LIFETIME_CARRIERS = 17
MIN_ACCESS_SITES = 10
MIN_REFRESH_SITES = 7
MIN_RESET_SITES = 4
MIN_CENSUS_ROWS = 8
MIN_CLAIMS_BY_CREDENTIAL = {"access": 3, "refresh": 1, "reset": 4}
MIN_FILES_BY_DIR = {"backend": 241, "ai-service": 228, "frontend": 180, "docs": 12, "e2e": 9, "scripts": 2}
# the refused spelling only has to be *reached*, and 64 rows were measured where this floor sits.
MIN_COMPACT_S_ROWS = 20
MIN_REFUSED_SUFFIX_FILES = 4
# the two yml property keys and the four env assignments: the reach behind `no reset knob is declared`.
MIN_TTL_STATEMENTS = 6

# ---------------------------------------------------------------- readers

INTERP = re.compile(r"\$\{(?P<var>[A-Z][A-Z0-9_]*)(?::(?P<dash>-)?(?P<default>[^}]*))?\}")
YML_TTL = re.compile(r"(?P<prop>access|refresh)-ttl-(?P<unit>minutes|days):\s*\$\{(?P<var>[A-Z_]+):(?P<v>\d+)\}")
JAVA_FIELD = re.compile(r"private int (?P<field>accessTtlMinutes|refreshTtlDays) = (?P<v>\d+);")
# the same shape with the name left open, which is the trap: `presignedUrlTtlSeconds` is a ttl-named
# integer default that is not a credential lifetime at all.
JAVA_TTL_FIELD = re.compile(r"private int (?P<field>\w*[Tt]tl\w*) = (?P<v>\d+);")
JAVA_SETTER = re.compile(r"set(?P<field>AccessTtlMinutes|RefreshTtlDays)\((?P<v>\d+)\)")
# the same call with the name left open: a test that invents a setter for a lifetime production hard-codes
# is a knob that exists only in tests, and the named pattern above would read zero of them.
JAVA_TTL_SETTER = re.compile(r"set(?P<field>\w*Ttl\w*)\(")
KNOB_ASSIGN = re.compile(rf"(?P<var>{ACCESS_KNOB}|{REFRESH_KNOB})[=:]\s*(?P<v>\d+)")
QUOTED_KNOB = re.compile(rf"\"(?P<var>{ACCESS_KNOB}|{REFRESH_KNOB})\"\s*:\s*\"?(?P<v>\d+)")
# The reset window is a constant, so no shipped file interpolates a knob for it -- and that is a decision,
# not an oversight: `RESET_TOKEN_TTL_MINUTES=30` in an env example is an operator-facing promise that
# Spring binds to nothing, because `AuthService` reads no property. These readers are the shapes such a
# knob would take (an env assignment, commented or not, and a yml property key interpolating a TTL var)
# against the same three files, and the scan refuses only the reset-shaped subset -- an `access` or
# `refresh` ttl key has an authority and must not be charged.
RESET_ENV_KNOB = re.compile(r"^[ \t]*(?P<comment>#\s*)?(?P<var>[A-Z0-9_]*RESET[A-Z0-9_]*TTL[A-Z0-9_]*)"
                            r"=(?P<v>\d+)", re.M)
RESET_YML_KEY = re.compile(r"^[ \t]*(?P<prop>[a-z0-9_-]*reset[a-z0-9_-]*ttl[a-z0-9_-]*):", re.M)
TTL_ASSIGN = re.compile(r"^[ \t]*(?P<comment>#\s*)?(?P<var>[A-Z0-9_]*TTL[A-Z0-9_]*)=(?P<v>\d+)", re.M)
TTL_KEY = re.compile(r"^[ \t]*(?P<prop>[a-z0-9_-]*ttl[a-z0-9_-]*):\s*\$\{(?P<var>[A-Z_]*TTL[A-Z_]*)", re.M)
RESET_DECL = re.compile(r"RESET_TOKEN_TTL = Duration\.of(?P<unit>Seconds|Minutes|Hours|Days)\((?P<v>\d+)\)")
DURATION_OF = re.compile(r"Duration\.of(?P<unit>Seconds|Minutes|Hours|Days)\((?P<v>\d+)\)")
CONSUMER_OF = re.compile(r"Duration\.of(?P<unit>Seconds|Minutes|Hours|Days)\(props\.getJwt\(\)\.get(?P<field>AccessTtlMinutes|RefreshTtlDays)\(\)\)")
PROSE_MINUTES = re.compile(r"(?P<v>\d+) minutes\b")
PROSE_DAYS = re.compile(r"(?P<v>\d+) days\b")
PROSE_HOURS = re.compile(r"(?P<v>\d+) hours\b")
PROSE_SECONDS = re.compile(r"(?P<v>\d+) seconds\b")
COMPACT_M = re.compile(r"\b(?P<v>\d+)m\b")
COMPACT_D = re.compile(r"\b(?P<v>\d+)d\b")
COMPACT_H = re.compile(r"\b(?P<v>\d+)h\b")
MAIL_PROMISE = re.compile(r"within (?P<v>\d+) minutes by opening this link")
DOC_PROMISE = re.compile(r"good for (?P<v>\d+) minutes")
SCREEN_PROMISE = re.compile(r"past its (?P<v>\d+) minutes")
ACCESS_LIVE = re.compile(r"Access tokens live (?P<v>\d+) minutes")
ARCH_CLAIM = re.compile(r"JWT access (?P<v>\d+)m\b")
DTO_CLAIM = re.compile(r"Access \(JWT, (?P<v>\d+)m\) \+ opaque refresh \((?P<refresh>\d+)d")
SECONDS_FIELD = re.compile(r"long (?P<field>accessExpiresIn(?P<unit>Seconds|Minutes|Millis))")
TO_UNIT = re.compile(r"return accessTtl\.to(?P<unit>Seconds|Millis|Nanos)\(\);")
SECONDS_METHOD = re.compile(r"public long (?P<name>accessTtl(?P<unit>Seconds|Millis))\(\)")
OF_CALL_HEAD = re.compile(r"TokenPairResponse\.of\(")
RECORD_BODY = re.compile(r"public record TokenPairResponse\((?P<body>.*?)\)\s*\{", re.S)
OF_PARAMS = re.compile(r"public static TokenPairResponse of\((?P<body>[^)]*)\) \{")
CTOR_ARGS = re.compile(r"new TokenPairResponse\((?P<body>[^)]*)\);")
AUTH_TOKENS = re.compile(r"export interface AuthTokens \{(?P<body>.*?)\n\}", re.S)
MEMBER_READ = re.compile(r"\.(?P<key>[A-Za-z][A-Za-z0-9]*)\b")
HARD_SECONDS = re.compile(r"\b(?P<v>\d+)\b")

# ---------------------------------------------------------------- the open census's admission rule

VOCAB = re.compile(r"(?i)(token|jwt|bearer|session|access|refresh|reset)")
CREDENTIAL_WORDS = {
    "access": re.compile(r"(?i)\baccess"),
    "refresh": re.compile(r"(?i)\brefresh"),
    "reset": re.compile(r"(?i)\breset|\bpassword"),
}
CLAIM_SHAPES = (
    ("prose-minutes", PROSE_MINUTES, "minutes"),
    ("prose-days", PROSE_DAYS, "days"),
    ("prose-hours", PROSE_HOURS, "hours"),
    ("prose-seconds", PROSE_SECONDS, "seconds"),
    ("compact-m", COMPACT_M, "minutes"),
    ("compact-d", COMPACT_D, "days"),
    ("compact-h", COMPACT_H, "hours"),
    ("duration-of", DURATION_OF, None),
)
# Two shapes in 19.9's ops plane are durations a reader cannot act on as a credential: a
# metrics window (`careeros.ai.tokens.24h`, "spent in the trailing 24 hours") says how far a
# gauge looks back, and a Prometheus rule's dwell (`for: 15m`) says how long a condition must
# hold before it pages. Neither promises how long a token lives, and neither sentence can be
# misread as one -- the `for:` line names its own field. The `coincident` clause applies this
# same regex, so a row excluded here is still held to the shipped pairs.
NOT_A_LIFETIME = re.compile(
    r"(?i)[._]24h\b|\btrailing\s+\d+\s+(?:hours?|days?|minutes?)\b|^\s*for:\s*\d+[smhd]\b")
# `422s` and `500s` are HTTP status codes written as English plurals, so this spelling is refused;
# `refused_seconds_claims()` below is what makes the refusal a decision rather than a hiding place.
COMPACT_S = re.compile(r"\b(?P<v>\d+)s\b")
# the closed readers whose statements are prose -- the open census has to see every file they charge,
# or the hand-enumerated list is defending a sentence the scan cannot.
PROSE_CLAIM_PATTERNS = (DTO_CLAIM, ACCESS_LIVE, ARCH_CLAIM, MAIL_PROMISE, DOC_PROMISE, SCREEN_PROMISE)

UNIT_SECONDS = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}


def canonical(unit: str) -> str:
    """One spelling of a unit: the yml key says `minutes`, `Duration.of*` says `Minutes`, the javadoc
    says `m`, and a pairing clause that compares them literally would refuse a correct file."""
    return {"m": "minutes", "d": "days", "h": "hours", "s": "seconds"}.get(unit.lower(), unit.lower())


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def line_no(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def groups(path: Path, pattern: re.Pattern, want: int, site: str) -> list[re.Match]:
    """Every match in one file, with the count pinned: a reader that silently narrows is a finding."""
    hits = list(pattern.finditer(read(path)))
    assert len(hits) == want, (
        f"{site}: {pattern.pattern} read {len(hits)} values out of {path.relative_to(ROOT)}, want {want} "
        f"-- the file's spelling moved, so this reader is reporting a number the file does not state")
    return hits


def walk(*population):
    """Repo-wide, pruning while descending: `rglob` cannot, and it reads 100k entries of tool state."""
    seen = []
    for base in population:
        if base.is_file():
            if base.suffix in SCAN_SUFFIXES and base.name not in SKIP_DIRS:
                seen.append(base)
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS]
            for name in filenames:
                p = Path(dirpath) / name
                if p.suffix in SCAN_SUFFIXES:
                    seen.append(p)
    return sorted(set(p for p in seen if p != CENSUS))


def claim_rows():
    """(file, line, shape, value, unit) for every lifetime statement the walk can name."""
    rows = []
    for path in walk(*SCAN_POPULATION):
        rel = path.relative_to(ROOT).as_posix()
        text = read(path)
        for shape, pattern, unit in (
            ("knob", KNOB_ASSIGN, None),
            ("yml-key", YML_TTL, None),
            ("java-field", JAVA_FIELD, None),
            ("java-setter", JAVA_SETTER, None),
            ("reset-decl", RESET_DECL, None),
        ):
            for m in pattern.finditer(text):
                rows.append((rel, line_no(text, m.start()), shape, int(m["v"]), unit))
        for m in DURATION_OF.finditer(text):
            if not re.search(r"(?i)token|jwt|ttl|bearer|credential", text[: m.start()].rsplit("\n", 1)[-1]
                             + text[m.start():m.end() + 80]):
                continue
            rows.append((rel, line_no(text, m.start()), "duration", int(m["v"]), canonical(m["unit"])))
        for shape, pattern, unit in (("prose-minutes", PROSE_MINUTES, "minutes"),
                                     ("prose-days", PROSE_DAYS, "days")):
            for m in pattern.finditer(text):
                rows.append((rel, line_no(text, m.start()), shape, int(m["v"]), unit))
    return rows


def refused_claims():
    """Lifetime claims in files the suffix list refuses -- the census's own hiding places."""
    out = []
    for base in SCAN_POPULATION:
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS]
            for name in filenames:
                p = Path(dirpath) / name
                if p.suffix in SCAN_SUFFIXES or p == CENSUS:
                    continue
                if p.suffix not in {".json", ".txt", ".csv", ".env", ".example2"}:
                    continue
                try:
                    text = read(p)
                except (UnicodeDecodeError, OSError):
                    continue
                hit = KNOB_ASSIGN.search(text) or QUOTED_KNOB.search(text) or MAIL_PROMISE.search(text)
                if hit:
                    out.append((p.relative_to(ROOT).as_posix(), line_no(text, hit.start()), hit.group(0)[:60]))
    return out


# ---------------------------------------------------------------- the three facts

KNOB_UNIT = {ACCESS_KNOB: "minutes", REFRESH_KNOB: "days"}
COMPACT_UNIT = {"m": "minutes", "d": "days"}


def lifetimes() -> dict[str, tuple[int, str, str]]:
    """{credential: (number, unit, what decides it)} for all three lifetimes, read from their authorities.

    The census charges a sentence to a credential by the pair, so the three pairs have to be distinct;
    they are compared in seconds, because 30 minutes and 30 days are one numeral and two facts.
    """
    caps = authority()
    reset_value, reset_unit = reset_authority()
    out = {
        "access": (caps[ACCESS_KNOB][0], caps[ACCESS_KNOB][1], f"application.yml's `${{{ACCESS_KNOB}}}` default"),
        "refresh": (caps[REFRESH_KNOB][0], caps[REFRESH_KNOB][1], f"application.yml's `${{{REFRESH_KNOB}}}` default"),
        "reset": (reset_value, reset_unit, "`AuthService.RESET_TOKEN_TTL`, which no property backs"),
    }
    seconds = {key: value * UNIT_SECONDS[unit] for key, (value, unit, _author) in out.items()}
    ambiguous = [key for key, seconds_value in seconds.items()
                 if sum(1 for other in seconds.values() if other == seconds_value) > 1]
    assert not ambiguous, (
        f"{ambiguous} share a lifetime in seconds ({seconds}): the open census identifies a credential "
        f"by its pair, and two credentials written as the same number of seconds could not be told apart "
        f"by any sentence in the repository")
    return out


def authority() -> dict[str, tuple[int, str]]:
    """{knob: (number, unit)} exactly as `application.yml` interpolates it.

    This is the deciding reading because the yml always defines `app.jwt.*`, so it is what Spring binds
    when the environment is silent; every other statement of the same number is a restatement of it.
    """
    out: dict[str, tuple[int, str]] = {}
    for match in groups(YML, YML_TTL, 2, "application.yml"):
        knob, unit, value = match["var"], canonical(match["unit"]), int(match["v"])
        assert knob in KNOB_UNIT, (
            f"application.yml interpolates {knob!r} on the `{match['prop']}` key: this gate reconciles "
            f"the two lifetimes named {sorted(KNOB_UNIT)}, and a third ttl knob would be a credential "
            f"whose carriers nobody is asked to have restated")
        assert unit == KNOB_UNIT[knob], (
            f"application.yml writes the {knob} default as `-ttl-{unit}`, but the knob's own name says "
            f"{KNOB_UNIT[knob]}: the key and the environment variable would be read by two different "
            f"people and agree on nothing but the numeral")
        out[knob] = (value, unit)
    assert set(out) == set(KNOB_UNIT), (
        f"application.yml interpolates {sorted(out)} of the two lifetimes: with one missing there is no "
        f"default to reconcile the nine restatements against, so the census below would be comparing "
        f"each carrier with itself")
    return out


def reset_authority() -> tuple[int, str]:
    """The password-reset window: a constant in `AuthService`, not a property, knob or yml key."""
    match = groups(AUTH_SVC, RESET_DECL, 1, "AuthService")[0]
    return int(match["v"]), canonical(match["unit"])


def ttl_statements() -> tuple[list[str], list[str]]:
    """(every ttl-shaped knob statement, the ones naming the reset window) over the yml and both examples.

    Both halves come out of one walk over one file list: the absence claim below is only as wide as the
    population the same scan reads, and the access and refresh keys in that population are its proof of
    reach -- a pattern that found no knob anywhere would also "find" no reset knob.
    """
    every: list[str] = []
    reset: list[str] = []
    for path in (YML, ENV_DEV, ENV_PROD):
        text = read(path)
        for pattern, label in ((TTL_ASSIGN, lambda m: m.group(0).strip()),
                               (TTL_KEY, lambda m: f"{m['prop']}: ${{{m['var']}}}")):
            for match in pattern.finditer(text):
                every.append(f"{path.name}:{line_no(text, match.start())} {label(match)}")
        for pattern in (RESET_ENV_KNOB, RESET_YML_KEY):
            for match in pattern.finditer(text):
                reset.append(f"{path.name}:{line_no(text, match.start())} `{match.group(0).strip()}`")
    return every, reset


def lifetime_carriers() -> list[tuple[str, str, int, str]]:
    """(what states it, which knob, what number, in what unit) for every shipped claim about the two."""
    out: list[tuple[str, str, int, str]] = []
    for path in (YML, ENV_DEV, ENV_PROD, SEC):
        text = read(path)
        for match in KNOB_ASSIGN.finditer(text):
            knob = match["var"]
            out.append((f"{path.relative_to(ROOT).as_posix()}:{line_no(text, match.start())} "
                        f"`{knob}`", knob, int(match["v"]), KNOB_UNIT[knob]))
    for match in groups(PROPS, JAVA_FIELD, 2, "AppProperties"):
        knob = ACCESS_KNOB if match["field"].startswith("access") else REFRESH_KNOB
        out.append((f"AppProperties' `{match['field']}` initialiser", knob, int(match["v"]),
                    KNOB_UNIT[knob]))
    for path, want in ((JWT_TEST, 1), (RESET_TEST, 2)):
        for match in groups(path, JAVA_SETTER, want, path.name):
            knob = ACCESS_KNOB if match["field"] == "AccessTtlMinutes" else REFRESH_KNOB
            out.append((f"{path.name}'s `set{match['field']}` call", knob, int(match["v"]),
                        KNOB_UNIT[knob]))
    for match in groups(PAIR_DTO, DTO_CLAIM, 1, "TokenPairResponse"):
        # the javadoc states both lifetimes in compact letters, so the unit is read from the letter.
        out.append(("TokenPairResponse's javadoc access figure", ACCESS_KNOB, int(match["v"]),
                    COMPACT_UNIT["m"]))
        out.append(("TokenPairResponse's javadoc refresh figure", REFRESH_KNOB, int(match["refresh"]),
                    COMPACT_UNIT["d"]))
    for path, pattern, knob, unit, site in (
        (API_DOC, ACCESS_LIVE, ACCESS_KNOB, "minutes", "`Access tokens live N minutes`"),
        (ARCH, ARCH_CLAIM, ACCESS_KNOB, "minutes", "`JWT access Nm`"),
    ):
        match = groups(path, pattern, 1, site)[0]
        out.append((f"{path.relative_to(ROOT).as_posix()}: {site}", knob, int(match["v"]), unit))
    return out


def duration_consumers() -> list[tuple[str, str, str, str]]:
    """(which service, which Duration unit, which property, which knob) for the two wiring points.

    These are where a number and a unit can part without either being wrong on its own: the property is
    an integer of a stated unit and `Duration.of*` is a unit of its own.
    """
    out = []
    for path in (JWT_SVC, TOKEN_SVC):
        for match in CONSUMER_OF.finditer(read(path)):
            field = match["field"]
            knob = ACCESS_KNOB if field == "AccessTtlMinutes" else REFRESH_KNOB
            out.append((path.name, canonical(match["unit"]), field, knob))
    return out


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


def reset_promise_carriers() -> list[tuple[str, int, str]]:
    """(what states the reset window, how long, in what unit) for the four places it is written."""
    out = []
    value, unit = reset_authority()
    out.append(("AuthService's `RESET_TOKEN_TTL` constant", value, unit))
    for path, pattern, site in (
        (AUTH_SVC, MAIL_PROMISE, "the mail body's `within N minutes by opening this link`"),
        (API_DOC, DOC_PROMISE, "API.md's `good for N minutes`"),
        (RECOVERY_TS, SCREEN_PROMISE, "auth-recovery.ts's `past its N minutes`"),
    ):
        match = groups(path, pattern, 1, site)[0]
        out.append((f"{path.relative_to(ROOT).as_posix()}: {site}", int(match["v"]), "minutes"))
    return out


def attach(line: str, start: int, end: int) -> tuple[str | None, list[str]]:
    """Which credential a figure belongs to, decided by the credential word nearest it on its own line.

    This is the directional half of the census. A membership test over the three shipped pairs would let
    "refresh (15d)" pass while telling a reader the refresh token lives as long as an access token, so
    the sentence a figure sits in is what the pair gets charged against.
    """
    gaps: dict[str, int] = {}
    for key, pattern in CREDENTIAL_WORDS.items():
        for word in pattern.finditer(line):
            gap = word.start() - end if word.start() >= end else start - word.end()
            gaps[key] = min(gaps.get(key, gap), max(gap, 0))
    if not gaps:
        return None, []
    closest = min(gaps.values())
    nearest = sorted(key for key, gap in gaps.items() if gap == closest)
    return (nearest[0] if len(nearest) == 1 else None), nearest


def census_rows() -> list[dict]:
    """Every duration the repository writes in a shape a human reads, with what the scan makes of it."""
    caps = lifetimes()
    shipped = {value * UNIT_SECONDS[unit] for value, unit, _author in caps.values()}
    rows = []
    for path in walk(*SCAN_POPULATION):
        rel = path.relative_to(ROOT).as_posix()
        text = read(path)
        for shape, pattern, unit in CLAIM_SHAPES:
            for match in pattern.finditer(text):
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.start())
                line = text[line_start:line_end if line_end != -1 else len(text)]
                value = int(match["v"])
                row_unit = canonical(match["unit"]) if "unit" in match.groupdict() else unit
                credential, nearest = attach(line, match.start("v") - line_start, match.end("v") - line_start)
                rows.append({
                    "file": rel,
                    "line": line_no(text, match.start()),
                    "shape": shape,
                    "value": value,
                    "unit": row_unit,
                    "seconds": value * UNIT_SECONDS[row_unit],
                    "vocabulary": bool(VOCAB.search(line)) and not NOT_A_LIFETIME.search(line),
                    "credential": credential,
                    "nearest": nearest,
                    "shipped": value * UNIT_SECONDS[row_unit] in shipped,
                    "text": line.strip(),
                })
    return rows


def refused_seconds_claims() -> tuple[int, list[dict]]:
    """The compact `Ns` spelling: how many rows it has, and which of them claim a shipped lifetime.

    Refusing the shape is only safe while none of its rows is a duration a credential owns -- every one of
    them today is an HTTP status written as an English plural -- so this returns the population it reached
    as well as the residue, and an empty population is not the same evidence as a clean one.
    """
    caps = lifetimes()
    shipped = {value * UNIT_SECONDS[unit] for value, unit, _author in caps.values()}
    total, charged = 0, []
    for path in walk(*SCAN_POPULATION):
        text = read(path)
        for match in COMPACT_S.finditer(text):
            total += 1
            if int(match["v"]) not in shipped:
                continue
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.start())
            charged.append({
                "file": path.relative_to(ROOT).as_posix(),
                "line": line_no(text, match.start()),
                "text": text[line_start:line_end if line_end != -1 else len(text)].strip(),
            })
    return total, charged


def refused_suffix_files() -> int:
    """How many files the refused-suffix walk actually opened -- the reach guard for `refused_claims`."""
    total = 0
    for base in SCAN_POPULATION:
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS]
            for name in filenames:
                p = Path(dirpath) / name
                if p.suffix in {".json", ".txt", ".csv", ".env", ".example2"} and p != CENSUS:
                    total += 1
    return total


def prose_carrier_files() -> set[str]:
    """Which shipped files state a lifetime in a shape a person reads -- the set the open scan must cover."""
    out = set()
    for path in CARRIERS:
        text = read(path)
        if any(pattern.search(text) for pattern in PROSE_CLAIM_PATTERNS):
            out.add(path.relative_to(ROOT).as_posix())
    assert out, "no shipped file states a lifetime in prose, which means every prose reader reads nothing"
    return out


def split_signature(blob: str) -> list[str]:
    """A Java parameter / component / argument list, one entry per comma.

    These signatures are read positionally because that is exactly how `TokenPairResponse.of` is called,
    so a comma inside a type would be a parse failure worth a red rather than a silent short list.
    """
    parts = [re.sub(r"\s+", " ", part).strip() for part in blob.replace("\n", " ").split(",")]
    out = [part for part in parts if part]
    assert not [part for part in out if "<" in part], (
        f"{out}: a generic type in this signature would need a real parser, and a list split on the "
        f"wrong comma turns one field into two and the positional mapping this reader checks into noise")
    return out


def declared_token_keys() -> list[str]:
    """The keys the frontend's own token type says a token pair has."""
    body = groups(TYPES_TS, AUTH_TOKENS, 1, "AuthTokens")[0]["body"]
    out = re.findall(r"(?m)^\s*([A-Za-z][A-Za-z0-9]*)\??:", body)
    assert out, f"`AuthTokens {body}` declares no keys, so the read audit below compares a type with nothing"
    return out


def call_arguments(text: str, head: re.Pattern, site: str) -> list[str]:
    """A call's argument list, found by balancing parentheses rather than stopping at the first `)`.

    `TokenPairResponse.of(accessToken, rawToken, jwtService.accessTtlSeconds())` ends its *outer* call two
    closes later than `[^)]*` reads, and a scan that stops early hands back a list whose last entry is an
    unfinished expression -- which is exactly the shape that lets a positional mapping look correct.
    """
    hits = list(head.finditer(text))
    assert len(hits) == 1, (
        f"{site}: `{head.pattern}` heads {len(hits)} calls, wanting exactly one, so the argument list "
        f"below has no single owner")
    start = hits[0].end()
    depth, index = 1, start
    while index < len(text) and depth:
        depth += text[index] == "("
        depth -= text[index] == ")"
        index += 1
    assert depth == 0, f"{site}: the call opened at {text[:start].count(chr(10)) + 1} never closes"
    return split_signature(text[start:index - 1])


# ---------------------------------------------------------------- the cases


def test_the_lifetime_readers_parse_shapes_this_repository_does_not_yet_write():
    """Every reader here is exercised against a number, a unit and a default it has never seen.

    Left unproven, a reader that is right by accident reconciles a stale copy without noticing: the one
    that truncates `JWT_ACCESS_TTL_MINUTES:900`, the one that only knows Spring's `:` and not compose's
    `:-`, and the one that hard-codes `Minutes` into the reset window are all green today.
    """
    assert interpolation_default("    access-ttl-minutes: ${JWT_ACCESS_TTL_MINUTES:900}",
                                 ACCESS_KNOB, "yml fixture") == "900", (
        "a three-digit lifetime read back wrong, and every carrier is then reconciled against a "
        "truncated authority")
    assert interpolation_default(f"      {ACCESS_KNOB}: ${{{ACCESS_KNOB}:-24}}",
                                 ACCESS_KNOB, "compose fixture") == "24", (
        "compose's `:-` and Spring's `:` are one character apart and this repository currently "
        "interpolates only the Spring spelling")
    assert interpolation_default(f"      access-ttl-minutes: ${{{ACCESS_KNOB}}}",
                                 ACCESS_KNOB, "bare fixture") is None, (
        "a knob with no default states nothing, which is not the same as an empty default")
    assert interpolation_default(f"      access-ttl-minutes: ${{{ACCESS_KNOB}:-}}",
                                 ACCESS_KNOB, "empty fixture") == "", (
        "an explicit empty default is a value the deployment chose, not an absent one")

    match = RESET_DECL.search("private static final Duration RESET_TOKEN_TTL = Duration.ofHours(1);")
    assert match and match["unit"] == "Hours" and match["v"] == "1", (
        "the reset reader must take the unit from the file rather than from what the file happens to "
        f"say today ({match.group(0) if match else None!r})")
    pair = DTO_CLAIM.search("/** Access (JWT, 5m) + opaque refresh (7d, rotated) token pair. */")
    assert pair and (pair["v"], pair["refresh"]) == ("5", "7"), (
        "the compact javadoc states both lifetimes with different unit letters; a reader that reads "
        "only one of them pairs a number with the wrong credential")
    wired = CONSUMER_OF.search(
        "this.refreshTtl = Duration.ofHours(props.getJwt().getRefreshTtlDays());")
    assert wired and wired["unit"] == "Hours" and wired["field"] == "RefreshTtlDays", (
        "the wiring reader exists to see a `Duration.of*` unit that disagrees with the property it "
        "reads; hard-coding either half of the pair makes it blind to the drift it is for")
    ttl_fields = [m["field"] for m in JAVA_TTL_FIELD.finditer(read(PROPS))]
    assert len(ttl_fields) == 3, (
        f"AppProperties now holds {ttl_fields} as `private int *Ttl* = n;` fields: the trap this reader "
        f"exists for is that a ttl-named integer default is not necessarily a credential lifetime -- "
        f"`presignedUrlTtlSeconds` is a storage URL's, in seconds")
    named = [m["field"] for m in groups(PROPS, JAVA_FIELD, 2, "AppProperties")]
    assert "presignedUrlTtlSeconds" in ttl_fields and "presignedUrlTtlSeconds" not in named, (
        f"the shadow reader names {named}: once it stops naming the two credential fields exactly, a "
        f"file whose third ttl default is a storage figure gets reconciled as a token lifetime")
    assert RESET_ENV_KNOB.search("# RESET_TOKEN_TTL_HOURS=6"), (
        "the reset-knob reader only knows an uncommented assignment, so the commented line an operator "
        "would copy is the one statement about the window this gate cannot refuse")
    assert RESET_YML_KEY.search("    reset-token-ttl-hours: ${SOME_OTHER_DEFAULT:6}"), (
        "the reset-knob reader takes its key from the variable inside the braces rather than the property "
        "name: the property name is what a deployment reads, and a renamed variable would keep the "
        "promise while the reader went quiet")
    assert not RESET_ENV_KNOB.search("JWT_ACCESS_TTL_MINUTES=15") \
        and not RESET_YML_KEY.search("access-ttl-minutes: ${JWT_ACCESS_TTL_MINUTES:15}"), (
        "the refused subset names a ttl knob that says nothing about the reset window: a predicate that "
        "refuses every knob would refuse the two lifetimes that DO have authorities, and this repository "
        "would already be red on its shipped yml")


def test_the_two_configurable_lifetimes_have_one_authority_and_every_carrier_agrees_in_number_and_unit():
    """The yml default decides; the rest restate it, and a restatement is only faithful as a pair.

    `JWT_ACCESS_TTL_MINUTES=15` and `JWT_REFRESH_TTL_DAYS=30` reuse the two numerals the reset window and
    the storage presign also carry, so a comparison of integers alone would pass on a document that says
    15 days. The unit is read from the shape that carries it -- the knob's own name, the field's suffix,
    the javadoc's `m` and `d`, the prose's word -- and both halves have to match.
    """
    caps = authority()
    carriers = lifetime_carriers()
    assert len(carriers) >= MIN_LIFETIME_CARRIERS, (
        f"the lifetime census read {len(carriers)} carriers, below the {MIN_LIFETIME_CARRIERS} the "
        f"shipped files state: a census that reads nothing reconciles a stub")
    per_knob = {knob: sum(1 for _l, k, _v, _u in carriers if k == knob) for knob in KNOB_UNIT}
    assert (per_knob[ACCESS_KNOB] >= MIN_ACCESS_SITES
            and per_knob[REFRESH_KNOB] >= MIN_REFRESH_SITES), (
        f"the census splits {per_knob} between the two knobs, wanting at least {MIN_ACCESS_SITES} "
        f"access and {MIN_REFRESH_SITES} refresh statements: one knob covered by a single stray match "
        f"is a census that passes on a coincidence")
    problems = [
        f"{label} states {value} {unit}, the shipped default for {knob} is "
        f"{caps[knob][0]} {caps[knob][1]}"
        for label, knob, value, unit in carriers
        if (value, unit) != caps[knob]
    ]
    assert not problems, (
        f"the credential lifetimes are written in more than one file and they disagree -- "
        f"{'; '.join(problems)} -- the authority is application.yml's `${{JWT_ACCESS_TTL_MINUTES}}` / "
        f"`${{JWT_REFRESH_TTL_DAYS}}` default, because that file always defines `app.jwt.*` and "
        f"therefore decides what Spring binds; a reader who follows the stale statement issues tokens "
        f"for a lifetime nobody chose")


def test_the_java_initialisers_are_a_shadow_and_still_say_what_spring_would_bind():
    """`AppProperties` and the reuse test initialise the same two integers, and every reader assumes it.

    The yml binds over the top of both, so a Java default that has drifted is not a second decision -- it
    is a statement about a decision that no longer holds, which is exactly what a reader wiring the
    property by hand (a test, a new service, a `main()` that skips Spring) will get.
    """
    caps = authority()
    for match in groups(PROPS, JAVA_FIELD, 2, "AppProperties"):
        knob = ACCESS_KNOB if match["field"].startswith("access") else REFRESH_KNOB
        assert (int(match["v"]), KNOB_UNIT[knob]) == caps[knob], (
            f"AppProperties' `{match['field']}` initialiser is {match['v']}, the yml default for "
            f"{knob} is {caps[knob][0]} {caps[knob][1]}: Spring overwrites it in a deployed backend and "
            f"leaves it in force in a unit test, so the two runtimes issue different tokens while every "
            f"document states one figure")
    setters = [m for path, want in ((JWT_TEST, 1), (RESET_TEST, 2))
               for m in groups(path, JAVA_SETTER, want, path.name)]
    for match in setters:
        knob = ACCESS_KNOB if match["field"] == "AccessTtlMinutes" else REFRESH_KNOB
        assert (int(match["v"]), KNOB_UNIT[knob]) == caps[knob], (
            f"`TokenRotationReuseTest` sets {match['field']} to {match['v']} while the shipped default "
            f"for {knob} is {caps[knob][0]}: the test would then be asserting a rotation rule against a "
            f"lifetime no deployment issues, and a reader copying its setup line copies a number that "
            f"was never chosen")
    ttl_setters = {match["field"] for path in (JWT_TEST, RESET_TEST)
                   for match in JAVA_TTL_SETTER.finditer(read(path))}
    assert ttl_setters == {"AccessTtlMinutes", "RefreshTtlDays"}, (
        f"the two auth tests call {sorted(ttl_setters)} on the property object: only the access and "
        f"refresh lifetimes are configurable, so a third ttl setter -- `setResetTokenTtl*` would be the "
        f"shape -- is a knob that exists only in tests and never reaches the server that issues the link")
    assert len({m["field"] for m in setters}) == 2, (
        "the test restates the two configurable lifetimes and no third: a setter for a lifetime that is "
        "hard-coded in production would be a test-only knob, which is the drift the reuse test exists "
        "to prevent")


def test_the_reset_window_has_one_author_and_three_sentences_a_human_reads():
    """`RESET_TOKEN_TTL` is a constant, so the documents about it are not restatements of a default.

    There is no knob, no env assignment and no yml key for it -- and this case is what keeps that sentence
    true: the mail body, the API table and the reset screen's comment each tell a person how long they
    have, all three are prose about a Java literal, and a fourth statement in the shape of a configuration
    would be a promise no deployment can keep. Comparing the carriers in seconds is what lets a
    `Duration.ofHours(1)` be an honest change -- and what makes `ofMinutes(15)` with the sentences
    untouched a lie about the server.
    """
    promises = reset_promise_carriers()
    assert len(promises) == MIN_RESET_SITES, (
        f"the reset window is stated by {len(promises)} carriers, wanting {MIN_RESET_SITES}: the "
        f"constant and the three sentences are this case's whole population, and a census that has lost "
        f"one of them has lost the human-visible half of the promise")
    author_label, author_value, author_unit = promises[0]
    author_seconds = author_value * UNIT_SECONDS[author_unit]
    for label, value, unit in promises[1:]:
        assert value * UNIT_SECONDS[unit] == author_seconds, (
            f"{label} promises {value} {unit} while `RESET_TOKEN_TTL` is {author_value} {author_unit}: "
            f"the server would answer `RESET_TOKEN_INVALID` on a link the user was told was still good, "
            f"and the reset screen's copy has no way to find out")
    assert "resetLink" in read(AUTH_SVC), (
        "the mail no longer puts a link next to the window it expires in, so the sentence this case "
        "reconciles is describing a token the reader cannot open")
    every, reset = ttl_statements()
    assert len(every) >= MIN_TTL_STATEMENTS, (
        f"the knob scan read {len(every)} ttl-shaped statements out of application.yml and the two env "
        f"examples, below the {MIN_TTL_STATEMENTS} shipped at this ref: `no reset window is declared as a "
        f"knob` would then be a report about files the reader no longer opens, and the access and refresh "
        f"keys it does read are the only proof that it opened them")
    assert not reset, (
        f"{reset} states the password-reset window in the shape of a knob: `AuthService.RESET_TOKEN_TTL` "
        f"is a `private static final Duration` that reads no property, so nothing binds that line and the "
        f"operator who sets it is promised a window the mail body still hard-codes -- either give the "
        f"constant a property and let this case reconcile its carriers, or delete the statement")


def test_thirty_days_and_thirty_minutes_are_two_facts_and_no_wiring_mixes_them_up():
    """The numeral 30 is the refresh token's days and the reset token's minutes; the units are the fact.

    Each `Duration.of*` that consumes a property is paired with the unit the property's own name states,
    and the two compact letters in the DTO's javadoc are read as units rather than as digits, because a
    swap between them leaves every integer correct and changes which credential lives a month.
    """
    consumers = duration_consumers()
    assert len(consumers) == 2, (
        f"the wiring census reads {len(consumers)} `Duration.of*(props.getJwt().get*())` sites, wanting "
        f"the two shipped ones: with a third, a lifetime would reach a Duration through a path this "
        f"case has not paired")
    for name, unit, field, knob in consumers:
        assert unit == KNOB_UNIT[knob], (
            f"{name} builds its Duration with `of{unit}` from `{field}`, which the property's own name "
            f"and the knob {knob} state as {KNOB_UNIT[knob]}: fifteen minutes handed to `ofDays` is a "
            f"fifteen-day access token, and no integer in the repository would read wrong")
    caps = authority()
    reset_value, reset_unit = reset_authority()
    confusable = [
        f"{label} states {value} {unit}"
        for label, knob, value, unit in lifetime_carriers()
        if knob == REFRESH_KNOB and (value, unit) == (reset_value, reset_unit)
    ]
    assert not confusable, (
        f"{'; '.join(confusable)} -- which is also exactly the reset window: the two 30s are the reason "
        f"every reader here binds a unit, and a statement that could be either credential is a "
        f"statement about neither")
    access, refresh = caps[ACCESS_KNOB], caps[REFRESH_KNOB]
    assert (access[1], refresh[1], reset_unit) == ("minutes", "days", "minutes"), (
        f"the shipped units are access {access[1]}, refresh {refresh[1]}, reset {reset_unit}: this "
        f"case's premise is that two of the three are minutes and one is days, and if that stops being "
        f"true the pairing readers have to be re-read rather than trusted")


def test_the_access_lifetime_reaches_the_client_as_seconds_that_no_file_writes_down():
    """`15` minutes becomes one integer on the wire, and the unit is stated twice along the way.

    `JwtService` converts the property to a `Duration`, `accessTtlSeconds()` converts that to a number,
    `TokenService` hands it to `TokenPairResponse.of` as the third argument, and the record component is
    named for its unit. Each step is where a minutes figure and a seconds name can part without either
    side being wrong alone -- and no file writes `900`, so the yml default is the only author of it.
    """
    caps = lifetimes()
    access_value, access_unit, access_author = caps["access"]
    access_seconds = access_value * UNIT_SECONDS[access_unit]

    wired = [m for m in CONSUMER_OF.finditer(read(JWT_SVC)) if m["field"] == "AccessTtlMinutes"]
    assert len(wired) == 1, (
        f"JwtService builds the access Duration {len(wired)} times from `getAccessTtlMinutes()`: the "
        f"property reaches a Duration through exactly one seam, and a second one is a second decision "
        f"about how long an access token lives")
    conversion = groups(JWT_SVC, TO_UNIT, 1, "JwtService accessTtlSeconds body")[0]
    method = groups(JWT_SVC, SECONDS_METHOD, 1, "JwtService accessTtlSeconds header")[0]
    assert canonical(conversion["unit"]) == canonical(method["unit"]), (
        f"`accessTtl{method['unit']}()` returns `accessTtl.to{conversion['unit']}()`: the method's name "
        f"is the only thing telling a caller what unit the number is in, and a `toMillis()` behind a "
        f"`Seconds` name hands the browser 900000 where it reads 900")
    fields = groups(PAIR_DTO, SECONDS_FIELD, 2, "TokenPairResponse seconds declarations")
    assert {canonical(m["unit"]) for m in fields} == {canonical(conversion["unit"])}, (
        f"the seconds figure is declared as {[m['field'] for m in fields]} with units "
        f"{[m['unit'] for m in fields]} while the producer converts with "
        f"`to{conversion['unit']}()`: the record's own name is the client's only unit annotation")

    components = split_signature(groups(PAIR_DTO, RECORD_BODY, 1, "TokenPairResponse record")[0]["body"])
    params = split_signature(groups(PAIR_DTO, OF_PARAMS, 1, "TokenPairResponse of")[0]["body"])
    arguments = split_signature(groups(PAIR_DTO, CTOR_ARGS, 1, "TokenPairResponse constructor")[0]["body"])
    assert len(components) == 4, (
        f"the token pair record has {components}: four components are accessToken, refreshToken, "
        f"tokenType and the lifetime, and a fifth would be a claim the client's type has never been "
        f"reconciled against")
    long_components = [c for c in components if c.startswith("long ")]
    assert len(long_components) == 1, (
        f"{long_components} of {components} are `long`: the lifetime is the one number the pair carries, "
        f"and a second would be a second credential's expiry with no authority of its own")
    seconds_component = long_components[0].split()[1]
    assert seconds_component == fields[0]["field"], (
        f"the record's only numeric component is `{seconds_component}` but the seconds reader named "
        f"`{fields[0]['field']}`: one of the two is reading a field that is no longer the lifetime")
    assert params[-1] == f"long {seconds_component}", (
        f"`of(...)` takes {params} and its last parameter is not the record's `{seconds_component}`: "
        f"the factory is where a caller's positional argument gets its meaning, so the lifetime has to "
        f"arrive in the slot the record reserves for it")
    assert arguments.index(seconds_component) == components.index(f"long {seconds_component}"), (
        f"the constructor call `{arguments}` does not land the seconds parameter in the component that "
        f"declares it")
    assert '"Bearer"' in arguments, (
        f"the constructor arguments are {arguments}: `tokenType` is filled by a literal, and if that "
        f"literal moves a slot every argument after it shifts -- which is how a lifetime ends up in the "
        f"field a reader calls the token type")

    supplied = call_arguments(read(TOKEN_SVC), OF_CALL_HEAD, "TokenService issueTokenPair")
    assert len(supplied) == len(params), (
        f"`TokenPairResponse.of` is called with {supplied} but declared with {params}: a record built "
        f"positionally has no protection against an argument count that changed on one side only")
    assert re.search(rf"\b{method['name']}\(\)$", supplied[-1]), (
        f"the factory's last argument is `{supplied[-1]}`, not `{access_author}` converted to seconds "
        f"(the {access_value} {access_unit} the yml states, which is {access_seconds} at this ref): "
        f"this is the one site where the configured lifetime and the number the client is told can part, "
        f"and a literal here freezes a default that the yml still says it owns")
    literal_seconds = []
    integers = 0
    for path in sorted(AUTH_MAIN.rglob("*.java")):
        text = read(path)
        for match in HARD_SECONDS.finditer(text):
            integers += 1
            if int(match["v"]) in {v * UNIT_SECONDS[u] for v, u, _a in caps.values()}:
                literal_seconds.append(f"{path.name}:{line_no(text, match.start())} {match['v']}")
    assert integers >= 20, (
        f"the auth sources expose {integers} integer literals for the seconds-literal scan to rule out: "
        f"a scan that reads nothing reports the same `no hard-coded lifetime` it would report on a file "
        f"full of them")
    assert not literal_seconds, (
        f"{literal_seconds} -- one of the three lifetimes expressed in seconds is written as a literal in "
        f"the auth sources: it agrees with the shipped default right now, and it will silently disagree "
        f"the day someone retires a token by editing the yml")

    declared = set(declared_token_keys())
    emitted = {component.split()[1] for component in components}
    both = declared & emitted
    drift = sorted(declared ^ emitted)
    assert len(both) >= 2, (
        f"the backend's token pair and the frontend's `AuthTokens` share {sorted(both)}: the read audit "
        f"below can only compare a key the client actually asks for against a field the record actually "
        f"sends once at least one name sits on both sides")
    reads: dict[str, list[str]] = {}
    for path in walk(FRONTEND):
        text = read(path)
        for match in MEMBER_READ.finditer(text):
            if match["key"] in declared | emitted:
                reads.setdefault(match["key"], []).append(
                    f"{path.relative_to(ROOT).as_posix()}:{line_no(text, match.start())}")
    assert {"accessToken", "refreshToken"} <= set(reads), (
        f"the frontend read {sorted(reads)} of the pair's keys: a scanner whose denominator is empty "
        f"would report the same clean audit for a client that never touches the payload")
    charged = {key: sites for key, sites in reads.items() if key not in both}
    assert not charged, (
        f"the frontend reads {charged}, and only {sorted(both)} of {drift} are named by both sides of "
        f"the contract: `{drift}` are invisible today -- the client stores the two tokens and learns the "
        f"expiry by being rejected -- so a first read of one of them is a claim about a value no "
        f"producer authors or no type declares")


def test_the_open_census_charges_a_lifetime_to_the_credential_sitting_beside_it():
    """A duration written next to the word `refresh` is a claim about the refresh token, wherever it is.

    The closed carrier list is twenty-one sentences somebody enumerated; this scan is the rest of the
    repository. Its admission rule is a shape test rather than a ledger, because the narratives it has to
    skip are too many to list and would rot the moment another session wrote a comment.
    """
    caps = lifetimes()
    rows = census_rows()
    shapes = {row["shape"] for row in rows}
    silent = sorted({shape for shape, _p, _u in CLAIM_SHAPES} - shapes)
    assert not silent, (
        f"the census read shapes {sorted(shapes)} and nothing in {silent}: an extractor that matches no "
        f"spelling the repository writes is a reader of an empty set, and every floor taken with it is a "
        f"claim about nothing")
    admitted = [row for row in rows if row["vocabulary"]]
    closed = claim_rows()
    unread = {"knob", "yml-key", "java-field", "java-setter", "reset-decl", "duration",
              "prose-minutes", "prose-days"} - {row[2] for row in closed}
    assert not unread, (
        f"the closed extractors produced no row for {sorted(unread)}: the carrier counts below are read "
        f"with those extractors, so one that has stopped matching makes its own floor a count of nothing")
    assert len(closed) >= MIN_LIFETIME_ROWS, (
        f"the closed extractors read {len(closed)} lifetime statements across the repository, below the "
        f"{MIN_LIFETIME_ROWS} at this ref, while the open census admits {len(admitted)} of them as "
        f"credential claims: the two scans disagree about how much of the repository talks about "
        f"lifetimes, and one of them has stopped looking")
    assert len(admitted) >= MIN_CENSUS_ROWS, (
        f"the open scan admitted {len(admitted)} credential-worded lifetime rows, below the "
        f"{MIN_CENSUS_ROWS} shipped at the ref this gate lands on: a census that narrowed is a census "
        f"that stopped reading")
    tallied: dict[str, int] = {}
    problems = []
    for row in admitted:
        if row["credential"] is None:
            problems.append(f"{row['file']}:{row['line']} `{row['text'][:60]}` puts {row['value']} "
                            f"{row['unit']} equally between {row['nearest']}, so the sentence states "
                            f"which token it means for neither")
            continue
        tallied[row["credential"]] = tallied.get(row["credential"], 0) + 1
        value, unit, author = caps[row["credential"]]
        if row["seconds"] != value * UNIT_SECONDS[unit]:
            problems.append(f"{row['file']}:{row['line']} states {row['value']} {row['unit']} for the "
                            f"{row['credential']} token while {author} is {value} {unit}")
    thin = {key: tallied.get(key, 0) for key, floor in MIN_CLAIMS_BY_CREDENTIAL.items()
            if tallied.get(key, 0) < floor}
    assert not thin, (
        f"the open census tallies {tallied}, wanting {MIN_CLAIMS_BY_CREDENTIAL}; it came up short on "
        f"{thin}: a credential the scan no longer sees in prose is a credential only the "
        f"hand-enumerated carriers still defend")
    assert not problems, (
        "a lifetime statement contradicts the authority for the credential its own sentence names, or "
        f"sits between two of them: {'; '.join(problems)}")
    coincident = [row for row in rows
                  if not row["vocabulary"] and row["shipped"]
                  and not NOT_A_LIFETIME.search(row["text"])]
    assert not coincident, (
        f"{[(r['file'], r['line'], r['value'], r['unit']) for r in coincident]} write a shipped lifetime "
        f"without naming a credential on their line: the numeral 30 alone already means two different "
        f"tokens in this repository, so a sentence that could be about either is a sentence the next "
        f"reader guesses at -- put the figure beside its credential's own word, or state it in a unit no "
        f"token uses")
    narrative = [row for row in rows if not row["vocabulary"] and not row["shipped"]]
    assert len(narrative) > len(admitted), (
        f"the scan admits {len(admitted)} credential rows and excludes {len(narrative)} narratives: the "
        f"rule's whole argument for not being a hand ledger is that the excluded population is the large "
        f"one -- if the predicate has started naming most of the repository's durations it no longer "
        f"distinguishes a claim from a sentence")

    reached, claimed = refused_seconds_claims()
    assert reached >= MIN_COMPACT_S_ROWS, (
        f"the refused `Ns` spelling yielded {reached} rows: the scan must read the shape it declines to "
        f"charge, or `no compact-seconds claim was found` is a report about a spelling it never looked at")
    assert not claimed, (
        f"{[(r['file'], r['line'], r['text'][:40]) for r in claimed]} state a shipped lifetime in the "
        f"compact `Ns` spelling the census refuses: every one of those rows is an HTTP status written as "
        f"an English plural today, and a real duration written that way has to be charged")

    suffixes = refused_suffix_files()
    assert suffixes >= MIN_REFUSED_SUFFIX_FILES, (
        f"the refused-suffix walk opened {suffixes} files before concluding nothing hides in them")
    assert not refused_claims(), (
        f"{refused_claims()} state a knob or the mail's promise in a suffix the census refuses to read")

    covered = {row["file"] for row in admitted}
    prose_files = prose_carrier_files()
    assert prose_files <= covered, (
        f"the hand-enumerated readers charge a lifetime in {sorted(prose_files - covered)}, which the "
        f"open scan does not admit: the closed list would then be defending a sentence the scan cannot "
        f"see, and a change to it would pass here and fail nobody")
    counts = {}
    for path in walk(*SCAN_POPULATION):
        counts[path.relative_to(ROOT).as_posix().split("/")[0]] = \
            counts.get(path.relative_to(ROOT).as_posix().split("/")[0], 0) + 1
    narrow = {key: counts.get(key, 0) for key, floor in MIN_FILES_BY_DIR.items()
              if counts.get(key, 0) < floor}
    assert not narrow, (
        f"the walk reads {narrow} files under those top-level directories, below the floors "
        f"{MIN_FILES_BY_DIR}: every count above is a statement about the population the scan actually "
        f"opened, so a narrowed walk narrows the census with it")
