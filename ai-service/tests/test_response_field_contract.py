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

The producer on the other side is not always a Java record. `normalizeMatch` reads a map the backend
hands over from the AI service -- `MatchResult.model_dump()` -- so its class body is the wire shape,
and a model is as static as a record. One local can also answer to *two* producers when the endpoint
and the persisted row disagree about where the same score lives (`MatchResult` for a fresh match,
`MatchSummary` for the stored one the job detail replays); such a receiver is bound to both, and a
site is live if either one emits a name it tries. That is weaker than one record per map, so the
weaker binding is only used where the response really has two authors.
"""

import re
from functools import lru_cache

from tests.test_response_shape_contract import (
    JAVA_ROOT,
    NORMALIZE,
    _record_components_at,
    pydantic_fields,
)

# What puts keys on the wire for one map: a Java record (path given), or a Pydantic model, whose
# annotated fields `model_dump()` emits verbatim.
PRODUCERS = {
    "ApplicationItem": ("java", "application/dto/ApplicationDtos.java"),
    "CompanyItem": ("java", "job/dto/JobDtos.java"),
    "MessageItem": ("java", "conversation/dto/ConversationDtos.java"),
    "MatchResponse": ("java", "job/dto/JobDtos.java"),
    "JobDetail": ("java", "job/dto/JobDtos.java"),
    "JobListItem": ("java", "job/dto/JobDtos.java"),
    "SavedJobItem": ("java", "job/dto/JobDtos.java"),
    "MatchSummary": ("java", "job/dto/JobDtos.java"),
    "MatchResult": ("pydantic",),
    "SearchResponse": ("java", "search/dto/SearchDtos.java"),
    "JobHit": ("java", "search/dto/SearchDtos.java"),
    "CompanyHit": ("java", "search/dto/SearchDtos.java"),
    "ResumeHit": ("java", "search/dto/SearchDtos.java"),
    "NoteHit": ("java", "search/dto/SearchDtos.java"),
    "ConversationHit": ("java", "search/dto/SearchDtos.java"),
    "ApplicationHit": ("java", "search/dto/SearchDtos.java"),
    "SkillGap": ("pydantic",),
}

# Readers whose producers are known per map. A reader with more producers than one is bound to their
# **union** -- weaker than one record per map, so it is only taken where the same mapper really is
# fed several endpoints (`normalizeJob` answers for JobListItem, JobDetail and SavedJobItem, which
# disagree about `match`/`matchOverall`/`company`), and a site then has to be missed by *every*
# author to count as dead.
#
#   record_of  receiver -> producer(s) it is read against; a list is the union of several
#   drilled    local -> (parent receiver, key drilled out of it)
#   elements   local -> parent receiver, when it is a `.map((local, i) …)` element
#   blind      receiver -> why no record can answer for it
#   dynamic    receiver -> why its names come from a variable rather than a call site, and which
#              source-derived rule checks them instead (an unexplained entry is not allowed)
READERS: dict[str, dict] = {
    "normalizeApplication": {
        "record_of": {"raw": "ApplicationItem", "nested": "CompanyItem"},
        "drilled": {"nested": ("raw", "company")},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeJob": {
        # `raw` is deliberately bound to all three job payloads: the saved-jobs list hands over a
        # SavedJobItem and the reader's first statement unwraps it (`raw = rec(pick(raw, "job", …))`),
        # so one local really does see three authors. `company` is the nested CompanyItem that only
        # JobDetail carries -- the list rows project the company through flat `companyId`/`companyName`
        # columns, which is why the reader reads both spellings.
        "record_of": {"raw": ["JobListItem", "JobDetail", "SavedJobItem"],
                      "company": "CompanyItem"},
        "drilled": {"company": ("raw", "company")},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeMessages": {
        "record_of": {"m": "MessageItem"},
        "drilled": {},
        "elements": {"m": "raw"},
        "blind": {"raw": "the list response envelope: `list(raw, \"messages\", …)` reads a page "
                          "wrapper built by the controller, not a record's fields"},
        "dynamic": {},
    },
    "normalizeMatch": {
        # `raw` is the envelope `pick(raw, "match", "latestMatch", …)` drills; the payload is the
        # union, because the score has two authors: POST /jobs/{id}/match answers with
        # `MatchResult.model_dump()` relayed through `MatchResponse`, while GET /jobs/{id} replays
        # the stored row as `MatchSummary`. Two of the five callers pre-unwrap
        # (`pick(raw, "match") ?? raw`), and one hands a copilot artifact blob -- that path reads
        # the same keys, and no site here is live only thanks to it.
        "record_of": {"raw": ["MatchResponse", "JobDetail"],
                      "m": ["MatchResult", "MatchSummary"]},
        "drilled": {"m": ("raw", "match")},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeSearch": {
        # One endpoint feeds this mapper (`GET /search` via `useGlobalSearch` and the palette), and
        # its answer is `SearchResponse`: seven flat components, six of them `List<*Hit>`. There is
        # no other shape. The reader also used to accept `{groups:[…]}` and a flat `{items:[…]}`;
        # nothing on either service emits either name for this route, so #128 deleted both paths along
        # with the two tests that fed them invented payloads -- a fallback a producer cannot reach is
        # a shape the mapper would silently reinterpret rather than a tolerance anyone needs.
        # `h` is a hit of whichever group is being rendered, which is why it is bound to the union of
        # the six records rather than to one of them: a name only `CompanyHit` carries is a real read
        # for companies and a blank for jobs, and the palette shows a blank subtitle by design.
        # `_search_hits` is what keeps that union honest rather than hand-picked.
        "record_of": {"raw": "SearchResponse",
                      "h": ["JobHit", "CompanyHit", "ResumeHit", "NoteHit",
                            "ConversationHit", "ApplicationHit"]},
        "drilled": {},
        "elements": {"h": "arr"},
        "blind": {},
        "dynamic": {
            "raw": "`const arr = list(raw, g.key)` asks for whichever list the group being rendered "
                   "names, so no literal name appears at the site; `_search_hits` ties those keys to "
                   "SearchResponse's components in both directions",
            "arr": "the per-group list itself, keyed by the same SEARCH_GROUPS variable -- it exists "
                   "to be `h`'s parent rather than to be read by name",
        },
    },
    "normalizeSkillGaps": {
        # The gap card's own reader, and the one whose ITEM shape is the contract: `g` is an item of
        # the `skillGaps` list that `arr` reads out of `raw`, and the only author of those items is
        # ai-service's SkillGap, persisted verbatim into `job_matches.skill_gaps` and projected back
        # by MatchSummary. `raw` cannot be bound: its two callers hand over two different shapes --
        # the list normalizeMatch already drilled, and a literal `{gaps: …}` the dashboard reader
        # builds from missingSkills -- so the shared name is checked where the risk actually is: on
        # the item.
        "record_of": {"g": "SkillGap"},
        "drilled": {"arr": ("raw", "skillGaps")},
        "elements": {"g": "raw"},
        "blind": {"raw": "the caller's payload, whatever shape it brings: `list(raw, \"skillGaps\", "
                         "…)` returns `raw` untouched when the caller already drilled the list, so "
                         "no single record owns the name"},
        "dynamic": {},
    },
}

# Sites that answer from their fallback on every response, declared rather than denied. The key is
# the reader plus that one call's candidate list *verbatim*, in source order -- so renaming or
# reordering the names in the reader has to come here and be thought about again.
DEAD_SITES = {
    ("normalizeApplication", ("matchScore", "match_score")):
        "ApplicationItem has matchId but no score column, and no page renders one today; the "
        "frontend's own test pins `matchScore` to null so the reader cannot invent a zero",
    ("normalizeMatch", ("jobId", "job_id")):
        "neither author carries it: job_matches has the column, but MatchSummary projects the "
        "scores and MatchResult is only what the AI service computed, so JobMatch.jobId stays "
        "undefined -- harmless, because every caller already knows the job from its own route",
    ("normalizeMatch", ("resumeVersionId", "resume_version_id")):
        "same column, same omission: jobs/[id]/page.tsx:103 sets it to null on purpose (the "
        "backend resolves the current version when the request omits it), so nothing reads it back",
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

_ACCESSORS = (r"\b(?:str|strOr|num|bool|list|pick|rec|int|pct)"
              # A typed accessor reads like any other call once the annotation is skipped:
              # `pick<Record<string, unknown>>(raw, "company")` is a read of `company`, and
              # skipping only the generic -- not the call -- is what keeps that site visible.
              r"(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?\(\s*")
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


def _search_group_keys() -> list[str]:
    """The list names `SEARCH_GROUPS` walks, read out of that table rather than repeated here."""
    source = NORMALIZE.read_text(encoding="utf-8")
    start = source.index("export const SEARCH_GROUPS")
    return re.findall(r'key:\s*"([^"]+)"', source[start:source.index("\n];", start)])


def _search_hits() -> dict[str, str]:
    """Which record answers for each group, off `SearchResponse`'s own declaration."""
    source = (JAVA_ROOT / "com" / "careeros" / "search" / "dto" / "SearchDtos.java").read_text(
        encoding="utf-8")
    head = source[source.index("record SearchResponse("):]
    body = head[:head.index(") {")]
    return {key: record for record, key in re.findall(r"List<(\w+)>\s+(\w+)", body)}


