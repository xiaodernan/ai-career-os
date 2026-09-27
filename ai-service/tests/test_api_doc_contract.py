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


def _rows() -> list[tuple[str, str, str]]:
    """(verb, path, notes) for every internal endpoint row."""
    out = []
    for line in DOC.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or "`/internal" not in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0] not in VERBS:
            continue  # the surface-overview table has the same shape but no method column
        path = re.sub(r"\{[^}]*}", "{}", cells[1].strip("`"))
        out.append((cells[0], path, cells[2]))
    return out


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
UNREACHED_BY_THE_APP = {
    "/internal/agents/runs": "the Activity panel reads agent_runs over the shared database instead",
    "/internal/agents/runs/{}": "same, for one run's detail",
    "/internal/rag/retrieve": "retrieval happens in-process (agent tools -> pipeline.retrieve)",
    "/internal/rag/answer": "same, for the grounded-answer variant",
    "/internal/rag/chunks": "chunk inspection, kept for operators",
    "/internal/rag/embeddings": "exposed for the backend's hybrid /jobs ranking; that call is not "
                                 "wired yet, and the agent embeds in-process via registry.embed_text",
    "/internal/tasks/{}": "task state; the app follows /internal/stream/{taskId} instead",
    "/internal/tasks/{}/stream": "a second stream spelling, unused by the relay",
}


def unreached_paths() -> set[str]:
    from tests.test_internal_contract import _calls, _relay_calls

    reached = {c["path"] for c in _calls()} | {c["path"] for c in _relay_calls()}
    return documented_paths() - reached


def test_what_the_doc_lists_but_the_app_never_calls_stays_explained():
    assert unreached_paths() == set(UNREACHED_BY_THE_APP)


def test_the_unreached_list_is_not_just_a_long_list_of_nothings():
    """Positive control: the comparison above also passes when both sides are empty."""
    assert len(UNREACHED_BY_THE_APP) == 8
    assert all(reason.strip() for reason in UNREACHED_BY_THE_APP.values())
    assert "/internal/stream/{}" not in UNREACHED_BY_THE_APP, \
        "the relay reaches that one; treating it as unreached would hide a live dependency"
