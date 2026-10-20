"""A doc that calls a route "proxied from ai-service" is claiming a dependency, and the code
either has it or does not.

`docs/AGENTS.md` said `GET /api/v1/activity/runs` and its detail route "are proxied from the
ai-service endpoints". They are not: `ActivityController` reads `agent_runs` and `agent_traces`
through JPA repositories scoped by the caller's own user id, and builds no HTTP request at all
-- which is also why those two ai-service routes sit in `test_api_doc_contract.py`'s ledger of
routes no backend client calls. A reader who believed the sentence would look for a client
method that does not exist, and would expect the panel to go down when ai-service does; it does
not, because it never went up with it.

So the claim is graded the way the rest of this suite grades prose: find every unit of docs text
that says something is proxied, relayed or forwarded *and* names ai-service, then check it
against two facts read out of the backend's own source. Which class answers the public route
(`@RequestMapping` grammar shared with the worked-examples gate, so the two cannot disagree about
what a mapping is), and whether that class reaches an ai-service request -- computed as the
transitive closure over the types that hold an `"/internal/..."` literal, through the code that
names them. The closure has to be transitive because Spring wires through interfaces and services:
`CopilotController` never spells a path, `HttpAiServiceClient` does. The `implements` clause is the
hop carrying the most weight -- the backend classes that depend on ai-service name `AiServiceClient`
and not the client class -- so the gate pins the files that depend on that interface against a
reading of the builders' own clause, not against the walk that is supposed to have followed it.

A claim that names no `/internal` route is also refused, because it cannot be checked: "proxies
ai-service internal SSE" points at nothing a test can look up.

The charge on the routes a claim *does* name is "some of them are relayed", not "all of them":
architecture.md's own sub-bullet spells both stream routes (`/internal/tasks/{id}/stream` and the
alias the relay actually calls), and the doc that lists them says in terms that the first one is
unused by the relay. Demanding that every named path be a built one would grade a careful
sentence as a lie, so the gate asks two weaker, separately-honest questions instead: every route a
relay claim names is one ai-service actually serves, and at least one is one the backend builds a
request for. A claim that names only never-called routes still has no referent to proxy and goes
red -- which is the only way this file can tell "the relay reads both spellings" from "the relay
reads the one it never touches".
"""

import re
from pathlib import Path

from tests.test_api_doc_contract import reached_pairs
from tests.test_internal_contract import _routes
from tests.test_the_worked_examples_survive_a_copy_paste import (BASE_MAPPING, MAPPING,
                                                                norm, read)

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
JAVA = ROOT / "backend" / "src" / "main" / "java"
DOCS = ROOT / "docs"

PROXY = re.compile(r"\b(proxies|proxied|proxying|relays|relayed|forwards|forwarded)\b", re.I)
API_LIT = re.compile(r"`(?:(?:GET|POST|PATCH|PUT|DELETE) )?"
                     r"((?:/api|https?://[^\s`]*/api)[^\s`]*)`")
# the verb inside the backticks is how the docs spell a route, so it cannot be what makes a
# literal invisible to this reader
INTERNAL_LIT = re.compile(r"`(?:(?:GET|POST|PATCH|PUT|DELETE) )?"
                          r"([^`\s]*/internal/[^`\s]*)`")
AI_SERVICE = "ai-service"

MINIMUM_CLAIMS = 1
MINIMUM_PUBLIC_PATHS = 40
MINIMUM_CLOSURE = 3
# a handful, not a count of today's 21: the pin needs a floor that survives the writer lane adding
# or renaming a service, but that still refuses a backend which stopped wiring against the interface
MINIMUM_INTERFACE_USERS = 10

# ------------------------------------------------------------------ the backend, as the code has it


def strip_comments_and_strings(text: str) -> str:
    """Java source with comments and string bodies blanked, so a type counts only where code uses it.

    A javadoc that mentions `AiServiceClient` in a sentence is not a dependency; a field, a
    constructor parameter and a call are. Blank first, then look for the name.
    """
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)


