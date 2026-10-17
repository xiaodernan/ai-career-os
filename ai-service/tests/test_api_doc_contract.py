"""What docs/API.md says the internal endpoints are is what the app actually serves.

The doc is the contract other people write code against: a path that no router registers sends a
reader to a 404 they cannot explain, and a response group missing a key means a client that never
thinks to look for it. Both happened once already -- `/internal/features/documents/{id}/text`
(documented; the router says `/internal/ingest/...`) was a path no caller could build.

Paths come from the live route table and response keys from the handler's own `return`, so a
rename on either side reddens this rather than quietly splitting the two.
"""

import re
from pathlib import Path

from tests.test_internal_contract import _routes
from tests.test_response_shape_contract import _returned

DOC = Path(__file__).resolve().parents[2] / "docs" / "API.md"
VERBS = {"GET", "POST", "PATCH", "PUT", "DELETE"}

# the doc's one generic mention of the prefix, in the section that describes the surface
EXEMPT = {"/internal/*": "the prose table of the two API surfaces, not an endpoint"}

# the heading whose table claims -- and is gated on claiming -- that the backend calls none of it
FORWARD_HEADING = "### 3.2"

# the phrase a section 3 row carries when no backend client builds that request
NO_CALLER = "no backend caller:"


def _rows(text: str | None = None) -> list[tuple[str, str, str]]:
    """(verb, path, notes) for every internal endpoint row -- in the doc, or in a fragment of it."""
    out = []
    lines = (DOC.read_text(encoding="utf-8") if text is None else text).splitlines()
    for line in lines:
        if not line.startswith("| ") or "`/internal" not in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0] not in VERBS:
            continue  # the surface-overview table has the same shape but no method column
        path = re.sub(r"\{[^}]*}", "{}", cells[1].strip("`"))
        out.append((cells[0], path, cells[2]))
    return out


def section_rows(heading: str) -> set[tuple[str, str]]:
    """The rows under one `###` heading, up to the next heading of any level.

    Section 3.2's membership is a claim about a *table*, so the reader has to stop at the
    table's own section: reading the whole doc would grade 3.2 by what section 3 happens to
    list as well, and the two would never disagree.
    """
    text = DOC.read_text(encoding="utf-8")
    start = text.index(heading) + len(heading)
    rest = text[start:]
    stops = [at for at in (rest.find("\n## "), rest.find("\n### ")) if at != -1]
    return {(verb, path) for verb, path, _notes in _rows(rest[:min(stops)] if stops else rest)}


def reached_pairs() -> set[tuple[str, str]]:
    """The requests the backend is seen building, from the walk that owns that reading."""
    from tests.test_internal_contract import _calls, _relay_calls

    return ({(c["verb"], c["path"]) for c in _calls()}
            | {(c["verb"], c["path"]) for c in _relay_calls()})


def documented_paths() -> set[str]:
    return {path for _verb, path, _notes in _rows()}


def all_internal_literals() -> set[str]:
    """Every `/internal/...` the doc writes in backticks, in rows or in prose."""
    text = DOC.read_text(encoding="utf-8")
    return {re.sub(r"\{[^}]*}", "{}", m) for m in re.findall(r"`(/internal/[^`\s]*)`", text)}


def _response_claim(notes: str) -> tuple[set[str], bool] | None:
    """The `{...}` group after an arrow: (keys named, whether the row left the list open)."""
    arrow = re.search(r"→\s*(.*)", notes)
    if not arrow:
        return None
    group = re.search(r"\{([^{}]*)}", arrow.group(1))
    if not group:
        return None
    names = [n.strip().rstrip("?").rstrip("[]") for n in group.group(1).split(",")]
    clean = {n for n in names if n and n != "..."}
    return clean, "..." in names


def response_claims() -> dict[str, tuple[set[str], bool]]:
    out = {}
    for _verb, path, notes in _rows():
        claim = _response_claim(notes)
        if claim:
            out[path] = claim
    return out


# ------------------------------------------------------------------------ the reconciliations

def test_every_internal_path_the_doc_writes_is_one_the_service_registers():
    registered = {path for (_verb, path) in _routes()}
    phantom = sorted(all_internal_literals() - registered - set(EXEMPT))
    assert phantom == [], f"API.md advertises paths no router serves: {phantom}"


def test_the_doc_names_the_method_each_internal_route_answers():
    routes = _routes()
    problems = []
    for verb, path, _notes in _rows():
        if (verb, path) not in routes:
            problems.append(f"{verb} {path} is documented but the app serves "
                            f"{sorted(v for (v, p) in routes if p == path)}")
    assert problems == [], "\n".join(problems)


