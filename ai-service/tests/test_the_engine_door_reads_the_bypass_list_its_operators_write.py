"""The engine's outbound door reads the proxy bypass list the way its operators write it.

Measured on this repository's own venv (httpx 0.28.1): constructing an ``AsyncClient`` while
``NO_PROXY`` holds a bracketed IPv6 literal -- ``[::1]``, the shape Windows' system-proxy
bypass list emits and the shape curl's documentation teaches -- raises

    httpx.InvalidURL: Invalid port: ':1]'

before a socket exists. httpx splits each entry on ``:`` and reads what follows as a port,
so the last colon of the literal leaves ``:1]`` where a number belongs. Nothing about the
call is wrong: the variable says *do not proxy these hosts*, and it was written for a
different program.

Two doors in the service build clients, and both were exposed. ``providers/registry``'s
shared pool answers every LLM, embedding and voice call, so each of those became a 500 whose
text names neither the variable nor the fix; ``ingestion/pipeline``'s fetch -- which asks the
*internal* backend for stored bytes, precisely the host class a bypass list exists to exempt
-- failed the ingestion of every document. And because ``/health`` asks the same factories
whether they can build what the deployment named, the readiness line died with them, which is
the shape this project keeps meeting: a dependency that cannot be reached answered as though
the service itself were broken.

``app/core/envnet`` is now the one door. It rewrites the bracket form -- a spelling change,
since ``[::1]`` and ``::1`` are one host and only the second parses -- and refuses, with the
variable and its value in the sentence, anything it would have to guess about. That refusal
travels two ways: ``_buildable`` reads it, so an unreadable environment costs the operator a
clear ``llm_ready: false`` instead of an exception through the probe, and the edge maps it to
``AI_EGRESS_ENV_UNREADABLE``, so the request that hits the closed door is answered with the
same sentence the log carries rather than httpx's ``Invalid port``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.core import envnet
from app.ingestion import pipeline
from app.providers import registry

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
REPO_ROOT = Path(__file__).resolve().parents[2]

#: What Windows' bypass list and curl's docs actually write, and what Epic 285's own example
#: documents -- both must build a client.
WINDOWS_BYPASS = "localhost,.localhost,127.0.0.1,127.0.0.0/8,[::1],::1"
SHIPPED_BYPASS = ("localhost,127.0.0.1,::1,redis,postgres,minio,backend,gateway,discovery,"
                  "config-server")
#: A bracket carrying its own port: translating it would mean deciding where the address ends,
#: so the door refuses it by name instead of guessing.
UNREADABLE_BYPASS = "localhost,[::1]:8080"


@pytest.fixture
def cleared_client_cache():
    registry._http_client.cache_clear()
    yield
    registry._http_client.cache_clear()


def _with_bypass(monkeypatch, value: str) -> None:
    """Set the bypass list the way a real shell does: both spellings, no proxy configured."""
    monkeypatch.setattr(os, "environ", {**os.environ, "NO_PROXY": value, "no_proxy": value})


def test_the_bracket_form_is_rewritten_and_everything_else_is_left_alone():
    changed = envnet.normalize_proxy_bypass({"NO_PROXY": "localhost,[::1],redis"})
    assert changed == [("NO_PROXY", "localhost,[::1],redis", "localhost,::1,redis")], (
        "the rewrite must name what it touched: the message an operator reads is built from "
        "this, and a silent edit to a proxy variable is the thing being fixed here")
    for untouched in ("localhost,redis", ".example.com,10.0.0.0/8", "localhost,[::1]:8080", ""):
        env: dict = {"NO_PROXY": untouched}
        assert envnet.normalize_proxy_bypass(env) == [] and env == {"NO_PROXY": untouched}, (
            f"{untouched!r} holds no bracket whose meaning is unchanged by removing it, so the "
            "door must not edit it")


def test_both_spellings_of_the_variable_are_read(monkeypatch):
    # POSIX tooling exports the upper case form and some HTTP stacks read the lower one; an
    # operator who sets both must not get a client that consulted only the unfixed half.
    lower = envnet.normalize_proxy_bypass({"no_proxy": "[::1]"})
    assert lower == [("no_proxy", "[::1]", "::1")]
    assert envnet.PROXY_BYPASS_VARS == ("NO_PROXY", "no_proxy")


def test_the_windows_bypass_list_builds_a_client(monkeypatch):
    """The regression, in one line: this construction is what used to raise InvalidURL."""
    _with_bypass(monkeypatch, WINDOWS_BYPASS)
    client = envnet.client(timeout=5)
    try:
        assert isinstance(client, httpx.AsyncClient)
    finally:
        pass  # no await: nothing was opened, so there is nothing to drain


def test_the_value_the_repository_ships_its_operators_still_builds(monkeypatch):
    """``.env.example`` documents a bypass list; the code that reads it has to agree with it.

    Read from the file rather than copied, so a later edit to the example is measured against
    the same parser the service uses. The shipped form is already bracket-free -- which is why
    nobody noticed the crash from the documentation side.
    """
    text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    m = re.search(r"^NO_PROXY=(.+)$", text, re.M)
    assert m, ".env.example no longer documents NO_PROXY, yet the compose files still pass it"
    assert m.group(1).strip() == SHIPPED_BYPASS
    _with_bypass(monkeypatch, m.group(1).strip())
    assert isinstance(envnet.client(), httpx.AsyncClient)


def test_what_cannot_be_translated_is_refused_with_the_variable_named(monkeypatch):
    _with_bypass(monkeypatch, UNREADABLE_BYPASS)
    with pytest.raises(envnet.ProxyEnvError) as raised:
        envnet.client()
    sentence = str(raised.value)
    assert "NO_PROXY" in sentence and UNREADABLE_BYPASS in sentence, (
        f"the refusal has to say which variable and what it holds: {sentence!r}")
    assert "brackets" in sentence, (
        "and the shape that works, because 'Invalid port' is not an instruction")


def test_an_unreadable_environment_costs_readiness_a_boolean_not_a_500(monkeypatch,
                                                                        cleared_client_cache):
    _with_bypass(monkeypatch, UNREADABLE_BYPASS)
    with pytest.raises(envnet.ProxyEnvError):
        registry._http_client()
    named = SimpleNamespace(llm_provider="openai_compat", app_env="dev", llm_api_key="k",
                            llm_base_url="https://relay.invalid/v1", llm_model="m",
                            llm_max_retries=0)
    assert registry.llm_ready(named) is False, (
        "/health asks the factory whether it can build what was named; an environment httpx "
        "cannot read is a 'no' the operator can act on, not an exception through the probe")


def test_the_route_behind_the_closed_door_answers_503_instructively(monkeypatch,
                                                                    cleared_client_cache):
    """The other half of the same failure: what a caller reads.

    ``_buildable`` protects the probe; nothing protected the AI routes, because the raise
    happens below every route's own ``try``, inside the factory. Without the handler this
    test installs, the reader gets FastAPI's bare 500 and httpx's ``Invalid port: ':1]'`` --
    a server error that blames the server for the operator's shell.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core import errors

    _with_bypass(monkeypatch, UNREADABLE_BYPASS)
    service = FastAPI()
    errors.register_refusal_handlers(service)

    @service.get("/under-the-door")
    async def _route():
        registry._http_client()  # what every provider call does before it can speak
        return {"ok": True}

    with TestClient(service, raise_server_exceptions=False) as probe:
        answer = probe.get("/under-the-door")
    assert answer.status_code == 503, (
        f"an environment the door cannot read is not the caller's mistake: {answer.status_code} "
        f"{answer.text!r}")
    detail = answer.json()["detail"]
    assert detail["code"] == errors.AI_EGRESS_ENV_UNREADABLE.code
    assert "NO_PROXY" in detail["reason"] and "brackets" in detail["reason"], (
        f"the refusal has to carry the sentence, not merely the fact of it: {detail!r}")

    from app.main import app as shipped

    assert envnet.ProxyEnvError in shipped.exception_handlers, (
        "the handler is registered on the app built here but not on the one that ships, so "
        "every real AI call still answers 500")


def test_the_door_is_the_only_place_the_service_builds_a_client():
    """Zero drift: a second bare construction is a second door with the same flaw.

    Walking ``app/`` rather than listing the two known callers is the point -- the next
    outbound need arrives without reading this file.
    """
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if path.name == "envnet.py":
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "httpx.AsyncClient(" in line and not line.lstrip().startswith("#"):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{n}")
    assert offenders == [], (
        f"{offenders} build an httpx client outside app/core/envnet.py; that is how the "
        "bracketed-bypass failure comes back after this file is green")


def test_the_ingestion_fetch_stands_in_the_same_door():
    """The internal fetch is the call a bypass list protects, so it cannot bypass the door."""
    source = Path(pipeline.__file__).read_text(encoding="utf-8")
    fn = re.search(r"async def _fetch_bytes.*?\n(?=\nasync def |\ndef |\nclass )", source, re.S)
    assert fn, "_fetch_bytes could not be read"
    assert "envnet.client(" in fn.group(0), (
        "_fetch_bytes builds its client outside the door again, which is how a bracketed "
        "NO_PROXY starts failing every ingestion in the fleet")