def source_types_to_names(text: str) -> set[str]:
    """Every declared type the file answers to: its own name is not enough -- Spring wires interfaces."""
    out = {norm_type(n) for n in re.findall(
        r"\b(?:class|interface|record|enum)\s+([A-Z][A-Za-z0-9]*)", text)}
    for clause in re.findall(r"\b(?:implements|extends)\s+([^{;]*)", text):
        out |= {norm_type(n) for n in clause.split(",")}
    return {n for n in out if n}


def norm_type(name: str) -> str:
    return name.strip().split("<")[0].strip()


def java_files() -> dict[str, str]:
    return {p.name: read(p) for p in sorted(JAVA.rglob("*.java"))}


def request_builders(files: dict[str, str]) -> set[str]:
    """Files holding an `"/internal/..."` literal: the only proof of an outbound ai-service request.

    `"/api/internal/files/{key}"` contains the same substring and is the backend's own surface, so
    the literal has to *start* with the prefix.
    """
    return {name for name, text in files.items() if re.search(r'"(/internal/[^"]*)"', text)}


def client_interface_names(files: dict[str, str]) -> set[str]:
    """The interfaces the request builders declare they implement, read off the builders themselves.

    Deliberately a second reading of the same clause `reaching_files` depends on: the pin below has
    to say what the walk should have found, so it cannot be computed with the walk's own helper.
    """
    out: set[str] = set()
    for name in sorted(request_builders(files)):
        for clause in re.findall(r"\bimplements\s+([^{;]+)", strip_comments_and_strings(files[name])):
            out |= {norm_type(part) for part in clause.split(",") if norm_type(part)}
    return out


def naming(body: str, names: set[str]) -> bool:
    return any(re.search(rf"\b{re.escape(n)}\b", body) for n in names)


def interface_users(files: dict[str, str], names: set[str]) -> set[str]:
    """Files that hold a field, constructor parameter or call typed by one of those interfaces.

    Spring wires against the interface, so this -- not the implementor's file name -- is how a
    controller depends on ai-service. A javadoc mention does not count, hence the blanked body.
    """
    return {name for name, text in files.items()
            if naming(strip_comments_and_strings(text), names)}


def reaching_files(files: dict[str, str]) -> set[str]:
    """The transitive closure of "names a type that builds an ai-service request".

    Admission is by the declared type name appearing in code, never by a suffix: `*Service` would
    have let `UserService` in and `AiServiceClient`'s implementor out on the strength of a name.
    """
    reaching = set(request_builders(files))
    names = set()
    for name in reaching:
        names |= source_types_to_names(files[name])
    for _hop in range(1, 12):
        added = set()
        for name, text in files.items():
            if name in reaching:
                continue
            body = strip_comments_and_strings(text)
            if naming(body, names):
                added.add(name)
        if not added:
            return reaching
        reaching |= added
        for name in added:
            names |= source_types_to_names(files[name])
    raise AssertionError("the dependency closure did not settle -- a type cycle the walk cannot break")


def public_paths() -> dict[str, set[str]]:
    """Folded public path -> the controller files that register it."""
    out: dict[str, set[str]] = {}
    for path in sorted(JAVA.rglob("*Controller.java")):
        text = read(path)
        base = BASE_MAPPING.search(text)
        prefix = base.group(1) if base else ""
        for _verb, tail in MAPPING.findall(text):
            out.setdefault(norm((prefix + (tail or "")).replace("//", "/")), set()).add(path.name)
    return out


# -------------------------------------------------------------------- the docs, as claims

