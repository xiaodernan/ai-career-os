"""The edge is more patient than the domain, and the domain than the engine.

Every hop in the browser's longest turn carries its own patience budget, and the
ladder only works if each hop is willing to wait longer than the hop behind it:
the ai-service's LLM call budget (120s), the backend's read timeout on the engine's
answer (180s), the gateway's response timeout on the whole turn (300s). The gateway's
own comment states the relationship -- "the response budget is above the backend's
180-second AI read budget, because the edge must not cut a turn the backend still
expects to finish" -- but nothing held it, so lowering the edge's patience to, say,
30s would ship a product where the longest AI turns die at the edge with a 504 while
the backend is still working, and every unit test in both modules stays green. The
same holds one hop down: an engine budget above 180s hangs calls the backend cuts
mid-read.

The budgets are read off the sources that promise them -- the gateway's
`httpclient.response-timeout`, the backend's `setReadTimeout`, the engine's
`llm_timeout_s` -- and the three numbers are pinned explicitly, because a budget
that moves should move knowingly, against this ladder, not silently. Honest scope:
`llm_timeout_s` budgets one LLM call, and an engine response that chains several
calls must fit the domain's 180s itself -- the orchestrator owns that sequencing;
this gate holds the hops' relationship, not the engine's internal arithmetic.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
GATEWAY_YML = ROOT / "gateway/src/main/resources/application.yml"
BACKEND_CLIENT = ROOT / "backend/src/main/java/com/careeros/ai/HttpAiServiceClient.java"
ENGINE_SETTINGS = ROOT / "ai-service/app/core/config.py"


def _gateway_base_document() -> dict:
    """The base document: the `eureka` profile is a second one (Epic 98)."""
    return next(iter(yaml.safe_load_all(GATEWAY_YML.read_text(encoding="utf-8"))))


def _edge_response_timeout_seconds() -> int:
    """The gateway's whole-turn budget, read off `httpclient.response-timeout`."""
    httpclient = _gateway_base_document()["spring"]["cloud"]["gateway"]["server"]["webflux"]["httpclient"]
    timeout = httpclient["response-timeout"]
    # The yaml spells it "300s"; the ladder works in seconds.
    match = re.fullmatch(r"(\d+)s", str(timeout))
    assert match, f"unexpected response-timeout spelling: {timeout!r}"
    return int(match.group(1))


def _edge_connect_timeout_ms() -> int:
    httpclient = _gateway_base_document()["spring"]["cloud"]["gateway"]["server"]["webflux"]["httpclient"]
    return int(httpclient["connect-timeout"])


def _domain_read_timeout_seconds() -> int:
    """The backend's engine-answer budget, read off the client factory's read timeout."""
    text = BACKEND_CLIENT.read_text(encoding="utf-8")
    match = re.search(r"setReadTimeout\(Duration\.ofSeconds\((\d+)\)\)", text)
    assert match, "HttpAiServiceClient no longer declares its engine read timeout"
    return int(match.group(1))


def _engine_llm_budget_seconds() -> int:
    text = ENGINE_SETTINGS.read_text(encoding="utf-8")
    match = re.search(r"llm_timeout_s:\s*float\s*=\s*(\d+)", text)
    assert match, "ai-service Settings no longer declares the LLM call budget"
    return int(match.group(1))


def test_the_edge_outlasts_the_domain_and_the_domain_the_engine():
    edge = _edge_response_timeout_seconds()
    domain = _domain_read_timeout_seconds()
    engine = _engine_llm_budget_seconds()

    assert edge > domain, (
        f"the edge's response timeout ({edge}s) must exceed the backend's engine read "
        f"budget ({domain}s): an edge that gives up first cuts a turn the backend is "
        "still working on, and the browser reads the 504 as the product failing"
    )
    assert domain > engine, (
        f"the backend's engine read budget ({domain}s) must exceed the engine's own LLM "
        f"call budget ({engine}s): an engine that hangs past the domain's patience gets "
        "its answer cut mid-read, which the backend reports as a 502 the caller cannot "
        "distinguish from a dead engine"
    )
    # The pinned numbers, so a budget that moves moves against this ladder knowingly.
    assert (edge, domain, engine) == (300, 180, 120), (
        "the patience ladder moved -- update this pin, the gateway's comment and "
        "docs/DEPLOYMENT.md together, or the three pages disagree about how long a "
        "turn may take"
    )


def test_the_edges_connect_budget_stays_the_short_one():
    """A connect that will not open should be abandoned before the caller notices.

    The edge's connect timeout (3s) is deliberately far below its response budget:
    the browser should hear "unavailable" fast when the backend is gone, not wait
    the whole response budget on a socket that never opened. Read off the same
    block so the two budgets move together.
    """
    assert _edge_connect_timeout_ms() == 3000, (
        "the edge's connect timeout moved: the response budget is the patience for "
        "work in flight, the connect budget is the fast 'the backend is gone' answer, "
        "and the two must not swap roles"
    )
    assert _edge_connect_timeout_ms() < _edge_response_timeout_seconds() * 1000, (
        "the connect budget must stay shorter than the response budget, or a dead "
        "backend looks like a slow one"
    )
