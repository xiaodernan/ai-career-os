"""API.md §2's endpoint tables are the controllers' own, in both directions.

§2 is the contract a client is written against: sixty-odd rows of method, path and what
the body takes. It is also the table most likely to rot, because every endpoint change
touches three files and only one of them is the doc. A route is renamed in a controller
and the doc keeps advertising the old path; a route is added and the doc never hears
about it; a `POST` becomes a `PUT` and the doc still says `POST`. Each of those is a
client written against a contract that was never true.

The companion gate over §3's internal surface (`test_the_backends_internal_surface_is_documented`)
proved the shape works and proved the drift is real -- that section had an entire route
missing. §2 is the same claim about a much larger surface, so it gets the same treatment.

Both directions, because either alone passes on a doc that documents nothing: a route the
controllers serve that the tables omit, and a row the tables claim that no controller
serves, both fail. Path parameters are normalised (`{id}` and Spring's `/**` both read
`{}`) so a parameter rename is not a doc break -- the row is about the route, not the
name of the variable in it.

Methods are checked where the doc states one and skipped where it does not. A few rows
cover several verbs at once (`GET / POST / PATCH / DELETE` over `/knowledge/notes` and
`/knowledge/notes/{id}`), and expanding those into a cross-product would invent
`PATCH /knowledge/notes` -- a route no controller serves and no reader expects. So a
combined row is held to its paths only, and a single-verb row is held to its verb too.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
DOC = ROOT / "docs" / "API.md"
JAVA = ROOT / "backend" / "src" / "main" / "java"

PREFIX = "/api/v1"
INTERNAL = "/api/internal"

MINIMUM_ROUTES = 60


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def norm(path: str) -> str:
    """One spelling for a path parameter or a trailing wildcard."""
    return re.sub(r"\{[^}]*\}|\*\*", "{}", path)


def controller_routes() -> set[tuple[str, str]]:
    """Every `(METHOD, path)` a backend controller mounts, as the doc spells them."""
    out: set[tuple[str, str]] = set()
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
            route = norm((base + sub).replace("//", "/"))
            if route.startswith(PREFIX):
                route = route[len(PREFIX) :]
            if not route.startswith(INTERNAL):
                out.add((match.group(1).upper(), route))
    return out


def public_section() -> str:
    text = read(DOC)
    return text[text.index("## 2. Public API") : text.index("## 3. Internal API")]


def documented_pairs() -> set[tuple[str | None, str]]:
    """`(method, path)` per table row, with `method` None where the doc names several."""
    out: set[tuple[str | None, str]] = set()
    for line in public_section().split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] == "Method" or set(cells[0]) <= {"-", " "}:
            continue
        verbs = re.findall(r"\b(GET|POST|PUT|PATCH|DELETE)\b", cells[0])
        for path in re.findall(r"`([^`]+)`", cells[1]):
            out.add((verbs[0] if len(verbs) == 1 else None, norm(path)))
    return out


def test_every_route_the_tables_name_is_a_route_a_controller_serves():
    served = {path for _, path in controller_routes()}
    phantom = sorted({path for _, path in documented_pairs() if path not in served})
    assert phantom == [], (
        f"API.md §2 advertises routes no controller serves: {phantom} -- a client written "
        f"against this table calls paths that 404"
    )


def test_every_verb_the_tables_name_is_the_verb_the_controller_uses():
    served = controller_routes()
    wrong = []
    for method, path in sorted(
        documented_pairs(), key=lambda pair: (pair[1], str(pair[0]))
    ):
        if method and (method, path) not in served:
            actual = sorted(verb for verb, route in served if route == path)
            wrong.append(f"{method} {path} (controller: {actual or 'nothing'})")
    assert wrong == [], (
        f"API.md §2 names a verb no controller maps: {wrong} -- the row reads as a "
        f"contract and the controller disagrees with it"
    )


def test_every_route_a_controller_serves_is_named_in_the_tables():
    documented = {path for _, path in documented_pairs()}
    undocumented = sorted(
        {
            f"{method} {path}"
            for method, path in controller_routes()
            if path not in documented
        }
    )
    assert undocumented == [], (
        f"the backend serves public routes API.md §2 never names: {undocumented} -- the "
        f"table is the contract, and a route missing from it is a route no client knows "
        f"it may call"
    )


def test_the_tables_are_a_population_rather_than_a_short_list():
    """Positive control: enough routes that a match cannot be an accident."""
    served = controller_routes()
    assert len(served) >= MINIMUM_ROUTES, f"only {len(served)} controller routes parsed"
    assert len(documented_pairs()) >= MINIMUM_ROUTES, (
        f"only {len(documented_pairs())} documented routes parsed"
    )
    assert len({path for _, path in served}) >= 40
