"""Per-read-site liveness: every key a browser mapper tries off a Java record's answer.

`test_response_shape_contract.py` checks the DTO-backed readers coarsely -- "at least one of the
names this function mentions is a component of the record". That survives the mistake that matters
least (a record renamed or moved, which the coarse assertion names loudly) and not the one that
matters most (a field renamed inside a record nobody renames): `ApplicationItem` renaming `notes`
would leave every other name in the function alive, so the coarse gate stays green while the
pipeline card loses its note forever. TypeScript cannot see it either, because the wire shape is
typed by hand in `types.ts` rather than derived from the record.

So the rule here is per call site, and per map. A site is one accessor call -- `str(raw, "a", "b")`
-- and it is live when at least one name it tries is a component of the record that produced the
object it reads from. A site with no live name can only ever answer with its fallback value, which
renders as a blank, a zero or `undefined`, never as an error.

Which record a site reads against is decided by its receiver, so a reader that drills a nested map
gets that map's own record instead of having its reads merged into the parent's -- the mixing the
coarse gate warns about. The links (receiver -> record, and how the local was obtained) are the
only hand-authored part; both sides come from sources, and a receiver the table does not know is an
error rather than a skip.

`@JsonAlias` does not help on this direction: it steers deserialisation only, and the backend has no
snake_case naming strategy, so a `company_name` candidate against a record is dead weight that a
live sibling in the same list saves. Only a site with *no* live name is a defect, and those are a
declared, shrink-only list.
"""

import re
from functools import lru_cache

from tests.test_response_shape_contract import NORMALIZE, _record_components_at

RECORDS = {
    "ApplicationItem": ("ApplicationItem", "application/dto/ApplicationDtos.java"),
    "CompanyItem": ("CompanyItem", "job/dto/JobDtos.java"),
    "MessageItem": ("MessageItem", "conversation/dto/ConversationDtos.java"),
}

# Readers whose producer is exactly one record per map. A reader with several producers --
# `normalizeJob` answers for JobListItem, JobDetail and SavedJobItem -- is deliberately absent:
# one record cannot answer for all of them, and naming one would redden on the truth.
#
#   record_of  receiver -> record it is read against
#   drilled    local -> (parent receiver, key drilled out of it)
#   elements   local -> parent receiver, when it is a `.map((local, i) …)` element
#   blind      receiver -> why no record can answer for it
READERS: dict[str, dict] = {
    "normalizeApplication": {
        "record_of": {"raw": "ApplicationItem", "nested": "CompanyItem"},
        "drilled": {"nested": ("raw", "company")},
        "elements": {},
        "blind": {},
    },
    "normalizeMessages": {
        "record_of": {"m": "MessageItem"},
        "drilled": {},
        "elements": {"m": "raw"},
        "blind": {"raw": "the list response envelope: `list(raw, \"messages\", …)` reads a page "
                          "wrapper built by the controller, not a record's fields"},
    },
}

# Sites that answer from their fallback on every response, declared rather than denied.
DEAD_SITES = {
    ("normalizeApplication", ("matchScore", "match_score")):
        "ApplicationItem has matchId but no score column, and no page renders one today; the "
        "frontend's own test pins `matchScore` to null so the reader cannot invent a zero",
}

# Drills whose key is not a component of the parent record, so the local can only ever be `{}`.
# Declared with the shape that would fill it in: `normalizeJob` guarantees `company` on a job and
# `ApplicationItem` does not, and a reader that copies that shape gets a logo no application
# response can supply.
HOLLOW_DRILLS = {
    ("normalizeApplication", "nested", "company"):
        "ApplicationItem names the company in flat columns (companyId + companyName) and never "
        "sends a nested object; the reader's own doc comment says so, and it projects the flat "
        "name into `company` because the row renders `app.company?.name`",
}

_ACCESSORS = r"\b(?:str|strOr|num|bool|list|pick|rec|int|pct)\(\s*"
_ID_OF = r"\bidOf\(\s*"