def test_every_route_the_service_registers_has_one_row_in_the_doc():
    """The other direction of the row above, and the one that was missing.

    A route can be added, called by an agent tool, and reached by no backend client, and pass
    every gate in this file -- because all of them start from what the doc wrote and ask whether
    it is true. This starts from the live route table and asks whether the doc wrote it at all.
    It is the gate that would have reddened when `POST /internal/features/follow-ups` landed.
    """
    counted = [(verb, path) for verb, path, _notes in _rows()]
    duplicates = sorted({pair for pair in counted if counted.count(pair) > 1})
    assert duplicates == [], f"an endpoint documented twice, in two tables that claim different things: {duplicates}"
    assert set(counted) == set(_routes()), (
        f"rows no router serves {sorted(set(counted) - set(_routes()))}, "
        f"routes no row names {sorted(set(_routes()) - set(counted))}")
    assert len(counted) >= 50, f"the doc was not read as a table of the surface ({len(counted)} rows)"


def unreached_pairs() -> set[tuple[str, str]]:
    """Registered routes the backend is never seen building a request for."""
    return set(_routes()) - reached_pairs()


def ledger_pairs() -> set[tuple[str, str]]:
    """The routes the `UNREACHED_BY_THE_APP` literal explains, at table granularity.

    Derived from the live route table rather than copied from the doc's rows: a ledger entry
    earns its routes by being registered, and a spelling no router serves explains nothing.
    """
    return {(verb, path) for (verb, path) in _routes() if path in UNREACHED_BY_THE_APP}


def test_the_forward_table_is_exactly_the_surface_the_backend_does_not_call():
    """Section 3.2's membership is measured, not remembered.

    Without this the table is a hiding place: a route could be parked there to escape the
    response-key reconciliation section 3 gets, and the completeness gate above would call that
    covered. It is covered by a table whose own claim is that nobody calls it.

    The routes that sit in the main table and are explained by the ledger instead are subtracted
    below -- and the gate after this one charges the two explanations with partitioning the
    unreached surface, so subtraction cannot become a gap a route falls through.
    """
    forward = section_rows(FORWARD_HEADING)
    assert forward == unreached_pairs() - ledger_pairs(), (
        f"3.2 names {sorted(forward & reached_pairs())} the backend does call -- move those rows "
        f"up to section 3; it omits {sorted(unreached_pairs() - ledger_pairs() - forward)}")
    assert len(forward) >= 25, f"the forward table cannot be read ({len(forward)} rows)"


def test_every_route_nobody_calls_is_explained_exactly_once():
    """The forward table and the ledger are two halves of one claim, and they do not overlap.

    A route the backend stopped calling could otherwise be excused twice -- and, worse, a ledger
    line can only excuse a route that exists. Both directions are charged here: the split must
    cover the measured set, and every entry in the literal must still name a registered route
    that nobody calls.
    """
    forward = section_rows(FORWARD_HEADING)
    unreached = unreached_pairs()
    ledger = ledger_pairs()
    assert len(ledger) == len(UNREACHED_BY_THE_APP), (
        "two ledger paths answer to one route spelling, so one reason is doing no work")
    assert forward | ledger == unreached, (
        f"unexplained {sorted(unreached - forward - ledger)}, "
        f"excused twice {sorted(forward & ledger)}")
    stale = sorted({path for path in UNREACHED_BY_THE_APP
                    if not any(p == path for (_v, p) in unreached)})
    assert stale == [], (f"the ledger excuses {stale} no router serves or the backend now calls")
    assert len(unreached) == len(forward) + len(ledger)


def test_what_the_backend_calls_is_documented_where_a_response_is_named():
    """The converse, aimed at section 3: a live dependency cannot hide in the forward table."""
    forward = section_rows(FORWARD_HEADING)
    hidden = sorted(reached_pairs() & forward)
    assert hidden == [], (f"the backend builds {hidden}, but only the table that claims nobody "
                          f"calls it names it")


def marker_reason(notes: str) -> str | None:
    """The sentence inside a row's `no backend caller:` parenthetical, or None."""
    at = notes.find(NO_CALLER)
    if at == -1:
        return None
    tail = notes[at + len(NO_CALLER):].rstrip()
    if not tail.endswith(")"):
        return "UNCLOSED"  # a marker the reader cannot finish reading is a problem, not an absence
    return tail[:-1].strip()