def _emitted(alias: str) -> set[str]:
    """The keys one producer puts on the wire, read from its own source either way."""
    if alias not in PRODUCERS:
        raise AssertionError(f"{alias!r} is bound to a receiver and PRODUCERS has no source for it: "
                             "the rule would compare its reads against nothing")
    spec = PRODUCERS[alias]
    if spec[0] == "java":
        return _record_components_at(spec[1], alias)
    return pydantic_fields(alias)


def _emitted_for(receiver: str | list[str]) -> set[str]:
    """What a map can hold: one producer's keys, or the union when the response has two authors.

    A union is the weaker binding -- a site survives if *either* producer emits the name -- so it
    is only taken where a real second endpoint exists, and `_emitted` keeps the per-producer count
    the positive control pins.
    """
    names = [receiver] if isinstance(receiver, str) else receiver
    if not names:
        raise AssertionError("a receiver bound to zero producers compares nothing")
    return set().union(*(_emitted(name) for name in names))


def _undeclared_receivers(reader: str) -> list[str]:
    """Receivers the reader reads from that no record answers for, and vice versa."""
    spec = READERS[reader]
    problems = []
    used = {site["receiver"] for site in _sites(reader)}
    known = set(spec["record_of"]) | set(spec["blind"]) | set(spec["dynamic"])
    for receiver in sorted(used - known):
        lines = [s["line"] for s in _sites(reader) if s["receiver"] == receiver]
        problems.append(f"{reader}: no record is bound for the receiver {receiver!r} read at "
                        f"L{lines}, while {sorted(known)} are the ones this gate knows")
    for receiver in sorted(known - used):
        if receiver in spec["dynamic"]:
            # Suppressing the complaint is allowed, vanishing with it is not: a dynamic receiver the
            # reader no longer names would leave the table excusing a local that moved.
            if not re.search(rf"\b{re.escape(receiver)}\b", _body(reader)):
                problems.append(f"{reader}: {receiver!r} is declared dynamic and appears nowhere in "
                                "the reader -- the entry excuses a name that moved")
            continue  # read under a name a variable supplies: no literal site can exist
        if not re.search(rf"\b{re.escape(receiver)}\b", _body(reader)):
            problems.append(f"{reader}: {receiver!r} is bound to a record and appears nowhere in "
                            "the reader -- the table links a name that moved")
        else:
            problems.append(f"{reader}: {receiver!r} is bound to a record no site reads from any "
                            "more -- a renamed local silently unchecks that record")
    for receiver in sorted(set(spec["record_of"]) & set(spec["blind"])):
        problems.append(f"{reader}: {receiver!r} is both bound to a record and declared blind")
    for receiver in sorted(set(spec["blind"]) & set(spec["dynamic"])):
        problems.append(f"{reader}: {receiver!r} is declared blind and dynamic at once -- the table "
                        "should say which of the two explains it")
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
        if parent not in (set(spec["record_of"]) | set(spec["blind"]) | set(spec["dynamic"])):
            problems.append(f"{reader}: {local!r} comes from {parent!r}, which the table neither "
                            "binds, declares blind, nor declares dynamic")
    return problems