@lru_cache(maxsize=None)
def _body(function_name: str) -> str:
    source = NORMALIZE.read_text(encoding="utf-8")
    opener = f"export function {function_name}("
    if opener not in source:
        raise AssertionError(
            f"{opener!r} is gone from normalize.ts: the table names a reader that moved, "
            "so this rule compares nothing")
    start = source.index(opener)
    return source[start:source.index("\n}\n", start)]


@lru_cache(maxsize=None)
def _id_of_keys() -> set[str]:
    """The names `idOf` reaches for, read out of its own body rather than copied here."""
    source = NORMALIZE.read_text(encoding="utf-8")
    start = source.index("export function idOf(")
    body = source[start:source.index("\n}\n", start)]
    return {key for group in re.findall(r'\(\s*raw\s*,([^)]*)\)', body)
            for key in re.findall(r'"([^"]+)"', group)}


def _sites(function_name: str) -> list[dict]:
    """Each accessor call: the variable it reads off, the names it tries, and where it sits."""
    body = _body(function_name)
    sites = []
    for pattern, keys in ((_ACCESSORS + r"([A-Za-z_$][\w$.]*)\s*,([^)]*)\)", None),
                          (_ID_OF + r"([A-Za-z_$][\w$.]*)\s*,", _id_of_keys())):
        for match in re.finditer(pattern, body):
            receiver = match.group(1)
            candidates = sorted(keys) if keys else re.findall(r'"([^"]+)"', match.group(2))
            if not candidates:
                continue  # an accessor with no name to try is not a read of a key
            line = body.count("\n", 0, match.start()) + 1
            sites.append({"receiver": receiver, "keys": tuple(candidates), "line": line,
                          "text": match.group(0).replace("\n", " ")[:90]})
    return sites


def _emitted(alias: str) -> set[str]:
    record, path = RECORDS[alias]
    return _record_components_at(path, record)


def _undeclared_receivers(reader: str) -> list[str]:
    """Receivers the reader reads from that no record answers for, and vice versa."""
    spec = READERS[reader]
    problems = []
    used = {site["receiver"] for site in _sites(reader)}
    known = set(spec["record_of"]) | set(spec["blind"])
    for receiver in sorted(used - known):
        lines = [s["line"] for s in _sites(reader) if s["receiver"] == receiver]
        problems.append(f"{reader}: no record is bound for the receiver {receiver!r} read at "
                        f"L{lines}, while {sorted(known)} are the ones this gate knows")
    for receiver in sorted(known - used):
        if not re.search(rf"\b{re.escape(receiver)}\b", _body(reader)):
            problems.append(f"{reader}: {receiver!r} is bound to a record and appears nowhere in "
                            "the reader -- the table links a name that moved")
        else:
            problems.append(f"{reader}: {receiver!r} is bound to a record no site reads from any "
                            "more -- a renamed local silently unchecks that record")
    for receiver in sorted(set(spec["record_of"]) & set(spec["blind"])):
        problems.append(f"{reader}: {receiver!r} is both bound to a record and declared blind")
    return problems


def _broken_links(reader: str) -> list[str]:
    """The hand-authored links, checked against the code they claim to describe."""
    spec, body = READERS[reader], _body(reader)
    problems = []
    for local, (parent, key) in spec["drilled"].items():
        bound = re.search(rf"const\s+{re.escape(local)}\s*=\s*[^;\n]*\(\s*{re.escape(parent)}\s*,"
                          rf"\s*(?:[\w$]+\s*,\s*)?" r'"([^"]+)"', body)
        if bound is None:
            problems.append(f"{reader}: {local!r} is declared as drilled out of {parent!r} but "
                            "nothing binds it that way")
            continue
        if bound.group(1) != key:
            problems.append(f"{reader}: {local!r} is drilled from {parent!r} under "
                            f"{bound.group(1)!r}, which the table calls {key!r}")
    for local, parent in spec["elements"].items():
        if not re.search(rf"\.map\(\s*\(?\s*{re.escape(local)}\b", body):
            problems.append(f"{reader}: {local!r} is declared as an element of {parent!r}'s list "
                            "but is not a `.map` callback parameter")
        if parent not in set(spec["record_of"]) | set(spec["blind"]):
            problems.append(f"{reader}: {local!r} comes from {parent!r}, which the table neither "
                            "binds nor declares blind")
    return problems


