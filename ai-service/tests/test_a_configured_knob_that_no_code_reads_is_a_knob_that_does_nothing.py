"""A knob no code reads is a knob that does nothing: thirty-four `app.*` keys ship, two are read by nobody.

`application.yml`'s `app:` block writes thirty-four leaves. Thirty-two of them reach a reader that some
service calls: twenty-two through a Java getter, two (`app.web.base-url` through a `@Value` placeholder in
`AuthService`'s constructor and `app.mail.link-secret`, read in `MailLinks` and again by the startup
guard) that never appear in `AppProperties`, and eight `app.email.*` leaves through
`EmailConfig`'s one transport bean. One (`app.storage.enabled`) is not written by the shipped file but
is armed by `@ConditionalOnProperty` on the MinIO bean, whose `matchIfMissing = true` makes silence mean "on".
The last two -- `app.upload.max-file-size-bytes` and `app.upload.presigned-url-ttl-seconds` -- bind fields in
`AppProperties`, are interpolated by no `${ENV}` variable, and are read by nothing: `getUpload()` itself has
zero call sites, so the whole block is unreachable from production code.

The danger is not an untidy file. It is that a dead knob looks exactly like a live one. An operator who
raises `max-file-size-bytes` to 50 MB changes the cap in zero places: the number that refuses an upload is
`FileValidator.DEFAULT_MAX_BYTES`, a `public static final long` written once in Java and passed by the one
overload every production caller uses -- all four of them call the no-argument `validate(content)`, and the
two-argument form exists in production only as that delegation. The sentence the candidate reads, "File
exceeds the limit of 20MB", is computed from that constant, not from the file. The second dead knob is worse,
because its authority is not even wired: `getPresignedUrl(key, ttl)` is the method that would consume a TTL,
declared on the port, implemented against the MinIO client, faked for tests -- and has no caller, while two
documents and the port's own javadoc promise that reads go through a presigned URL. `ResumeController` says
the opposite in a comment: files are served user-scoped *rather than* through a presigned URL. So the 600 is
one of three statements of a duration no request ever carries, and the three promises are pinned next to the
zero-caller finding rather than smoothed over: closing this gate means either wiring the port or deleting
the sentences, and doing it in one place where the next reader can see which was chosen.

A census that greps only for `props.getX().getY()` would have called `app.storage.enabled` dead too, so this
gate reads three arming mechanisms -- accessor, `@Value`, condition -- and requires all three to come up empty
before it charges a key. Three more asymmetries are censused rather than smoothed, because each is a decision
someone made: the **prod credential pair** (`MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` are in the dev example and
not in the prod one, because the prod compose re-arms them from the MinIO root pair -- without that mapping
the backend would sign in to production with the dev defaults the yml interpolates), the **proxy trust
switch** (`APP_HTTP_TRUST_FORWARDED_FOR` sits in neither example because it is a deployment decision, and
`DEPLOYMENT.md`'s checklist is where an operator meets it -- putting it in the copy-me dev file would invite
a directly reached backend to trust a header any client can write), and the **env-only key**
(`app.email.console.log-body` is reachable from the environment, is stated in `docs/API.md`, is named in no
env example and written in no yml). What this gate reports is a population, not a bug list: 22 accessor
readers, 10 `@Value` leaf binders (the web base-url, the mail link secret and the eight mail knobs) plus the env-only mail switch,
1 condition, 2 bound-but-unread leaves, 1 field that is the shadow of a live key.
Two of those readings are each taken twice on purpose, because each pair was found by turning one of them off:
`AppProperties`'s nested classes are enumerated from the class declarations *and* from the `private final`
holder fields, since the leaf walk follows the first and the key derivation follows the second, and an arm that
planted a class with no field stayed green until the two lists were compared; and a dead knob's env carrier is
charged by the key's own words (`MAX_FILE_SIZE_BYTES`), not by one guessed prefix spelling, because the first
version of that clause looked for `UPLOAD_UPLOAD_...` and an example naming `UPLOAD_APP_MAX_FILE_SIZE_BYTES`
walked straight past it.
"""

import os
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
BACKEND = ROOT / "backend"
MAIN_JAVA = BACKEND / "src" / "main" / "java"
TEST_JAVA = BACKEND / "src" / "test" / "java"
PKG = MAIN_JAVA / "com" / "careeros"

YML = BACKEND / "src" / "main" / "resources" / "application.yml"
PROPS = PKG / "config" / "AppProperties.java"
FILEVAL = PKG / "storage" / "FileValidator.java"
STORAGE_PORT = PKG / "storage" / "StorageService.java"
MINIO_IMPL = PKG / "storage" / "MinioStorageService.java"
INGEST_SVC = PKG / "knowledge" / "service" / "FileIngestService.java"
RESUME_SVC = PKG / "resume" / "service" / "ResumeService.java"
RESUME_CTRL = PKG / "resume" / "web" / "ResumeController.java"
GEH = PKG / "common" / "GlobalExceptionHandler.java"
FILEVAL_TEST = TEST_JAVA / "com" / "careeros" / "storage" / "FileValidatorTest.java"
INMEM_STORAGE = TEST_JAVA / "com" / "careeros" / "support" / "InMemoryStorageConfig.java"
ABSTRACT_IT = TEST_JAVA / "com" / "careeros" / "AbstractIntegrationTest.java"
GROWTH_IT = TEST_JAVA / "com" / "careeros" / "ai" / "service" / "GrowthPlanRepositoryIT.java"
ENV_DEV = ROOT / ".env.example"
ENV_PROD = ROOT / ".env.prod.example"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
SEC_DOC = ROOT / "docs" / "SECURITY.md"
DEPLOYMENT_DOC = ROOT / "docs" / "DEPLOYMENT.md"
API_DOC = ROOT / "docs" / "API.md"
ARCH_DOC = ROOT / "docs" / "architecture.md"
FE_SOURCE = ROOT / "frontend" / "src" / "components" / "knowledge" / "source-actions.tsx"
FE_ACTIONS = ROOT / "frontend" / "src" / "lib" / "hooks" / "actions.ts"
# The upload refusals are copy now: the sentence naming the cap lives in the English
# catalogue and the screen renders it, so the reader below follows the sentence there.
FE_COPY = ROOT / "frontend" / "src" / "lib" / "i18n" / "translations.ts"

# ---------------------------------------------------------------- the population, pinned both ways