def _producer_bookkeeping() -> list[str]:
    """The producer table against the reader table, both ways. A name bound to nothing, or a
    producer nothing binds, both leave a rule comparing a set nobody reads."""
    problems = []
    named = {alias for spec in READERS.values() for value in spec["record_of"].values()
             for alias in ([value] if isinstance(value, str) else value)}
    for alias in sorted(named - set(PRODUCERS)):
        problems.append(f"{alias!r} is bound to a receiver but PRODUCERS has no source for it, so "
                        "the liveness rule has nothing to compare against")
    for alias in sorted(set(PRODUCERS) - named):
        problems.append(f"{alias!r} is registered as a producer and bound to no receiver -- the "
                        "reader that used it has moved, and its reads are now unchecked")
    for alias in sorted(named & set(PRODUCERS)):
        if not _emitted(alias):
            problems.append(f"{alias} emits no keys at all: the source it names no longer has a "
                            "record or model of that shape")
    return problems


_SPEC_KEYS = {"record_of", "drilled", "elements", "blind", "dynamic"}


def _spec_shape() -> list[str]:
    """A reader that stops declaring one link stops being checked by the rule that reads it, and a
    `dynamic` entry with a one-word reason is free tolerance rather than an explanation."""
    problems = []
    for reader, spec in READERS.items():
        if set(spec) != _SPEC_KEYS:
            problems.append(f"{reader}: declares {sorted(spec)}, not the five links "
                            f"{sorted(_SPEC_KEYS)} -- a rule now has nothing to read")
        for receiver, why in spec["dynamic"].items():
            if len(why) <= 40:
                problems.append(f"{reader}: {receiver!r} is excused by {why!r}, which is a label "
                                "and not a reason the next reader can act on")
    return problems