def _structural_problems() -> list[str]:
    """Everything wrong with the table itself, which would make the liveness rule check less than
    it claims rather than make it red."""
    return [p for reader in READERS for p in (*_undeclared_receivers(reader), *_broken_links(reader))]


def _hollow_drills() -> set[tuple]:
    """(reader, local, key) where the local is drilled out of a record that lacks that key: the
    map can only ever be `{}`, so every read that goes through it answers from its fallback.
    Declared once per drill rather than per site, because the site names are fine -- the map is not."""
    out = set()
    for reader, spec in READERS.items():
        for local, (parent, key) in spec["drilled"].items():
            if parent in spec["record_of"] and key not in _emitted(spec["record_of"][parent]):
                out.add((reader, local, key))
    return out


def _dead_read_sites() -> list[dict]:
    """Sites whose every candidate name is absent from the record behind their receiver."""
    out = []
    for reader, spec in READERS.items():
        hollow = {local for (r, local, _) in _hollow_drills() if r == reader}
        for site in _sites(reader):
            receiver = site["receiver"]
            if receiver not in spec["record_of"]:
                continue  # unbound or blind: the structural rule has already named it
            if receiver in hollow:
                continue
            if not set(site["keys"]) & _emitted(spec["record_of"][receiver]):
                out.append(dict(site, reader=reader))
    return out


# -------------------------------------------------------------- the reconciliations

def _keyed(sites: list[dict]) -> set[tuple]:
    return {(site["reader"], site["keys"]) for site in sites}


def test_every_read_site_hits_a_field_the_record_emits():
    """A site with no live name is a field the UI shows empty forever: `num` falls back to null,
    `str` to nothing, and no layer between the record and the component can tell the difference."""
    found = _keyed(_dead_read_sites()) - set(DEAD_SITES)
    assert found == set(), ("no record answers these reads: "
                            f"{[f'{reader} {list(keys)}' for reader, keys in sorted(found)]}")


def test_the_readers_this_gate_binds_are_the_ones_that_exist():
    """The table's own bookkeeping: an unbound receiver, a local that moved, or a declared
    receiver nothing reads from any more each mean the gate checks less than it claims."""
    assert _structural_problems() == []


def test_the_dead_reads_stay_declared():
    """Shrink-only, with a reason each: a new one is a field the browser cannot get, and an old
    one that came alive should leave this list rather than sit here as free tolerance."""
    found = _keyed(_dead_read_sites())
    assert found == set(DEAD_SITES), f"off the list: {sorted(found ^ set(DEAD_SITES))}"
    assert _hollow_drills() == set(HOLLOW_DRILLS), \
        f"off the list: {sorted(_hollow_drills() ^ set(HOLLOW_DRILLS))}"
    for key, why in (*DEAD_SITES.items(), *HOLLOW_DRILLS.items()):
        assert len(why) > 40, f"{key} needs a reason a reader can act on, not a label"


def test_the_reads_are_actually_found():
    """Positive control: every rule above is satisfied by an empty reading, so the census itself is
    pinned -- real sites, at the receivers this gate claims to bind, against real components."""
    applications = _sites("normalizeApplication")
    assert len(applications) == 15
    assert {s["receiver"] for s in applications} == {"raw", "nested"}
    assert sum(1 for s in applications if s["receiver"] == "nested") == 3
    messages = _sites("normalizeMessages")
    assert len(messages) == 8
    assert {s["receiver"] for s in messages} == {"m", "raw"}
    assert len(_emitted("ApplicationItem")) == 15
    assert len(_emitted("CompanyItem")) == 9
    assert len(_emitted("MessageItem")) == 8
    assert _id_of_keys() == {"_id", "eventId", "event_id", "id", "key", "uuid"}
    assert len(_dead_read_sites()) == 1
    assert {s["line"] for s in _dead_read_sites()} == {19}
    assert _structural_problems() == []