APP_LEAVES = frozenset({
    "cors.allowed-origins", "web.base-url", "jwt.secret", "jwt.access-ttl-minutes", "jwt.refresh-ttl-days",
    "internal.token", "storage.endpoint", "storage.access-key", "storage.secret-key", "storage.bucket",
    "ai-service.base-url", "ratelimit.enabled", "ratelimit.auth-per-minute", "ratelimit.ai-per-minute",
    "ratelimit.mail-per-minute",
    "ratelimit.mfa-per-minute",
    "upload.max-file-size-bytes", "upload.presigned-url-ttl-seconds",
    "retention.expired-token-days",
    "email.provider", "email.from", "email.smtp.host", "email.smtp.port", "email.smtp.username",
    "email.smtp.password", "email.smtp.starttls", "email.smtp.ssl", "mail.link-secret",
    "http.trust-forwarded-for", "deployment.env",
    "push.vapid-public-key", "push.vapid-private-key", "push.contact", "push.ttl-seconds",
    "security.mfa-secret",
})
HOLDERS = frozenset({"Cors", "Jwt", "Internal", "Storage", "AiService", "Ratelimit", "Upload",
                     "Retention", "Http", "Deployment", "Push"})
# `security` joins the namespace without an AppProperties holder, the same shape `mail` has:
# 36.1's seed key is read through `@Value` by the cipher and the guard, so the admission rule
# follows the yml's block rather than a nested class that would exist only to be unread.
HOLDER_KEYS = frozenset({"cors", "web", "jwt", "internal", "storage", "ai-service", "ratelimit", "upload",
                         "retention", "email", "mail", "http", "deployment", "push", "security"})

# leaf -> (holder, field, accessor, the files that call it), measured at the ref this gate lands on.
READERS = {
    # Since 31.11 the guard reads the allow-list to refuse a prod boot whose origins no
    # deployed shell can use; SecurityConfig still applies the list to the CORS filter.
    "cors.allowed-origins": ("Cors", "allowedOrigins", "getAllowedOrigins",
                             ("config/ProductionGuard.java", "config/SecurityConfig.java")),
    "jwt.secret": ("Jwt", "secret", "getSecret",
                   ("auth/service/JwtService.java", "config/ProductionGuard.java")),
    "jwt.access-ttl-minutes": ("Jwt", "accessTtlMinutes", "getAccessTtlMinutes", ("auth/service/JwtService.java",)),
    "jwt.refresh-ttl-days": ("Jwt", "refreshTtlDays", "getRefreshTtlDays", ("auth/service/TokenService.java",)),
    "internal.token": ("Internal", "token", "getToken",
                       ("ai/HttpAiServiceClient.java", "ai/SseRelayService.java", "auth/security/InternalApiFilter.java",
                        "config/ProductionGuard.java")),
    "storage.endpoint": ("Storage", "endpoint", "getEndpoint", ("storage/MinioStorageService.java",)),
    # Since 31.9 the guard reads the credential pair to refuse a prod boot on the
    # repository's published object-store defaults; the store itself still reads all
    # four keys, so the pair legitimately has two readers and the other two have one.
    "storage.access-key": ("Storage", "accessKey", "getAccessKey",
                           ("config/ProductionGuard.java", "storage/MinioStorageService.java")),
    "storage.secret-key": ("Storage", "secretKey", "getSecretKey",
                           ("config/ProductionGuard.java", "storage/MinioStorageService.java")),
    "storage.bucket": ("Storage", "bucket", "getBucket", ("storage/MinioStorageService.java",)),
    "ai-service.base-url": ("AiService", "baseUrl", "getBaseUrl",
                            ("ai/HttpAiServiceClient.java", "ai/SseRelayService.java")),
    # The rate-limit knobs are read by the filter that enforces them and, since
    # 16.2, by the status route that reports them — a knob with two readers
    # still has to be the one the operator edits, and the table names both so
    # a third reader is a change an operator has to see.
    "ratelimit.enabled": ("Ratelimit", "enabled", "isEnabled",
                          ("ratelimit/RateLimitFilter.java", "ratelimit/RateLimitController.java")),
    "ratelimit.auth-per-minute": ("Ratelimit", "authPerMinute", "getAuthPerMinute",
                                   ("ratelimit/RateLimitFilter.java", "ratelimit/RateLimitController.java")),
    "ratelimit.ai-per-minute": ("Ratelimit", "aiPerMinute", "getAiPerMinute",
                                 ("ratelimit/RateLimitFilter.java", "ratelimit/RateLimitController.java")),
    # The mail ceiling is the filter's alone: the status route reports the AI
    # bucket's remaining tokens (keyed by the principal) and deliberately says
    # nothing about the mail bucket, so a controller read appearing here would
    # mean the status page started advertising a quota it does not track.
    "ratelimit.mail-per-minute": ("Ratelimit", "mailPerMinute", "getMailPerMinute",
                                   ("ratelimit/RateLimitFilter.java",)),
    # The MFA ceiling is the filter's alone for the mail bucket's reason, and one worse:
    # 36.2's bucket is the only one keyed by the signed-in account, so no status route
    # reports it -- a second reader would advertise a quota nothing else tracks.
    "ratelimit.mfa-per-minute": ("Ratelimit", "mfaPerMinute", "getMfaPerMinute",
                                  ("ratelimit/RateLimitFilter.java",)),
    # The proxy declaration is read by the two places that need a client address
    # (the limiter and the session record); a third reader would be another
    # decision about what "trusted" means.
    "http.trust-forwarded-for": ("Http", "trustForwardedFor", "isTrustForwardedFor",
                                 ("auth/web/AuthController.java", "ratelimit/RateLimitFilter.java")),
    # The deployment switch is read by the bean that refuses a prod boot on the
    # repository's published secrets; it is a knob like any other, and a second
    # reader would be another place that decides what "prod" means.
    "deployment.env": ("Deployment", "env", "getEnv",
                       ("config/ProductionGuard.java",)),
    # The retention window is read only by the sweep it bounds: a second reader
    # (a status route, a manual trigger) would be a caller deciding row ages on
    # its own, so the single site is the claim.
    "retention.expired-token-days": ("Retention", "expiredTokenDays", "getExpiredTokenDays",
                                     ("auth/retention/RetentionSweeper.java",)),
    # The VAPID pair is read by the bean that chooses a transport (PushConfig) and by no
    # other site: the guard cannot name a half pair because the bean already refuses to
    # start on one, and the sender receives the parsed keys rather than the properties.
    "push.vapid-public-key": ("Push", "vapidPublicKey", "getVapidPublicKey", ("config/PushConfig.java",)),
    "push.vapid-private-key": ("Push", "vapidPrivateKey", "getVapidPrivateKey", ("config/PushConfig.java",)),
    "push.contact": ("Push", "contact", "getContact", ("config/PushConfig.java",)),
    "push.ttl-seconds": ("Push", "ttlSeconds", "getTtlSeconds", ("config/PushConfig.java",)),
}