def prose_units(text: str) -> list[str]:
    """Blank-line blocks, bullet lists split per bullet, fenced code removed.

    A unit is the smallest thing that can hold one claim: the activity sentence wraps across four
    lines and a bullet's continuation line belongs to its bullet, while `proxy_pass` inside an
    nginx block is not a claim about this product's routes.
    """
    text = re.sub(r"```.*?```", "\n", text, flags=re.S)
    out = []
    for block in text.split("\n\n"):
        block = block.strip("\n")
        if not block.strip():
            continue
        lines = block.split("\n")
        if sum(1 for line in lines if line.lstrip().startswith(("- ", "* "))) >= 2:
            current: list[str] = []
            for line in lines:
                if line.lstrip().startswith(("- ", "* ")) and current:
                    out.append("\n".join(current))
                    current = [line]
                else:
                    current.append(line)
            out.append("\n".join(current))
        else:
            out.append(block)
    return [unit for unit in out if unit.strip()]


def fold_api(path: str) -> str:
    folded = re.sub(r"^https?://[^/]+", "", path)
    folded = norm(folded.split("?")[0])
    return folded.rstrip("/") or folded


def relay_prose() -> list[dict]:
    """Every docs unit that says something is proxied, relayed or forwarded from ai-service.

    This is `claims()` before its route filter, and the corpus really does hold relay sentences
    about a header and about a field; a reader that cannot tell those from route claims starts
    grading sentences that name nothing a test could look up.
    """
    out = []
    for doc in sorted(DOCS.glob("*.md")):
        for unit in prose_units(read(doc)):
            if PROXY.search(unit) and AI_SERVICE in unit:
                out.append({"doc": doc.name, "unit": unit})
    return out


def claims() -> list[dict]:
    """The relay prose that names routes: the units this file can actually check."""
    out = []
    for prose in relay_prose():
        unit = prose["unit"]
        routes = {fold_api(p) for p in API_LIT.findall(unit)}
        internals = {norm(p) for p in INTERNAL_LIT.findall(unit)}
        if not (routes or internals):
            continue  # prose about forwarding a header, not about a route
        out.append({"doc": prose["doc"], "unit": unit, "api": routes, "internal": internals})
    return out


# ---------------------------------------------------------------------------- the reconciliation


def served_internal_paths() -> set[str]:
    """Every `/internal` path a router serves, verbs folded away -- the docs name paths.

    A relay claim about a route ai-service never registered is a dead referent whatever verb the
    reader would have used, and the live route table is the only place that answers.
    """
    return {path for (_verb, path) in _routes()}


def facts() -> dict:
    """Everything the reconciliation reads, gathered once so both gates grade the same world."""
    return {"paths": public_paths(), "reach": reaching_files(java_files()),
            "built": {path for (_verb, path) in reached_pairs()},
            "served": served_internal_paths()}


def problems_of(claim: dict, *, paths, reach, built, served) -> list[str]:
    """Every way this one docs sentence fails the code it says the code has."""
    where = f"{claim['doc']}: {claim['unit'].splitlines()[0][:70]!r}"
    out = []
    if claim["api"] and not claim["internal"]:
        out.append(f"{where} claims a relay and names no `/internal` route, so nothing "
                   "can be looked up about it")
    for route in sorted(claim["internal"]):
        if route not in served:
            out.append(f"{where} says the backend relays {route}, and no ai-service router "
                       "serves that path")
    if claim["internal"] and not (claim["internal"] & built):
        out.append(f"{where} claims a relay, but the backend builds a request for none of "
                   f"{sorted(claim['internal'])} -- there is nothing here to proxy")
    for route in sorted(claim["api"]):
        answers = paths.get(route)
        if answers is None:
            out.append(f"{where} says {route} is proxied, but no controller registers it")
            continue
        if not (answers & reach):
            out.append(f"{where} says {route} is proxied from ai-service, but "
                       f"{sorted(answers)} is served by a class that reaches no "
                       "ai-service request -- the rows come from somewhere else")
    return out


def test_what_the_docs_call_proxied_is_a_route_a_reaching_class_answers():
    world = facts()
    problems = [problem for claim in claims() for problem in problems_of(claim, **world)]
    assert problems == [], "\n".join(problems)