def test_a_route_the_backend_never_builds_says_so_in_its_own_row():
    """The main table cannot advertise a surface as though the product drives every line of it.

    A reader of section 3 cannot tell `/internal/rag/embeddings`, which the backend calls for the
    hybrid `/jobs` ranking, from `/internal/rag/retrieve`, which nothing in the backend builds:
    both answer, both take the token. The marker is the only thing that separates them on the
    page, so it is held to the measured set -- a row claiming no caller while the walk sees one,
    or a ledger route whose row stayed silent, reddens this. And the sentence the marker carries
    is the ledger's own, compared verbatim: two copies of one reason is the drift this file exists
    to close, so the doc quotes the literal rather than restating it.
    """
    marked = {}
    for verb, path, notes in _rows():
        reason = marker_reason(notes)
        if reason is not None:
            marked[(verb, path)] = reason
    assert set(marked) == ledger_pairs(), (
        f"marked but not excused {sorted(set(marked) - ledger_pairs())}, "
        f"excused but unmarked {sorted(ledger_pairs() - set(marked))}")
    lying = sorted(set(marked) & reached_pairs())
    assert lying == [], f"{lying} is marked as called by nobody, but the walk sees the request"
    stale = sorted(f"{verb} {path}: row says {reason!r}, ledger says "
                   f"{UNREACHED_BY_THE_APP[path]!r}"
                   for (verb, path), reason in marked.items()
                   if reason != UNREACHED_BY_THE_APP[path])
    assert stale == [], "\n".join(stale)


def test_every_response_key_the_doc_names_is_one_the_handler_returns():
    routes = _routes()
    problems = []
    for verb, path, notes in _rows():
        claim = _response_claim(notes)
        route = routes.get((verb, path))
        if claim is None or route is None:
            continue
        shape = _returned(route)
        if shape is None:
            problems.append(f"{verb} {path} documents a response group but this reader cannot "
                            "name what the handler returns")
            continue
        phantom = sorted(claim[0] - set(shape))
        if phantom:
            problems.append(f"{verb} {path} is documented with {phantom}, which it never answers")
        forgotten = sorted(set(shape) - claim[0])
        if forgotten and not claim[1]:
            problems.append(f"{verb} {path} answers {forgotten} that the row never names")
    assert problems == [], "\n".join(problems)


def test_the_exempted_literal_is_still_what_it_was():
    """The exemption needs a real reason: if the prose changes shape, this has to be re-earned."""
    assert all_internal_literals() - documented_paths() == set(EXEMPT)


def test_both_sides_of_the_comparison_are_actually_read():
    """Positive control: the gates above stay green on a doc that named nothing."""
    assert len(documented_paths()) >= 20, "the doc's internal table was not read"
    assert "/internal/ingest/documents/{}/text" in documented_paths()
    assert response_claims() == {"/internal/agents/chat": ({"task_id", "run_id"}, False),
                                 "/internal/rag/embeddings": ({"embedding"}, False)}
    shape = _returned(_routes()[("POST", "/internal/agents/chat")])
    assert set(shape) == {"task_id", "run_id"}


# --------------------------------------------------- who can reach an internal endpoint

# Documented, registered, and not called by the backend -- each for its own reason, so that a new
# caller means retiring a line here rather than letting the table quietly advertise surfaces the
# product never reaches. `/internal/stream/{}` and `/internal/agents/chat` are *not* in this list:
# `SseRelayService` relays the first, and the copilot's streaming route starts the second.
# `/internal/rag/embeddings` left this list when `HttpAiServiceClient.embedQuery` began feeding the
# backend's hybrid /jobs ranking; the agent still embeds in-process via registry.embed_text.
UNREACHED_BY_THE_APP = {
    "/internal/agents/runs": "the Activity panel reads agent_runs over the shared database instead",
    "/internal/agents/runs/{}": "same, for one run's detail",
    "/internal/rag/retrieve": "retrieval happens in-process, agent tools -> pipeline.retrieve",
    "/internal/rag/answer": "same, for the grounded-answer variant",
    "/internal/rag/chunks": "kept for operators",
    "/internal/tasks/{}": "the app follows /internal/stream/{taskId} instead",
    "/internal/tasks/{}/stream": "a second stream spelling, unused by the relay",
}


def unreached_paths() -> set[str]:
    from tests.test_internal_contract import _calls, _relay_calls

    reached = {c["path"] for c in _calls()} | {c["path"] for c in _relay_calls()}
    return documented_paths() - reached


def test_what_the_doc_lists_but_the_app_never_calls_stays_explained():
    """A documented-but-unreached path is explained twice over or not at all.

    Section 3.2's table is one explanation, carried by the gate that pins its membership to the
    measured unreached set; the list below is the other, for the routes that sit in the main
    table and are reached by nobody for a reason of their own.
    """
    forward = {path for (_verb, path) in section_rows(FORWARD_HEADING)}
    assert unreached_paths() - forward == set(UNREACHED_BY_THE_APP)


def test_the_unreached_list_is_not_just_a_long_list_of_nothings():
    """Positive control: the comparison above also passes when both sides are empty."""
    assert len(UNREACHED_BY_THE_APP) == 7
    assert all(reason.strip() for reason in UNREACHED_BY_THE_APP.values())
    assert "/internal/stream/{}" not in UNREACHED_BY_THE_APP, \
        "the relay reaches that one; treating it as unreached would hide a live dependency"