def _structural_problems() -> list[str]:
    """Everything wrong with the table itself, which would make the liveness rule check less than
    it claims rather than make it red."""
    problems = _spec_shape()
    if problems:
        # A spec missing one of the five links makes the rules below unreadable rather than wrong,
        # so say which key vanished before anything tries to index it.
        return problems
    return [p for reader in READERS
            for p in (*_undeclared_receivers(reader), *_broken_links(reader))] + \
        _producer_bookkeeping()


def _hollow_drills() -> set[tuple]:
    """(reader, local, key) where the local is drilled out of a record that lacks that key: the
    map can only ever be `{}`, so every read that goes through it answers from its fallback.
    Declared once per drill rather than per site, because the site names are fine -- the map is not."""
    out = set()
    for reader, spec in READERS.items():
        for local, (parent, key) in spec["drilled"].items():
            if parent in spec["record_of"] and key not in _emitted_for(spec["record_of"][parent]):
                out.add((reader, local, key))
    return out


def _hollow_drill_reads() -> set[tuple]:
    """The one-name read that *performs* a hollow drill, on its parent receiver.
    `pick(raw, "company")` on a record with no `company` component is the drill's own defect, which
    HOLLOW_DRILLS already carries with the reason; counting it a second time as a dead read site
    would let the two lists disagree about the same line without telling anyone more."""
    return {(reader, READERS[reader]["drilled"][local][0], (key,))
            for (reader, local, key) in _hollow_drills()}


