"""A doc that points at a prefix or a wildcard is graded against the file that declares it.

API.md's two tables are already held to the controllers (`test_the_api_docs_public_tables_are_
the_controllers_own.py`, `test_the_backends_internal_surface_is_documented.py`). What neither
gate reads is the prose: the bullet in SECURITY.md that lists the unauthenticated routes, the
line in DEPLOYMENT.md that says where the API lives, the parenthetical in architecture.md that
names the REST prefix. Those spell a path too, in backticks, and a reader trusts them exactly
as much as a table row. `POST /api/v1/contacs` typed from a prose bullet is the same broken
client as one typed from §2.

Prose is where the hard cases live, because prose names *groups* rather than endpoints:
`/api/v1/auth/**`, `/api/internal/*`, "the public REST API under `/api/v1`". A route table
cannot answer those -- no controller's path is `/api/v1/auth/**`. The file that does answer
them is the one that *declares* the group: the `requestMatchers(...)` call that admits it, the
filter whose `startsWith(...)` decides whether it is guarded, the springdoc property that
serves the OpenAPI at it. So the carriers this gate reads are every `/api`-shaped string the
backend declares, plus the shared prefix the controllers actually live under.

The direction the tables never check is the other one, and it is the one SECURITY.md is written
for: its "Public (unauthenticated) routes" bullet is the audit answer to "what can an
anonymous caller reach". A matcher added to SecurityConfig and not written into that bullet
leaves the doc claiming a smaller anonymous surface than the deploy ships. So every
`permitAll` path the security config declares has to be named in the doc.

`/api/v1` itself is derived rather than remembered: the longest directory prefix every public
controller route shares. Rename one controller to a different version and the derived base
moves, and the doc that still says `/api/v1/*` goes red -- which is the moment the doc starts
being wrong for real.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
DOCS = ROOT / "docs"
JAVA = ROOT / "backend" / "src" / "main" / "java"
RESOURCES = ROOT / "backend" / "src" / "main" / "resources"
SECURITY_DOC = DOCS / "SECURITY.md"

INTERNAL_PREFIX = "/api/internal"

MIN_LITERALS = 25
MIN_GROUP_HITS = 4
MIN_PUBLIC_ROUTES = 40
MIN_PERMIT_ALL = 6


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def norm(path: str) -> str:
    """One spelling for a path parameter or a trailing wildcard."""
    return re.sub(r"\{[^}]*\}|\*\*", "{}", path)


def stem(path: str) -> str:
    """Drop a trailing group marker, however the doc or the guard spells it.

    Stripped before `norm`, because `**` here means "this whole group", not "one path
    segment" -- the same characters mean a wildcard to Spring's matcher and a parameter to
    the table gate.
    """
    return re.sub(r"/(?:\.\.\.|\*+)$", "", path).rstrip("/")


def controller_routes() -> set[str]:
    """Every path a backend controller mounts, base included."""
    out: set[str] = set()
    for path in sorted(JAVA.rglob("*Controller.java")):
        text = read(path)
        base = re.search(r'@RequestMapping\("([^"]+)"\)', text)
        base = base.group(1) if base else ""
        for match in re.finditer(
            r"@(Get|Post|Put|Patch|Delete)Mapping"
            r'(?:\(\s*(?:value\s*=\s*)?"([^"]*)"\s*[,)])?',
            text,
        ):
            sub = match.group(2) or ""
            out.add(norm((base + sub).replace("//", "/")))
    return out


def declared_paths() -> set[str]:
    """Every `/api`-shaped string the backend declares: matchers, guards, config values."""
    out: set[str] = set()
    for java in sorted(JAVA.rglob("*.java")):
        out.update(re.findall(r'"(/api[^"]*)"', read(java)))
    for yml in sorted(RESOURCES.glob("application*.yml")):
        out.update(re.findall(r":\s*(/api\S*)", read(yml)))
    return {norm(p) for p in out}


def public_base() -> str:
    """The longest `/`-separated prefix every public controller route shares."""
    routes = [r for r in controller_routes() if not r.startswith(INTERNAL_PREFIX)]
    assert routes, "no public controller routes parsed"
    parts = routes[0].split("/")
    for route in routes[1:]:
        other = route.split("/")
        for index in range(min(len(parts), len(other))):
            if parts[index] != other[index]:
                parts = parts[:index]
                break
        else:
            parts = parts[: min(len(parts), len(other))]
    return "/".join(parts) or "/"


def doc_literals() -> list[tuple[str, int, str]]:
    """`(file, line, literal)` for every backticked `/api...` path in the docs."""
    out = []
    for doc in sorted(DOCS.rglob("*.md")):
        text = read(doc)
        for number, line in enumerate(text.split("\n"), 1):
            for literal in re.findall(r"`(/api[^`\s|]*)`", line):
                out.append((doc.name, number, literal))
    return out


def answered(literal: str, routes: set[str], declared: set[str], base: str) -> bool:
    n = norm(literal)
    if n in routes or n in declared:
        return True
    group = norm(stem(literal))
    return group in {norm(stem(p)) for p in declared} or group == base


def permit_all_paths() -> set[str]:
    """The paths SecurityConfig admits without a validated token.

    The scan stops at the first `)`, so a matcher written with a nested call inside
    `requestMatchers(...)` would silently drop a path and the reverse clause would grade
    nothing. The floor in the test below is what notices.
    """
    configs = list(JAVA.rglob("SecurityConfig.java"))
    assert configs, "no SecurityConfig.java to read the anonymous surface from"
    text = read(configs[0])
    out: set[str] = set()
    for match in re.finditer(r"requestMatchers\(([^)]*)\)", text):
        for quoted in re.findall(r'"([^"]+)"', match.group(1)):
            if quoted.startswith(("/api", "/v3", "/swagger", "/actuator")):
                out.add(quoted)
    return out


def test_the_anonymous_surface_is_a_population_before_it_is_a_comparison():
    paths = permit_all_paths()
    assert len(paths) >= MIN_PERMIT_ALL, (
        f"only {len(paths)} anonymous matchers parsed from SecurityConfig ({sorted(paths)}); "
        f"below that the reverse clause is comparing against a truncated read"
    )


def test_every_api_path_the_docs_name_is_declared_by_the_backend():
    routes, declared, base = controller_routes(), declared_paths(), public_base()
    orphans = [
        f"{name}:{number} `{literal}`"
        for name, number, literal in doc_literals()
        if not answered(literal, routes, declared, base)
    ]
    assert orphans == [], (
        f"the docs name paths no carrier declares: {orphans} -- a reader copies a "
        f"backticked path into a client and nothing on the other end owns it"
    )


def test_the_literals_are_a_population_that_includes_the_hard_spellings():
    """Positive control: the gate is grading groups, not only exact routes.

    A doc that named only exact controller paths would pass this gate on the strength of the
    table gate alone, and the interesting half -- the wildcard, the Ant pattern, the bare
    prefix -- would never be read. So the count is pinned, and so is how many answers had to
    come from a *group* carrier rather than a route.
    """
    routes, declared = controller_routes(), declared_paths()
    literals = doc_literals()
    assert len(literals) >= MIN_LITERALS, (
        f"only {len(literals)} backticked /api paths in docs -- too few to grade anything"
    )
    group_hits = [
        literal
        for _, _, literal in literals
        if norm(literal) not in routes and norm(literal) not in declared
    ]
    assert len(group_hits) >= MIN_GROUP_HITS, (
        f"only {len(group_hits)} literals needed a group carrier (wildcard/prefix): the "
        f"declared-path half of this gate is not being read"
    )


def test_the_derived_public_base_is_not_an_accident_of_one_route():
    base = public_base()
    assert base.startswith("/api/"), f"derived base {base!r} is not an /api prefix"
    routes = controller_routes()
    sharing = sum(1 for r in routes if r.startswith(base + "/"))
    assert sharing >= MIN_PUBLIC_ROUTES, (
        f"the base {base!r} is shared by only {sharing} routes; a two-route intersection "
        f"is not the API's documented home"
    )


def test_every_route_security_admits_anonymously_is_named_in_the_security_doc():
    doc = read(SECURITY_DOC)
    missing = sorted(p for p in permit_all_paths() if p not in doc)
    assert missing == [], (
        f"SecurityConfig admits {missing} without a token and SECURITY.md never names them "
        f"-- the audit doc describes a smaller anonymous surface than the deploy ships"
    )
