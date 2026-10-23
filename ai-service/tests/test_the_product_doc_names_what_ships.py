"""PRODUCT.md's feature inventory names routes and endpoints that exist, and its
counts are the populations they measure.

The inventory table is the document's central claim: thirteen rows, each saying "this
capability is shipped, here is the route that exposes it, here is the API behind it".
Nothing else in the repo checks that claim, and it is exactly the kind that rots
quietly -- a route gets renamed in `frontend/src/app` and the table keeps advertising
the old path, or an endpoint moves controller and the row still points where it used
to. A reader planning work from this table would plan against a product that no longer
exists.

The counts drift the same way, and already had. The table's own neighbours claimed
"passes 17/17" for a suite that had grown to twenty cases (the pagination spec's two
arrived without anyone touching the doc), and "embedded all 46 roles" for a seed that
has held 41 roles since the day it was written -- the 46 counted the importer's rows in
one developer's local database, which is not a number this repository can substantiate.

So the table is read as a set of claims and each one is checked against the thing that
would have to honour it. Routes are matched against the `page.tsx` files under
`frontend/src/app` (route groups like `(app)` stripped, since they are not part of the
URL). APIs are matched against the controller mappings under
`backend/src/main/java`, `/api/v1` dropped from both sides because the doc writes the
short form, `{id}` folded to `{}` so a parameter rename is not a break, and a trailing
`/*` read as "some route lives under this prefix" rather than as a literal.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
DOC = ROOT / "docs" / "PRODUCT.md"
E2E_README = ROOT / "e2e" / "README.md"
README = ROOT / "README.md"
APP = ROOT / "frontend" / "src" / "app"
JAVA = ROOT / "backend" / "src" / "main" / "java"
SEED = ROOT / "scripts" / "seed" / "01_jobs.sql"

PREFIX = "/api/v1"
SPECS = ROOT / "e2e" / "tests"

MINIMUM_ROWS = 12
# a count written as a ratio, the spelling that can be either a claim about today's suite
# ("passes 65/65") or a record of one run ("65/65 (2026-10-24, ...)"), and the size spelling
# the gated sentence under "Run" owns.
RATIO = re.compile(r"\b(?P<said>\d{1,3})\s*/\s*(?P<total>\d{1,3})\b")
DATED = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
PASSED = re.compile(r"\b\d+ passed\b")
COUNT_DOCS = (DOC, E2E_README, README)


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def norm(path: str) -> str:
    """One spelling for a path parameter or a trailing wildcard."""
    return re.sub(r"\{[^}]*\}|\*\*", "{}", path)


# --------------------------------------------------------------------------- routes


def frontend_routes() -> set[str]:
    """Every URL the frontend answers, derived from where its pages live."""
    out = set()
    for page in APP.rglob("page.tsx"):
        rel = page.relative_to(APP).parent.as_posix()
        parts = [
            p
            for p in rel.split("/")
            if p and not (p.startswith("(") and p.endswith(")"))
        ]
        out.add("/" + "/".join(parts) if parts else "/")
    return out


def backend_routes() -> set[str]:
    """Every route a backend controller mounts, as the doc spells them."""
    out = set()
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
            route = (base + sub).replace("//", "/")
            out.add(route[len(PREFIX) :] if route.startswith(PREFIX) else route)
    return {norm(route) for route in out}


def inventory_rows() -> list[tuple[str, str]]:
    """The `| capability | routes | apis |` rows of the feature inventory."""
    rows = []
    for line in read(DOC).split("\n"):
        if (
            not line.startswith("| ")
            or line.startswith("| ---")
            or line.startswith("| Capability")
        ):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3:
            rows.append((cells[1], cells[2]))
    return rows


def backticked(cell: str) -> list[str]:
    return re.findall(r"`([^`]+)`", cell)


# --------------------------------------------------------------------------- counts


def e2e_case_count() -> int:
    """How many cases the Playwright suite actually contains."""
    total = 0
    for spec in sorted(SPECS.glob("*.spec.ts")):
        total += len(re.findall(r"(?m)^\s*test\(", read(spec)))
    return total


def seed_population() -> tuple[int, int]:
    """(companies, roles) the seed script inserts, counted at paren depth one."""
    text = read(SEED)

    def statement(table: str) -> str:
        at = text.index(f"INSERT INTO {table} ")
        depth = 0
        for index in range(at, len(text)):
            if text[index] == "(":
                depth += 1
            elif text[index] == ")":
                depth -= 1
            elif text[index] == ";" and depth == 0:
                return text[at:index]
        raise AssertionError(f"the seed has no terminated INSERT INTO {table}")

    def tuples(stmt: str) -> int:
        """Rows in a VALUES list: depth-one opens, stopping where the list stops.

        The stop matters. The companies statement ends `ON CONFLICT (id) DO NOTHING`
        and the jobs one ends `) AS v(...) JOIN companies c ON ...`, and both of those
        carry parens that are not rows -- counting them inflates the census by one and
        by one is exactly the kind of error a census cannot afford.
        """
        body = stmt[stmt.index("VALUES") + len("VALUES") :]
        depth = count = 0
        for index, char in enumerate(body):
            if char == "(":
                depth += 1
                if depth == 1:
                    count += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and not body[index + 1 :].lstrip().startswith(","):
                    break
        return count

    return tuples(statement("companies")), tuples(statement("jobs"))


# ----------------------------------------------------------------------------- tests


def test_every_route_the_inventory_names_has_a_page():
    routes = frontend_routes()
    missing = sorted(
        {
            route
            for cell, _ in inventory_rows()
            for route in backticked(cell)
            if route.startswith("/")
        }
        - routes
    )
    assert missing == [], (
        f"PRODUCT.md's inventory names routes with no page under frontend/src/app: {missing}"
    )


def test_every_api_the_inventory_names_is_served():
    served = backend_routes()
    phantom = []
    for _, cell in inventory_rows():
        for token in backticked(cell):
            if not token.startswith("/"):
                continue
            if token.endswith("/*"):
                prefix = norm(token[:-1])
                if not any(route.startswith(prefix) for route in served):
                    phantom.append(token)
            elif norm(token) not in served:
                phantom.append(token)
    assert phantom == [], (
        f"PRODUCT.md's inventory names APIs no controller serves: {sorted(set(phantom))}"
    )


def test_the_inventory_names_a_population_rather_than_a_short_list():
    """Positive control: enough rows and spellings that a match cannot be an accident."""
    rows = inventory_rows()
    assert len(rows) >= MINIMUM_ROWS, f"only {len(rows)} inventory rows parsed"
    assert (
        len({r for cell, _ in rows for r in backticked(cell) if r.startswith("/")})
        >= 12
    )
    assert (
        len({a for _, cell in rows for a in backticked(cell) if a.startswith("/")})
        >= 12
    )


def stated_e2e_counts() -> dict[str, tuple[int, int]]:
    """Every place a document states how many Playwright cases the suite holds.

    Two documents carry the number, and they drift independently: PRODUCT.md says
    "passes N/N" and e2e/README.md says "N passed". Both are the same claim about the
    same files, so both are read here -- a gate over one of them just relocates the
    drift instead of closing it.
    """
    product = re.search(r"passes (\d+)/(\d+)", read(DOC))
    assert product, "PRODUCT.md no longer states how many Playwright cases pass"
    runner = re.search(r"(\d+) passed", read(E2E_README))
    assert runner, "e2e/README.md no longer states how many cases the suite runs"
    return {
        "PRODUCT.md": (int(product.group(1)), int(product.group(2))),
        "e2e/README.md": (int(runner.group(1)), int(runner.group(1))),
    }


def ratio_rows() -> list[tuple[str, int, str, int, int, bool]]:
    """(document, line, the line as written, said, total, dated) for every `N/N` the docs carry."""
    rows: list[tuple[str, int, str, int, int, bool]] = []
    for doc in COUNT_DOCS:
        for number, line in enumerate(read(doc).splitlines(), start=1):
            for match in RATIO.finditer(line):
                rows.append((str(doc.relative_to(ROOT)).replace("\\", "/"), number,
                             line.strip(), int(match["said"]), int(match["total"]),
                             bool(DATED.search(line))))
    return rows


def test_the_e2e_count_is_the_suite_that_runs():
    actual = e2e_case_count()
    for name, (said, total) in stated_e2e_counts().items():
        assert said == total == actual, (
            f"{name} says the suite passes {said}/{total} but e2e/tests holds {actual} "
            f"cases -- whoever adds a case updates the sentence, and a case that stops "
            f"passing is not a documentation problem"
        )


def test_every_count_is_either_the_gated_size_or_a_dated_record():
    """A number is graded when it claims today's suite; a run's own record only has to date itself.

    This case used to forbid the `N/N` shape anywhere outside PRODUCT.md, because a second copy of
    "17/17 against the host-frontend stack" sat in the README and went stale the moment the suite grew.
    A shape ban cannot tell that stale copy from `65/65 (2026-10-24, all three images rebuilt ...)`,
    which is a dated record of one verification run and true no matter how far the suite grows -- so
    the README's verification note went red for naming the date it ran on.

    The distinction worth gating is whether a reader can tell which run a number describes. Undated, it
    is a claim about the current suite and it is graded against `e2e/tests` like the size sentence is.
    Dated, it is a record, and what it owes the reader is internal honesty: a line that says it verified
    cannot report 60 of 65. Either way the number has an author; nothing is excused by being unlookupable.
    """
    actual = e2e_case_count()
    rows = ratio_rows()
    graded = [row for row in rows if not row[5]]
    records = [row for row in rows if row[5]]
    assert rows and graded and records, (
        f"{len(rows)} counts, {len(graded)} undated, {len(records)} dated: the two directions this case "
        "gates each need a carrier, or a green here means the documents stopped stating counts at all "
        "and the rule has nothing left to decide")

    for where, number, line, said, total, _ in graded:
        assert (said, total) == (actual, actual), (
            f"{where}:{number} states {said}/{total} with no date, so a reader cannot tell it apart from "
            f"the suite's current size, which is {actual} -- update the sentence or put the run's date on "
            f"it ({line[:70]}!)")
    for where, number, line, said, total, _ in records:
        assert said == total, (
            f"{where}:{number} reports {said}/{total} as a dated record: a line that names the day it "
            f"ran is telling the reader what that run proved, and a run that did not pass its whole "
            f"suite is not a verification ({line[:70]}!)")

    found = PASSED.findall(read(E2E_README))
    assert len(found) == 1, (
        f"e2e/README.md carries {found}: the suite's size is stated once, under \"Run\", and "
        "`test_the_e2e_count_is_the_suite_that_runs` is what grades that one")
    # `stated_e2e_counts()` reads the one PRODUCT.md sentence it can find, so a second undated
    # count in that document is a claim nothing grades -- and a reader cannot tell which one the
    # suite grew past.
    product_claims = [row for row in ratio_rows() if row[0] == "docs/PRODUCT.md" and not row[5]]
    assert len(product_claims) == 1, (
        f"{[(r[1], r[2][:40]) for r in product_claims]}: PRODUCT.md's `passes N/N` is the claim "
        "`stated_e2e_counts()` grades, and it grades the first one it finds")


def test_the_seeded_corpus_is_the_corpus_in_the_seed_script():
    companies, roles = seed_population()
    text = read(DOC)
    corpus = re.search(r"(\d+)-company / (\d+)-role corpus", text)
    assert corpus, "PRODUCT.md no longer states the seeded corpus size"
    assert (int(corpus.group(1)), int(corpus.group(2))) == (companies, roles), (
        f"PRODUCT.md calls the corpus {corpus.group(1)} companies / {corpus.group(2)} roles "
        f"but scripts/seed/01_jobs.sql inserts {companies} / {roles}"
    )
    embedded = re.search(r"embedded all (\d+) roles", text)
    assert embedded, "PRODUCT.md no longer states how many roles were embedded"
    assert int(embedded.group(1)) == roles, (
        f"PRODUCT.md says {embedded.group(1)} roles were embedded and the seed holds {roles} "
        f"-- the larger number was somebody's local database, not this repository"
    )


def test_the_readmes_agree_with_the_seed_script():
    companies, roles = seed_population()
    for doc in (README, E2E_README):
        found = re.search(r"(\d+) compan\w* / (\d+) role", read(doc))
        assert found, f"{doc.name} no longer states the seed corpus size"
        assert (int(found.group(1)), int(found.group(2))) == (companies, roles), (
            f"{doc.name} says {found.group(1)} companies / {found.group(2)} roles but "
            f"scripts/seed/01_jobs.sql inserts {companies} / {roles}"
        )