# A shared accessor name belongs to more than the knob. `isEnabled()` is the
# ratelimit switch and also `IngestionFeed`'s own per-feed toggle, and the
# feed DTO reads the latter. A call site that names no holder getter is not a
# read of an `app.*` key, so it is pinned here rather than charged to a knob --
# and the pin is exact, so a bare two-statement knob read (`Ratelimit rl =
# app.getRatelimit(); ... rl.isEnabled()`) cannot hide among these by being
# added.
NON_KNOB_SHARED = {
    ("job/dto/IngestionFeedDtos.java", "isEnabled"),
}

# the bound-but-unread leaves, each stated with the authority that decides the value instead and with what an
# operator who edits the key would then see.
DEAD_KNOBS = {
    "upload.max-file-size-bytes": (
        "storage/FileValidator.DEFAULT_MAX_BYTES, a compile-time constant",
        "the refusal still prints 20MB, computed from the constant"),
    "upload.presigned-url-ttl-seconds": (
        "nothing: StorageService.getPresignedUrl(key, ttl) has no production caller",
        "no request carries a TTL, so 600 seconds is one of three statements of an unrouted duration"),
}

# `AppProperties` fields whose key the `app:` block never writes -- armed by a mechanism that reads the
# environment rather than the property object, which is why they are shadows and not dead knobs.
ORPHAN_FIELDS = {"Storage.enabled"}

# the two yml leaves that no `${ENV}` interpolates, and the third that is a shipped boolean default.
FILE_ONLY_LEAVES = frozenset({"ratelimit.enabled", "upload.max-file-size-bytes", "upload.presigned-url-ttl-seconds"})
PROD_CREDENTIAL_VARS = frozenset({"MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"})
# Vars neither env example names because they are deployment decisions, not
# copy-me dev values: docs/DEPLOYMENT.md's checklist is the carrier, and the gate
# reads that document rather than waving the var through. Turning X-Forwarded-For
# on in a dev example would invite a directly reached backend to trust a header
# any client can write, which is the bypass finding #2 measured.
DOC_NAMED_VARS = frozenset({"APP_HTTP_TRUST_FORWARDED_FOR"})
EMAIL_KEY = "email.console.log-body"

SCAN_SUFFIXES = {".md", ".yml", ".yaml", ".ts", ".tsx", ".java", ".py", ".sh", ".ps1", ".example", ".txt"}
SKIP_DIRS = {"node_modules", ".next", "target", "dist", "__pycache__", ".venv",
             "playwright-report", "test-results", "evals"}
CENSUS = Path(__file__).resolve()

# floors read off this repository at the ref the gate lands on, so a narrowed scan cannot report "no readers"
# for a census that simply stopped reading files.
MIN_MAIN_JAVA_FILES = 150
MIN_ACCESSOR_SITES = 15
MIN_SCANNED_FILES = 600
MIN_PROP_ROWS = 250
MIN_ADMITTED_ROWS = 18
MIN_REFUSED_ROWS = 200
MIN_MENTION_FILES = 20

# ---------------------------------------------------------------- readers

YML_LEAF = re.compile(r"^(?P<indent> +)(?P<key>[a-z][a-z0-9-]*):(?P<value>\s*(?P<inline>\S.*?))?\s*$")
ENV_INTERP = re.compile(r"^\$\{(?P<var>[A-Z][A-Z0-9_]*):(?P<default>.*)\}$")
ENV_NAME = re.compile(r"^[#]?\s*(?P<var>[A-Z][A-Z0-9_]*)=", re.M)
HOLDER_FIELD = re.compile(r"^    private final (?P<cls>\w+) (?P<name>\w+) = new", re.M)
NESTED_CLASS = re.compile(r"public static class (?P<cls>\w+) \{")
LEAF_FIELD = re.compile(r"^ {8}private (?P<type>[\w.]+(?:<[\w.,<> ]+>)?) (?P<name>\w+)(?: = (?P<init>[^;]+))?;", re.M)
VALUE_APP_KEY = re.compile(r'@Value\("\$\{app\.(?P<key>[a-z0-9._-]+)(?::(?P<default>[^}"]*))?\}"\)')
CONDITION_APP = re.compile(r'@ConditionalOnProperty\(\s*prefix = "app\.(?P<prefix>[a-z][a-z0-9-]*)",'
                           r'\s*name = "(?P<name>[a-z][a-z0-9-]*)"'
                           r'(?:,\s*havingValue = "(?P<having>[^"]*)")?'
                           r'(?:,\s*matchIfMissing = (?P<missing>true|false))?')
MULTIPART = re.compile(r"max-(?P<which>file|request)-size:\s*(?P<v>\d+)(?P<unit>KB|MB|GB)")
CONSTANT_BYTES = re.compile(r"DEFAULT_MAX_BYTES\s*=\s*(?P<a>\d+)L?\s*\*\s*(?P<b>\d+)\s*\*\s*(?P<c>\d+)\s*;")
MESSAGE_MIBS = re.compile(r'"File exceeds the limit of " \+ \(\s*(?P<num>\w+)\s*/\s*\(\s*(?P<a>\d+)\s*\*\s*'
                         r'(?P<b>\d+)\s*\)\s*\) \+ "MB"')
VALIDATE_CALL = re.compile(r"FileValidator\.validate\((?P<args>[^)]*)\)")
PRESONED_CALL = re.compile(r"getPresignedUrl\s*\(")
# the three sentences that promise a presigned read, each pinned by its own spelling: a promise that moved is
# a decision about the unrouted port, and this gate is where that decision has to be re-taken.
PRESIGNED_GET = re.compile(r"presigned GET only")
PRESIGNED_READS = re.compile(r"presigned reads")
PORT_PROMISE = re.compile(r"reads go through presigned URLs only")
TTL_USED = re.compile(r"\.expiry\(\(int\)\s*ttl\.to(?P<unit>Seconds|Millis|Nanos)\(\)\)")
DOC_CAP = re.compile(r"caps size at (?P<v>\d+) MB")
FE_CAP = re.compile(r"over the (?P<v>\d+) MB ingestion cap")
FE_MIRROR = re.compile(r"Mirrors `storage/FileValidator`: (?P<v>\d+) MB cap")
MAX_DOCUMENT = re.compile(r"MAX_DOCUMENT_BYTES = (?P<a>\d+) \* (?P<b>\d+) \* (?P<c>\d+)")
RESUME_MAX = re.compile(r"RESUME_MAX_BYTES = (?P<a>\d+) \* (?P<b>\d+) \* (?P<c>\d+)")
PROP_MENTION = re.compile(r"app\.(?P<s1>[a-z][a-z0-9-]*)\.(?P<s2>[a-z][a-z0-9_-]*)")
COMPOSE_ENV = re.compile(
    r"^\s+(?P<var>MINIO_ACCESS_KEY|MINIO_SECRET_KEY):\s*\$\{(?P<from>[A-Z_]+)(?=[:\}])", re.M
)
# The integration harness names the switch inside a multi-line array (it also declares
# the forwarded-for trust), so the opening brace and the whitespace before the string
# are optional here; the single-string spelling is still matched.
TEST_SOURCE = re.compile(
    r'@TestPropertySource\(properties = (?:\{\s*)?"app\.storage\.enabled=false"')
