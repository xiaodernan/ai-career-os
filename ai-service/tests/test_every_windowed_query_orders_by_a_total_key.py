"""Every windowed query orders by a total key, so a page is a partition.

#227 found the companies board paging `findAll(pageable)` with no ORDER BY at all, and #229/#230
found the job board ordering by keys that tie. This is the same defect read over every repository
in the backend at once, because "the list happens to come back in a stable order" is not a
property anybody can rely on: two rows that tie on the visible key are separated by whichever plan
PostgreSQL picked, so the same URL answers different rows on two visits, and a row can be served
by two pages or by none.

The rule this file holds is one line: **the last key of a windowed query's ORDER BY is a column the
schema declares unique.** Every entity here has one -- its primary key -- so in practice the rule
reads "every ordering ends in the id", and the only exception is the companies board, whose name is
unique and whose visible order is the alphabet (#227).

The population is every repository method that takes a `Pageable`: a `Page<...>` return is a paged
board, and a `List<...>` return with a `Pageable` parameter is a capped preview, which has the same
boundary decision to make. One method is pinned as an exception rather than fixed --
`ApplicationEventRepository.findByUserIdOrderByCreatedAtDesc`, the dashboard's five-row activity
preview -- because its only caller lives in a file another unit is editing; the exception is a
measurement, not a permission, and it names the reason.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
JAVA = ROOT / "backend" / "src" / "main" / "java"

# method name -> the unique column its ordering ends in. Everything else must end in the id.
UNIQUE_BY_METHOD = {
    "findAllByOrderByNameAsc": "name",
    "findByNameContainingIgnoreCaseOrderByNameAsc": "name",
}

# Windowed queries whose order still ties, with the reason each is still here.
EXEMPT = {
    "findByUserIdOrderByCreatedAtDesc":
        "the dashboard's five-row activity preview; its only caller is being edited in another unit",
}

MINIMUM = 11


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def balanced(text: str, open_at: int, opener: str, closer: str) -> int:
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"no matching {closer!r} after offset {open_at}")


def repositories() -> list[Path]:
    return sorted(p for p in JAVA.rglob("*Repository.java") if "package" in read(p))


def methods(text: str) -> list[tuple[str, str, str]]:
    """(name, parameter list, the @Query annotation or "") for every declared method."""
    out = []
    for match in re.finditer(r"^\s+(?:public\s+)?(?:Page|List)<[\w<>,\s]+>\s+(\w+)\(", text, re.M):
        name = match.group(1)
        close = balanced(text, match.end() - 1, "(", ")")
        params = text[match.end():close]
        before = text[:match.start()]
        query = ""
        at = before.rfind("@Query")
        if at != -1 and ";" not in before[at:]:
            open_at = before.index("(", at)
            query = before[open_at:balanced(before, open_at, "(", ")") + 1]
        out.append((name, collapse(params), collapse(query)))
    return out


def windowed(text: str) -> list[tuple[str, str, str]]:
    """Every method that takes a `Pageable`: a paged board or a capped preview."""
    return [(name, params, query) for name, params, query in methods(text) if "Pageable" in params]


def ordering(name: str, query: str) -> list[str] | None:
    """The sort keys of a windowed query, in order, or None when it declares no order at all."""
    if "OrderBy" in name:
        tail = name.split("OrderBy", 1)[1]
        parts = [p for p in re.split(r"(Asc|Desc)", tail) if p and p not in ("Asc", "Desc")]
        return [p.lower() for p in parts]
    if query:
        found = re.search(r"ORDER BY ([^\"\']+)", query)
        if found:
            keys = []
            for term in found.group(1).split(","):
                column = term.strip().split(".")[-1].strip().lower()
                column = re.sub(r"\s+(asc|desc)$", "", column)
                if column:
                    keys.append(column)
            return keys or None
    return None

def test_every_windowed_query_declares_an_order_at_all():
    """Case 1: the population is real, and nothing in it pages unordered."""
    seen = []
    for path in repositories():
        for name, params, query in windowed(read(path)):
            seen.append(f"{path.name}#{name}")
            assert ordering(name, query) is not None, (
                f"{path.name}#{name} takes a Pageable and orders by nothing, so its window is "
                f"whatever the database felt like returning -- the shape #227 found on the "
                f"companies board")
    assert len(seen) >= MINIMUM, f"{len(seen)} windowed queries walked, pinned at least {MINIMUM}"
    assert len(seen) == len(set(seen)), f"two repositories declare the same windowed query: {seen}"


def test_every_ordering_ends_in_a_column_the_schema_declares_unique():
    """Case 2: the last sort key is unique, so no two rows can share a page."""
    for path in repositories():
        for name, _params, query in windowed(read(path)):
            keys = ordering(name, query)
            assert keys, f"{path.name}#{name} has no order to end"
            last = keys[-1]
            expected = UNIQUE_BY_METHOD.get(name, "id")
            if name in EXEMPT:
                assert last != expected, (
                    f"{name} is on the exemption list but orders by {last!r} already, so the "
                    f"exemption is stale and its reason no longer applies: {EXEMPT[name]}")
                continue
            assert last == expected, (
                f"{path.name}#{name} orders by {keys}, so its last key is {last!r} where the "
                f"unique column is {expected!r}: two rows the earlier keys call equal are then "
                f"separated by the plan, and the same URL answers different rows on two visits")


def test_the_one_known_tie_is_pinned_with_its_reason():
    """Case 3: the exemption is a measurement with an owner, not a silent hole."""
    found = {name for path in repositories() for name, _p, _q in windowed(read(path))}
    for name, reason in EXEMPT.items():
        assert name in found, f"{name} is exempt but no repository declares it any more"
        assert reason and "unit" in reason, f"the exemption for {name} no longer says who owns it"
    assert set(EXEMPT) <= found, "an exemption names a query that does not exist"
    assert len(found - set(EXEMPT) - set(UNIQUE_BY_METHOD)) == len(found) - len(EXEMPT) - len(UNIQUE_BY_METHOD)