def test_the_reader_grades_route_claims_and_declines_the_rest():
    """The reader's own scope, pinned from both sides.

    `claims()` skips units that name no route -- a decision, not an accident -- and this is the
    leg that says the skipped pile exists and stayed skipped. Without it the filter could admit
    everything and the reconciliation would still be green, because a header sentence generates
    no problem to find.
    """
    prose = relay_prose()
    routeless = [entry for entry in prose
                 if not (API_LIT.findall(entry["unit"]) or INTERNAL_LIT.findall(entry["unit"]))]
    assert routeless, ("every relay sentence in docs/*.md names a route, so the reader's decision "
                       "to skip the ones that do not is no longer skipping anything -- either the "
                       "prose changed shape or the literal regexes went blind")
    graded = {entry["unit"] for entry in claims()}
    skipped = [f"{entry['doc']}: {entry['unit'].splitlines()[0][:60]!r}"
               for entry in routeless if entry["unit"] in graded]
    assert skipped == [], f"route-free relay prose is being graded as a claim: {skipped}"


def test_the_claims_are_read_from_the_docs_and_the_closure_is_read_from_the_backend():
    """Positive control, both ends: the claim scan finds real claims and the closure has real teeth.

    The gate above passes on an empty `claims()`, and it would pass on a closure that stayed at
    its two seed files if the walk never grew -- either failure alone turns the reconciliation into
    a green that says nothing. A third way to be hollow is to grade only denials: if no relay claim
    survives at all, the real proxy in this product goes unjudged and every future edit reads as a
    pass.
    """
    world = facts()
    found = claims()
    assert len(found) >= MINIMUM_CLAIMS, (f"only {len(found)} route claims found across docs/*.md;"
                                          " the prose stopped claiming anything, or the reader broke")
    clean = [claim for claim in found if not problems_of(claim, **world)]
    assert clean, ("no relay claim in the docs names a route that a reaching controller answers "
                   "and the backend really builds, so the gate above is a denial list rather "
                   "than a contract")
    files = java_files()
    builders = request_builders(files)
    assert builders == {"HttpAiServiceClient.java", "SseRelayService.java"}, builders
    reach = world["reach"]
    assert len(reach) >= MINIMUM_CLOSURE, f"the closure never grew past its seeds ({len(reach)})"
    # The implements clause is load-bearing: it is the only reason a controller that never
    # mentions the implementing class joins the closure. Measured from the builders themselves, so
    # a walk that stops following it fails against the code rather than against its own reading.
    interfaces = client_interface_names(files)
    assert interfaces, ("neither request builder declares an `implements` clause, so this pin can "
                        "no longer say what the closure is supposed to follow")
    dependents = interface_users(files, interfaces)
    assert len(dependents) >= MINIMUM_INTERFACE_USERS, (
        f"only {len(dependents)} backend file(s) name the interface(s) {sorted(interfaces)} in "
        "code; a backend that wires its ai-service dependency that way is not what this gate was "
        "written against")
    lost = sorted(dependents - reach)
    assert lost == [], (f"{lost} name{'s' if len(lost) == 1 else ''} an ai-service client "
                        f"interface ({sorted(interfaces)}) and the closure does not see "
                        "them -- the walk stopped following `implements`")
    assert "CopilotController.java" in reach and "AiStreamController.java" in reach, (
        "the copilot stream is the product's one real proxy; if the closure cannot see it, the "
        "gate cannot blame anything")
    assert "ActivityController.java" not in reach, (
        "ActivityController reads agent_runs over JPA; if the closure now says it reaches "
        "ai-service, the claim it disproved in this file's header is true again and the prose "
        "needs rewriting, not the closure")
    assert len(world["paths"]) >= MINIMUM_PUBLIC_PATHS
    assert world["built"] <= world["served"], (
        f"{sorted(world['built'] - world['served'])}: the backend builds a request for a path "
        "no router serves, so every referent check in this file reads a broken table")