NO_HANDLER = re.compile(r"MaxUploadSizeExceededException|MultipartException|MultiPartException")


# ---------------------------------------------------------------- helpers

def read(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    except (UnicodeDecodeError, OSError):
        return ""


def line_no(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def groups(path: Path, pattern: re.Pattern, want: int, site: str) -> list:
    """Every match in one file, with the count pinned: a reader that silently narrows is a finding."""
    hits = list(pattern.finditer(read(path)))
    assert len(hits) == want, (
        f"{site}: {pattern.pattern!r} read {len(hits)} values out of {rel(path)}, want {want} "
        f"-- that file's spelling moved, so this reader is reporting a number the file no longer states")
    return hits


def relaxed(kebab: str) -> str:
    parts = kebab.split("-")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def holder_class(top: str) -> str:
    camel = relaxed(top)
    return camel[:1].upper() + camel[1:]


def accessor_for(field: str, java_type: str) -> str:
    return ("is" if java_type == "boolean" else "get") + field[:1].upper() + field[1:]


def app_leaves() -> dict:
    """`app:`'s leaves as {dotted key: raw value}, folded from the block's own indentation."""
    lines = read(YML).splitlines()
    starts = [i for i, line in enumerate(lines) if line == "app:"]
    assert len(starts) == 1, (
        f"application.yml has {len(starts)} top-level `app:` blocks, want exactly one -- the census below "
        f"reads one block and would otherwise read the wrong one")
    out, stack = {}, []
    for line in lines[starts[0] + 1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            break
        match = YML_LEAF.match(line)
        if not match:
            continue
        indent, key = len(match["indent"]), match["key"]
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if match["inline"] is None:
            stack.append((indent, key))
        else:
            out[".".join([s[1] for s in stack] + [key])] = match["inline"].strip()
    return out


def prop_structure() -> tuple:
    """({holder class: getter}, {"Class.field": (java type, initialiser or None)})."""
    text = read(PROPS)
    holders = {m["cls"]: "get" + m["name"][:1].upper() + m["name"][1:] for m in HOLDER_FIELD.finditer(text)}
    fields = {}
    for match in NESTED_CLASS.finditer(text):
        start = match.end() - 1
        depth, i = 0, start
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        for field in LEAF_FIELD.finditer(text[start:i]):
            init = (field["init"] or "").strip() or None
            fields[f"{match['cls']}.{field['name']}"] = (field["type"].strip(), init)
    return holders, fields


def declared_holders() -> set:
    """The nested classes AppProperties declares, whether or not a field binds one."""
    return {m["cls"] for m in NESTED_CLASS.finditer(read(PROPS))}


def main_sources() -> dict:
    """Every `backend/src/main/java` file except the property class itself -- the reader population."""
    return {p: read(p) for p in MAIN_JAVA.rglob("*.java") if p != PROPS}


def sites(accessor: str, sources: dict) -> list:
    """Call sites of `.accessor(`, each with the full line it sits on, which is what resolves a shared name."""
    pattern = re.compile(rf"\.{accessor}\s*\(")
    out = []
    for path, text in sources.items():
        for match in pattern.finditer(text):
            end = text.find("\n", match.start())
            line = text[text.rfind("\n", 0, match.start()) + 1:(len(text) if end < 0 else end)].strip()
            out.append((path, line_no(text, match.start()), line))
    return sorted(out, key=lambda row: (rel(row[0]), row[1]))


def value_bindings() -> dict:
    """{key (without the `app.` prefix) -> (file, placeholder default or None)} for every `@Value` binder."""
    out = {}
    for path in MAIN_JAVA.rglob("*.java"):
        for match in VALUE_APP_KEY.finditer(read(path)):
            out[match["key"]] = (path, (match["default"] or "").strip() or None)
    return out


def conditions() -> dict:
    """{key -> (file, havingValue, matchIfMissing)} -- the third arming mechanism, split across two arguments."""
    out = {}
    for path in MAIN_JAVA.rglob("*.java"):
        for match in CONDITION_APP.finditer(read(path)):
            out[f"{match['prefix']}.{match['name']}"] = (path, match["having"], match["missing"])
    return out


def walk_repo() -> list:
    seen = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix in SCAN_SUFFIXES and path != CENSUS:
                seen.append(path)
    return sorted(set(seen))


def prop_rows() -> list:
    """(file, line, key, admitted) for every `app.<seg>.<seg>` mention the walk can name."""
    out = []
    for path in walk_repo():
        text = read(path)
        for match in PROP_MENTION.finditer(text):
            out.append((path, line_no(text, match.start()), f"{match['s1']}.{match['s2']}",
                        match["s1"] in HOLDER_KEYS))
    return out


def to_bytes(number: str, unit: str) -> int:
    """Spring's `DataSize` counts a megabyte as 1048576 bytes, so `20MB` and `20 * 1024 * 1024` are one number."""
    return int(number) * {"KB": 1024, "MB": 1024 * 1024, "GB": 1024 * 1024 * 1024}[unit]


def armed_bytes() -> int:
    m = groups(FILEVAL, CONSTANT_BYTES, 1, "the armed upload cap")[0]
    return int(m["a"]) * int(m["b"]) * int(m["c"])


# ---------------------------------------------------------------- the cases

def test_the_app_block_writes_thirty_five_leaves_and_each_binds_by_one_of_three_mechanisms():
    leaves = app_leaves()
    assert len(leaves) >= 15, (
        f"the `app:` block parsed to {len(leaves)} leaves, below the 15 the shipped file writes -- the parser "
        f"stopped following the indentation, so every number below is a reading of nothing")
    assert frozenset(leaves) == APP_LEAVES, (
        f"`app:`'s leaves are not the thirty-five pinned here: extra={sorted(frozenset(leaves) - APP_LEAVES)} "
        f"missing={sorted(APP_LEAVES - frozenset(leaves))} -- a new key needs a binder and a reader before it "
        f"is a configuration rather than a comment")

    holders, fields = prop_structure()
    assert frozenset(holders) == HOLDERS, (
        f"AppProperties binds the holder fields {sorted(holders)}, not the ten holders {sorted(HOLDERS)} "
        f"-- the leaf-to-field derivation keys off these names, so the census would aim at the wrong class")
    declared = declared_holders()
    assert declared == frozenset(holders), (
        f"AppProperties declares the nested classes {sorted(declared)} while its fields bind "
        f"{sorted(holders)} -- the leaf walk follows the declarations and the key derivation follows the "
        f"fields, so a name in only one list is a holder the census reads but the walk never fills, or one "
        f"the walk fills but nothing can name its keys")
    assert len(fields) == 25, (
        f"AppProperties declares {len(fields)} leaf fields, want the 25 whose readers are censused here -- the "
        f"population moved, so 'every field has a reader or a ledger entry' is a claim about a different file")

    values, conds = value_bindings(), conditions()
    assert len(values) >= 2, (
        f"the `@Value` scan found {len(values)} app.* placeholders, want at least the two that bind the web "
        f"base-url and the console-mail switch -- this is a binder that lives outside AppProperties, so a scan "
        f"that misses it reports a bound key as unbound")
    assert len(conds) == 1, (
        f"the `@ConditionalOnProperty` scan found {len(conds)} arming conditions, want exactly the one that "
        f"chooses the MinIO bean -- this is the mechanism that keeps a reader-less key alive, so its count is "
        f"load-bearing for every verdict below")

    for key in sorted(leaves):
        top, rest = key.split(".", 1)
        binder = holder_class(top)
        if binder not in holders:
            assert key in values, (
                f"`app.{key}` names no holder class ({binder}) and no @Value placeholder, so Spring binds the key "
                f"to nothing: the file writes a configuration no code can receive")
            continue
        assert f"{binder}.{relaxed(rest)}" in fields, (
            f"`app.{key}` derives the field {binder}.{relaxed(rest)}, which AppProperties does not declare, so "
            f"the relaxed binding Spring would attempt has no target to write into")
    assert frozenset(values) - frozenset(leaves) == frozenset({EMAIL_KEY}), (
        f"keys bound by @Value that the shipped file never writes: {sorted(frozenset(values) - frozenset(leaves))}, "
        f"want exactly [{EMAIL_KEY}] -- an env-only knob is a decision, and this gate is where it is named")
    assert "web.base-url" in leaves and "Web" not in holders, (
        "`app.web.base-url` is expected to bind through AuthService's constructor with no `Web` class in "
        "AppProperties; if a Web holder now exists the key changed binder and READERS must re-aim")


def test_a_live_knob_is_one_whose_name_a_reader_calls_and_the_reader_resolves_to_a_holder():
    sources = main_sources()
    assert len(sources) >= MIN_MAIN_JAVA_FILES, (
        f"the reader census scanned {len(sources)} files under backend/src/main/java, below the "
        f"{MIN_MAIN_JAVA_FILES} this repository ships -- a census reading fewer files can report a reader-less "
        f"key that in fact has one")
    total = sum(len(sites(accessor, sources)) for _, _, accessor, _ in READERS.values())
    assert total >= MIN_ACCESSOR_SITES, (
        f"the {len(READERS)} read keys together produced {total} accessor call sites, below {MIN_ACCESSOR_SITES}: the "
        f"scanner is not finding calls that exist, so a 'no reader' verdict anywhere else is a scanner failure")

    _, fields = prop_structure()
    owners_by_accessor = {}
    for name, (java_type, _init) in fields.items():
        holder, field = name.split(".")
        owners_by_accessor.setdefault(accessor_for(field, java_type), []).append(holder)
    shared = {a: o for a, o in owners_by_accessor.items() if len(o) > 1}
    assert "isEnabled" in shared, (
        f"AppProperties no longer declares `isEnabled` in two holders (Storage, Ratelimit); the accessor names "
        f"that repeat are {sorted(shared)} -- a name that stopped being shared makes the attribution clause "
        f"below vacuous, and the census would then be counting calls it cannot resolve")

    for key, (holder, field, accessor, files) in sorted(READERS.items()):
        rows = sites(accessor, sources)
        assert rows, (
            f"`app.{key}` binds AppProperties.{holder}.{field} and nothing outside AppProperties calls "
            f".{accessor}() any more -- that is the bound-but-unread class this gate names in DEAD_KNOBS, so "
            f"the key has to move there instead of staying listed as read")
        # A name only one holder declares resolves to that key wherever it is
        # called. A shared name (`isEnabled` is Storage's and Ratelimit's, and
        # also an entity's own toggle) does not, so for those the line has to
        # name the holder getter that produced the object the call is on.
        found = tuple(sorted({rel(p).split("/careeros/")[-1] for p, _, line in rows
                              if accessor not in shared or f".get{holder}(" in line}))
        assert found == tuple(sorted(files)), (
            f"the files reading `app.{key}` through .{accessor}() are {found}, not the pinned {sorted(files)} -- "
            f"a caller added or moved changes which file an operator has to edit for this knob to matter")

    unattributed = [(rel(p).split("/careeros/")[-1], n, a, owners) for a, owners in sorted(shared.items())
                    for p, n, line in sites(a, sources)
                    if not any(f".get{holder}(" in line for holder in owners)]
    unknown = [row for row in unattributed if (row[0], row[2]) not in NON_KNOB_SHARED]
    assert not unknown, (
        f"these call sites of a shared accessor name no holder getter on the same line, so the census cannot "
        f"say which key arms them: {unknown} -- a two-statement read (holder into a local, then accessor) "
        f"is legal Java and this scan is line-scoped, so the site has to name its holder for the count to mean "
        f"anything")
    assert {(f, a) for f, _n, a, _owners in unattributed} == set(NON_KNOB_SHARED), (
        f"the pinned non-knob sites of shared accessor names are no longer the measured ones: "
        f"{sorted({(f, a) for f, _n, a, _owners in unattributed})} -- a pinned site that moved or a new bare "
        f"site that is not a knob read has to be re-measured, not excused")

    secret = [rel(p) for p, _, _ in sites("getSecret", sources)]
    secret_key = [rel(p) for p, _, _ in sites("getSecretKey", sources)]
    assert secret and not any("Minio" in s for s in secret), (
        f"the prefix-collision control failed: .getSecret() was charged {secret}, which must not include "
        f"MinioStorageService's .getSecretKey() call -- the open-paren anchor is the only thing that separates "
        f"a shorter accessor from the longer one that starts with it")
    assert secret_key and not any("Jwt" in s for s in secret_key), (
        f".getSecretKey() was charged {secret_key}; the JWT secret's reader must not double as the MinIO "
        f"credential's, or one file becomes the witness for two different knobs")


def test_two_bound_knobs_have_no_reader_under_any_mechanism_and_the_ledger_names_what_arms_them_instead():
    leaves, sources = app_leaves(), main_sources()
    holders, fields = prop_structure()
    values, conds = value_bindings(), conditions()

    def accessor_of(key):
        top, rest = key.split(".", 1)
        name = f"{holder_class(top)}.{relaxed(rest)}"
        if name not in fields:
            return None
        return accessor_for(name.split(".")[1], fields[name][0])

    unread = []
    for key in sorted(leaves):
        if key in values or key in conds:
            continue
        accessor = accessor_of(key)
        assert accessor is not None, (
            f"`app.{key}` binds no AppProperties field, no @Value placeholder and no condition, so it is not "
            f"bound at all -- that is a different fault than unread and needs its own ledger")
        if not sites(accessor, sources):
            unread.append(key)
    assert frozenset(unread) == frozenset(DEAD_KNOBS), (
        f"the leaves bound and read by nothing are {sorted(unread)}, the ledger says {sorted(DEAD_KNOBS)} -- "
        f"a knob that lost or gained its last reader makes this list a description of a different tree")

    assert not sites("getUpload", sources), (
        "AppProperties.getUpload() now has a caller outside the property class, so the `upload` block is no "
        "longer unreachable from production code, and the two DEAD_KNOBS entries have to be re-argued")
    for holder in sorted(HOLDERS - {"Upload"}):
        assert sites(holders[holder], sources), (
            f"nothing obtains props.{holders[holder]}() any more, yet {holder} leaves are listed as read: the "
            f"leaf-accessor census would still find those calls on a receiver this repository no longer builds")

    assert armed_bytes() == int(leaves["upload.max-file-size-bytes"]), (
        f"FileValidator arms {armed_bytes()} bytes while `app.upload.max-file-size-bytes` reads "
        f"{leaves['upload.max-file-size-bytes']} -- the dead knob and the armed cap have come apart, so the file "
        f"no longer even describes the limit the server applies")
    rows = [(rel(p), line_no(read(p), m.start()), m["args"].strip())
            for p in (INGEST_SVC, RESUME_SVC) for m in VALIDATE_CALL.finditer(read(p))]
    assert len(rows) == 4, (
        f"production calls FileValidator.validate() {len(rows)} times ({rows}), want the 4 measured here -- a "
        f"new caller is where a caller could start passing a cap, which is what would retire a DEAD_KNOBS entry")
    assert all(args == "content" for _, _, args in rows), (
        f"these validate() calls pass more than the bytes: {rows} -- at least one upload path now takes a cap "
        f"from somewhere, so the constant is no longer the only authority and the ledger is stale")
    two_arg = [m for m in VALIDATE_CALL.finditer(read(FILEVAL_TEST)) if "," in m["args"]]
    assert len(two_arg) == 1, (
        f"FileValidatorTest calls the two-argument validate() {len(two_arg)} times; the single call is the "
        f"evidence that the larger overload is reachable only from a test, which is exactly what makes the "
        f"yml knob dead rather than merely unused today")

    assert TTL_USED.search(read(MINIO_IMPL)), (
        f"the ledger says no request carries the presigned TTL, but {rel(MINIO_IMPL)} no longer converts a "
        f"Duration into the MinIO request's expiry -- re-read DEAD_KNOBS['upload.presigned-url-ttl-seconds']")
    callers = [(rel(p), line_no(t, m.start())) for p, t in sources.items()
               if p not in (STORAGE_PORT, MINIO_IMPL) for m in PRESONED_CALL.finditer(t)]
    assert not callers, (
        f"StorageService.getPresignedUrl now has production callers {callers} -- the second DEAD_KNOBS entry "
        f"reports an unrouted port, so wiring the method means the TTL knob needs a reader, not a eulogy")

    promises = {site: len(list(pattern.finditer(read(path))))
                for site, path, pattern in (("architecture.md's ingest row", ARCH_DOC, PRESIGNED_GET),
                                            ("architecture.md's upload bullet", ARCH_DOC, PRESIGNED_READS),
                                            ("the port javadoc", STORAGE_PORT, PORT_PROMISE))}
    assert all(count == 1 for count in promises.values()), (
        f"the presigned read is promised by {promises}, and each of the three sentences is worth exactly one "
        f"mention -- no caller answers them (above), so a sentence that moved is somebody deciding the unrouted "
        f"port without saying so here")


def test_a_key_the_shipped_file_never_writes_is_still_armed_when_a_condition_reads_the_environment():
    leaves = app_leaves()
    holders, fields = prop_structure()
    conds = conditions()

    derived = {f"{holder_class(top)}.{relaxed(rest)}" for top, rest in (k.split(".", 1) for k in leaves)}
    without_key = sorted(set(fields) - derived)
    assert frozenset(without_key) == frozenset(ORPHAN_FIELDS), (
        f"AppProperties fields whose key the `app:` block never writes are {without_key}, the ledger says "
        f"{sorted(ORPHAN_FIELDS)} -- a field gaining a yml key, or a key losing its field, is a binding change "
        f"and the shadow that stops being a shadow is exactly what this gate exists to notice")
    assert "Storage.enabled" in fields and fields["Storage.enabled"][1] == "true", (
        f"the ledger describes Storage.enabled as the shadow of a key armed by matchIfMissing, but the field "
        f"now reads {fields.get('Storage.enabled')} -- an uninitialised or differently-initialised copy is a "
        f"different claim about what silence means")

    assert "storage.enabled" in conds, (
        f"no @ConditionalOnProperty arms `app.storage.enabled` (the scan sees {sorted(conds)}), yet ORPHAN_FIELDS "
        f"still calls it a live key read through the environment -- the accessor would then be plain dead and "
        f"the field belongs in DEAD_KNOBS instead")
    path, having, missing = conds["storage.enabled"]
    assert having == "true" and missing == "true", (
        f"`app.storage.enabled` is now conditioned on havingValue={having!r} matchIfMissing={missing}; the ledger "
        f"describes a key the shipped file leaves silent, and silence means on only under this pair")
    assert "storage.enabled" not in leaves, (
        "application.yml now writes app.storage.enabled, so the key the integration tests switch off is no "
        "longer armed only by matchIfMissing -- the shipped default and the test override need re-reconciling")

    carriers = [(rel(p), len(list(TEST_SOURCE.finditer(read(p))))) for p in (ABSTRACT_IT, GROWTH_IT)]
    assert all(n == 1 for _, n in carriers) and len({n for _, n in carriers}) == 1, (
        f"the integration tests that switch MinIO off now carry {carriers} @TestPropertySource annotations; "
        f"these two are the only code that ever sets the key to false, so a moved count means the switch has "
        f"more or fewer carriers than ORPHAN_FIELDS states")
    assert "app.storage.enabled=false" in read(INMEM_STORAGE), (
        "the in-memory storage double no longer names the key it replaces, so nothing in the tree explains why "
        "app.storage.enabled is a live key that application.yml never writes")
    enabled_sites = [row for row in sites("isEnabled", main_sources()) if "getStorage" in row[2]]
    assert not enabled_sites, (
        f"somebody now calls props.getStorage().isEnabled(): {enabled_sites} -- the property object would be a "
        f"second reader of a key the bean condition already decides, and the shadow becomes a live copy")


def test_the_cap_the_dead_knob_would_set_is_a_compile_time_constant_and_the_container_refuses_before_it():
    leaves = app_leaves()
    multipart = {m["which"]: to_bytes(m["v"], m["unit"]) for m in groups(YML, MULTIPART, 2, "the container's two ceilings")}
    assert set(multipart) == {"file", "request"}, (
        f"the multipart scan read {sorted(multipart)}, want both the file and the request ceiling -- the "
        f"ordering below compares the two, so a missing one silently shortens the claim")
    assert multipart["request"] >= multipart["file"], (
        f"spring.servlet.multipart caps a request at {multipart['request']} bytes but one file at "
        f"{multipart['file']}: a single-file request that fits the file cap would be refused for its envelope, "
        f"and the answer it gets is not the validator's")

    armed = armed_bytes()
    assert armed == multipart["file"], (
        f"FileValidator refuses at {armed} bytes while the container stops at {multipart['file']}: whichever "
        f"way the gap runs, the limit a candidate is told and the limit that answers are no longer one number")
    assert armed == int(leaves["upload.max-file-size-bytes"]), (
        f"the armed cap is {armed} and the unread `app.upload.max-file-size-bytes` reads "
        f"{leaves['upload.max-file-size-bytes']} -- they agreed by accident before this gate, and an operator "
        f"editing one still changes only the other")

    message = groups(FILEVAL, MESSAGE_MIBS, 1, "the refusal sentence's own arithmetic")[0]
    assert message["num"] == "maxBytes", (
        f"the refusal divides {message['num']!r} to print its megabytes, not the `maxBytes` argument the cap is "
        f"compared against -- the sentence would then report a number other than the limit it enforces")
    divisor = int(message["a"]) * int(message["b"])
    assert divisor == 1024 * 1024, (
        f"the refusal computes megabytes by {message['a']} * {message['b']}, not 1024 * 1024 -- if the divisor "
        f"moved, the printed 'N MB' lies about the unit the cap is written in")
    printed = armed // divisor
    doc = groups(SEC_DOC, DOC_CAP, 1, "docs/SECURITY.md's upload row")[0]
    assert int(doc["v"]) == printed, (
        f"docs/SECURITY.md tells a reader the cap is {doc['v']} MB while the refusal computes {printed} MB from "
        f"FileValidator.DEFAULT_MAX_BYTES -- that row is the number's only promise to a human, so it reconciles "
        f"to the constant that arms it")

    mirror = groups(FE_SOURCE, FE_MIRROR, 1, "the client's mirror comment")[0]
    client = groups(FE_COPY, FE_CAP, 1, "the client's refusal sentence in the English catalogue")[0]
    product = groups(FE_SOURCE, MAX_DOCUMENT, 1, "the client's own cap expression")[0]
    fe_bytes = int(product["a"]) * int(product["b"]) * int(product["c"])
    assert int(mirror["v"]) == int(client["v"]) == printed and fe_bytes == armed, (
        f"the knowledge screen claims {mirror['v']}/{client['v']} MB from a constant of {fe_bytes} bytes against "
        f"a server cap of {armed}; its comment says it mirrors storage/FileValidator, so the mirror owes the same "
        f"number and the same unit")
    resume = groups(FE_ACTIONS, RESUME_MAX, 1, "the resume guard's expression")[0]
    resume_bytes = int(resume["a"]) * int(resume["b"]) * int(resume["c"])
    assert resume_bytes != armed, (
        f"the browser's resume guard is now {resume_bytes} bytes, the same as the server's armed cap -- the two "
        f"are deliberately different limits (10 MB in the dropzone, 20 MB at the server), and a gate that "
        f"charged them one number would hide the difference the operator-facing docs describe")

    assert not NO_HANDLER.search(read(GEH)), (
        "GlobalExceptionHandler now maps a multipart-size exception, so an over-container-cap upload is answered "
        "as FILE_TOO_LARGE instead of by the catch-all: the statement that the validator's refusal has no "
        "multipart carrier has to be re-measured")
    assert "rather than through a presigned URL" in read(RESUME_CTRL), (
        "ResumeController's comment no longer states that files are served user-scoped instead of by a presigned "
        "URL -- that sentence is the code's own testimony that the presigned port is unrouted, and DEAD_KNOBS "
        "quotes it")


def test_thirty_two_leaves_reach_the_environment_and_the_three_that_do_not_are_literals_in_a_file():
    leaves = app_leaves()
    interpolated, literal = {}, {}
    for key, value in leaves.items():
        match = ENV_INTERP.match(value)
        (interpolated if match else literal)[key] = (match["var"] if match else value)
    assert len(interpolated) == 32 and len(literal) == 3, (
        f"{len(interpolated)} of the thirty-five leaves interpolate an `${{ENV}}` and {len(literal)} are literals; "
        f"the split is what makes a knob deployable, so a pair that moved needs this carrier list rewritten")
    assert frozenset(literal) == FILE_ONLY_LEAVES, (
        f"the file-only leaves are {sorted(literal)}: ratelimit.enabled is a shipped default an operator edits in "
        f"the yml and the two upload knobs are read by nobody, so each literal is a decision this gate names")

    dev, prod = read(ENV_DEV), read(ENV_PROD)
    missing_dev = sorted(v for v in interpolated.values() if v and not re.search(rf"^[#]?\s*{v}=", dev, re.M))
    assert frozenset(missing_dev) == DOC_NAMED_VARS, (
        f"these variables the yml interpolates are named nowhere in .env.example: {missing_dev}, while the "
        f"ledger excuses exactly {sorted(DOC_NAMED_VARS)} -- either an operator reading the dev example cannot "
        f"learn the knob exists, or a var joined the example and the exception is now stale")
    for var in sorted(missing_dev):
        assert var in read(DEPLOYMENT_DOC), (
            f"{var} is excused from .env.example by DOC_NAMED_VARS but docs/DEPLOYMENT.md never names it, so "
            f"the exception excuses a knob documented nowhere an operator looks")
    missing_prod = sorted(v for v in interpolated.values() if v and not re.search(rf"^[#]?\s*{v}=", prod, re.M))
    assert frozenset(missing_prod) == PROD_CREDENTIAL_VARS | DOC_NAMED_VARS, (
        f".env.prod.example omits {missing_prod}; only the MinIO credential pair (re-armed by the prod compose "
        f"from the MinIO root pair) and the deployment decisions in DOC_NAMED_VARS may be absent -- any other "
        f"omission is a knob prod never sets")
    armed_by_compose = {m["var"]: m["from"] for m in COMPOSE_ENV.finditer(read(COMPOSE_PROD))}
    assert armed_by_compose == {"MINIO_ACCESS_KEY": "MINIO_ROOT_USER", "MINIO_SECRET_KEY": "MINIO_ROOT_PASSWORD"}, (
        f"docker-compose.prod.yml arms the credential pair as {armed_by_compose}; without both mappings the "
        f"backend signs in to production MinIO with the dev defaults application.yml interpolates")

    for key in sorted(DEAD_KNOBS):
        tail = re.sub(r"[^A-Z0-9]", "_", key.split(".", 1)[1].upper())
        carriers = sorted({m["var"] for text in (dev, prod) for m in ENV_NAME.finditer(text)
                           if tail in m["var"]})
        assert not carriers, (
            f"an env example now names {carriers} for {key}, a leaf read by nobody -- the promise would be that "
            f"an operator can set a value no code consults, so give it a reader or take the carrier out. The "
            f"carrier is charged by the key's own words ({tail}), so any prefix spelling counts, not one guess")

    values = value_bindings()
    email_path, email_default = values[EMAIL_KEY]
    assert email_default == "false", (
        f"`app.email.console.log-body` now defaults to {email_default!r} in {rel(email_path)}; the shipped yml "
        f"writes no key for it, so this placeholder default is the only value a fresh install gets")
    assert "APP_EMAIL_CONSOLE_LOGBODY" in read(API_DOC), (
        "docs/API.md no longer names APP_EMAIL_CONSOLE_LOGBODY, the env spelling by which the one key reachable "
        "from the environment yet written in no shipped yml actually gets set")
    assert not re.search(r"^[#]?\s*APP_EMAIL_CONSOLE_LOGBODY=", dev, re.M), (
        ".env.example now advertises APP_EMAIL_CONSOLE_LOGBODY; either application.yml should write the key too, "
        "or the asymmetry this case pins -- a knob the environment can set that no shipped file declares -- ends")


def test_the_open_scan_charges_an_app_dot_mention_to_the_config_namespace_only_when_the_segment_is_a_holder():
    rows = prop_rows()
    mention_files = len({p for p, _, _, _ in rows})
    assert mention_files >= MIN_MENTION_FILES, (
        f"only {mention_files} files mention an `app.x.y` shape, below {MIN_MENTION_FILES}: a census over that "
        f"many rows cannot claim the configuration namespace has no other carrier")
    scanned = len(walk_repo())
    assert scanned >= MIN_SCANNED_FILES, (
        f"the walk covered {scanned} files, below the {MIN_SCANNED_FILES} of this repository -- the split below "
        f"would be a reading of a subtree, not of the project")
    assert len(rows) >= MIN_PROP_ROWS, (
        f"the census read {len(rows)} rows, below {MIN_PROP_ROWS}: the scan stopped matching the shape, so "
        f"'nothing else carries a key' would be vacuous")

    admitted = [r for r in rows if r[3]]
    refused = [r for r in rows if not r[3]]
    assert len(admitted) >= MIN_ADMITTED_ROWS and len(refused) >= MIN_REFUSED_ROWS, (
        f"the split is {len(admitted)} admitted against {len(refused)} refused; both populations have to be "
        f"present before the rule can be credited with separating them")
    keys = {r[2] for r in admitted}
    allowed = frozenset(APP_LEAVES) | {EMAIL_KEY, "email.console", "email.smtp", "storage.enabled"}
    assert keys <= allowed, (
        f"admitted rows name keys outside the pinned leaves plus the env-only email key, the mail holder's "
        f"segment and the condition's storage.enabled: {sorted(keys - allowed)} -- either a new key needs a "
        f"binder above, or the holder rule let a module path through")
    # charged against the LEDGER, not against the rule's own predicate: comparing a refusal to the same
    # membership test that produced it is a belt that cannot fail, and a renamed holder would slip through
    # while the census still printed green.
    leaked = sorted({r[2] for r in refused if r[2] in allowed})
    assert not leaked, (
        f"these rows were refused although their key is one of this gate's own config ledger: {leaked} -- the "
        f"admission rule is the census's only defence against a hidden carrier, and a refused ledger key is "
        f"exactly one")
    refused_keys = {r[2] for r in refused}
    assert {"core.skills", "eval.run_eval", "providers.base"} <= refused_keys, (
        f"the refused population no longer contains the Python module spellings that motivated the rule (its "
        f"first six are {sorted(refused_keys)[:6]}) -- if they moved, the rule is guarding an empty set")
    presigned = [r for r in admitted if "presigned" in r[2]]
    assert not presigned, (
        f"`app.upload.presigned-url-ttl-seconds` is now spelled where the walk reads it: {[(rel(p), n) for p, n, _, _ in presigned]} "
        f"-- DEAD_KNOBS says the TTL names an unrouted duration, so a fourth mention needs its own verdict")
    storage_enabled = [r for r in admitted if r[2] == "storage.enabled"]
    # 31.9 added the fourth: ProductionGuardTest turns the store off with every other
    # credential real and asserts the guard still names the MinIO pair, because four
    # services inject a StorageService and a prod boot cannot use the switch to dodge
    # the check. The three integration-test carriers are unchanged.
    assert len(storage_enabled) == 4, (
        f"`app.storage.enabled` is written down in {len(storage_enabled)} flat rows, want the 4 judged "
        f"here -- the annotation's split spelling (prefix + name) is read by another scanner, so a fifth "
        f"row means the key is now also spelled in a place this census has not judged")