def _dead_read_sites() -> list[dict]:
    """Sites whose every candidate name is absent from the producers behind their receiver."""
    out = []
    for reader, spec in READERS.items():
        hollow = {local for (r, local, _) in _hollow_drills() if r == reader}
        drill_reads = _hollow_drill_reads()
        for site in _sites(reader):
            receiver = site["receiver"]
            if receiver not in spec["record_of"]:
                continue  # unbound or blind: the structural rule has already named it
            if receiver in hollow:
                continue
            if (reader, receiver, site["keys"]) in drill_reads:
                continue
            if not set(site["keys"]) & _emitted_for(spec["record_of"][receiver]):
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
    assert len(applications) == 16
    assert {s["receiver"] for s in applications} == {"raw", "nested"}
    assert sum(1 for s in applications if s["receiver"] == "nested") == 3
    messages = _sites("normalizeMessages")
    assert len(messages) == 8
    assert {s["receiver"] for s in messages} == {"m", "raw"}
    matches = _sites("normalizeMatch")
    assert len(matches) == 18
    assert {s["receiver"] for s in matches} == {"raw", "m"}
    assert sum(1 for s in matches if s["receiver"] == "m") == 17  # every payload read, incl. idOf
    gaps = _sites("normalizeSkillGaps")
    assert len(gaps) == 4
    assert {s["receiver"] for s in gaps} == {"raw", "g"}
    assert sum(1 for s in gaps if s["receiver"] == "g") == 3     # the three item reads
    jobs = _sites("normalizeJob")
    assert len(jobs) == 33
    assert {s["receiver"] for s in jobs} == {"raw", "company"}
    assert sum(1 for s in jobs if s["receiver"] == "company") == 5
    # 33, not the 37 this reader had before #127 bound it: `remote`, `salaryText`, a standalone
    # `tags` field and `whyMatch` had no author on any of the three job payloads, and the job card
    # had a fifth name on top of them -- `Job.match`, which no hook ever set. Each one read as a
    # nullable field the UI could only ever show as empty. `tags` still appears once, as a candidate
    # inside the `skills` site, where a live sibling carries the call.
    hits = _sites("normalizeSearch")
    assert len(hits) == 3
    assert {s["receiver"] for s in hits} == {"h"}
    # Three sites, all on a hit -- and the reader had 17 before #128 measured that its two fallback
    # paths answer to nothing: `/search` is the only caller's endpoint, `SearchResponse` has no
    # `groups` component and no `items`/`results`, so `{groups:[…]}` and flat `{items:[…]}` payloads
    # were shapes the mapper would silently reinterpret rather than shapes anyone served. The tests
    # that fed them invented a "People" entity with a `/people/:id` route the product does not have.
    # `list(raw, g.key)` is the one read of `raw` left, and it has no literal name to check, so the
    # two source-derived lists below are what make it live instead of a candidate table here.
    groups, records = _search_group_keys(), _search_hits()
    assert groups == ["jobs", "companies", "resumes", "notes", "conversations", "applications"]
    assert sorted(groups) == sorted(records)
    assert set(records.values()) == set(READERS["normalizeSearch"]["record_of"]["h"])
    assert set(groups) <= _emitted("SearchResponse")
    # Per group, which names the subtitle site actually answers from. Measured, because a group whose
    # record carries none of them renders a row with no second line in the palette.
    subtitle = next(s for s in hits if "industry" in s["keys"])
    assert {key: sorted(set(subtitle["keys"]) & _emitted(record))
            for key, record in records.items()} == {
        "jobs": ["companyName", "location", "status"],
        "companies": ["industry"],
        "resumes": ["status"],
        "notes": ["snippet"],
        "conversations": ["snippet"],
        "applications": ["companyName", "status"],
    }
    assert len(_emitted("JobListItem")) == 18
    assert len(_emitted("SavedJobItem")) == 3
    assert len(_emitted("SearchResponse")) == 7
    assert len(_emitted("SkillGap")) == 3
    assert len(_emitted("ApplicationItem")) == 15
    assert len(_emitted("CompanyItem")) == 9
    assert len(_emitted("MessageItem")) == 8
    assert len(_emitted("MatchResponse")) == 3
    assert len(_emitted("JobDetail")) == 23
    assert len(_emitted("MatchSummary")) == 14
    assert len(_emitted("MatchResult")) == 14
    # ...and the union is not a restatement of one side: `id`/`createdAt` come only from the stored
    # row, `interviewTopics`/`model` only from the AI service's answer. `skillGaps` used to sit on
    # the second side too — #126 gave it a column, so both authors now emit it and the site that
    # reads it is live on every path rather than only after a fresh compute.
    assert _emitted("MatchSummary") - _emitted("MatchResult") == {"id", "createdAt"}
    assert _emitted("MatchResult") - _emitted("MatchSummary") == {"interviewTopics", "model"}
    assert _id_of_keys() == {"_id", "eventId", "event_id", "id", "key", "uuid"}
    dead = _dead_read_sites()
    assert len(dead) == 3
    assert {(s["reader"], s["line"]) for s in dead} == {
        ("normalizeApplication", 19), ("normalizeMatch", 12), ("normalizeMatch", 13)}
    assert _structural_problems() == []
