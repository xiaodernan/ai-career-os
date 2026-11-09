"""The edge and the domain must not disagree about the browser's contract (Epic 90).

The gateway copies two policies the backend already owns: the CORS answer to a
preflight, and the rule that decides whether an inbound `X-Request-Id` is quotable.
Copying is cheap; keeping the copies equal is not, because neither process imports the
other's constants -- a one-line edit on either side would leave a browser that passes
one door and fails the other, and no unit test in either module would notice.

This gate is the noticing. It reads both sources as text, which is deliberate: the
backend is servlet-shaped and the gateway is reactive, so there is no shared type to
assert against. The values are the contract, and the contract is short enough to parse.

It also confirms that the one route the edge declares covers the API the docs publish.
A gateway that forwards `/api/**` while the API moves under `/api/v2` would answer 404
for every call and still pass its own routing test.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
GATEWAY_YML = ROOT / "gateway/src/main/resources/application.yml"
GATEWAY_ID = ROOT / "gateway/src/main/java/com/careeros/gateway/RequestIdFilter.java"
GATEWAY_GUARD = ROOT / "gateway/src/main/java/com/careeros/gateway/EdgeSurfaceGuard.java"
BACKEND_ID = ROOT / "backend/src/main/java/com/careeros/common/RequestIdFilter.java"
BACKEND_SECURITY = ROOT / "backend/src/main/java/com/careeros/config/SecurityConfig.java"
API_DOC = ROOT / "docs/API.md"


def _gateway_document() -> dict:
    """The base document: the `eureka` profile is a second one (Epic 98)."""
    return next(iter(yaml.safe_load_all(GATEWAY_YML.read_text(encoding="utf-8"))))


def _gateway_cors() -> dict:
    document = _gateway_document()
    global_cors = document["spring"]["cloud"]["gateway"]["server"]["webflux"]["globalcors"]
    configurations = global_cors["cors-configurations"]
    assert "[/**]" in configurations, f"unexpected CORS paths: {sorted(configurations)}"
    return configurations["[/**]"]


def _backend_lists() -> tuple[list[str], list[str], list[str], int]:
    source = BACKEND_SECURITY.read_text(encoding="utf-8")
    request_id_header = re.search(
        r'public static final String HEADER = "([^"]+)"',
        BACKEND_ID.read_text(encoding="utf-8"),
    ).group(1)

    def entries(pattern: str) -> list[str]:
        found = re.search(pattern, source)
        assert found, f"SecurityConfig no longer matches {pattern!r}"
        return [
            request_id_header if part.strip() == "RequestIdFilter.HEADER" else part.strip().strip('"')
            for part in found.group(1).split(",")
            if part.strip()
        ]

    methods = entries(r"setAllowedMethods\(List\.of\(([^)]*)\)\)")
    headers = entries(r"setAllowedHeaders\(List\.of\(([^)]*)\)\)")
    exposed = entries(r"setExposedHeaders\(List\.of\(([^)]*)\)\)")
    max_age = int(re.search(r"setMaxAge\((\d+)L?\)", source).group(1))
    return methods, headers, exposed, max_age


def test_the_two_doors_allow_the_same_verbs():
    cors = _gateway_cors()
    methods, _, _, _ = _backend_lists()
    assert cors["allowed-methods"] == methods, (
        "a browser's preflight must get the same verbs from either door"
    )


def test_the_two_doors_allow_and_expose_the_same_headers():
    cors = _gateway_cors()
    _, headers, exposed, _ = _backend_lists()
    assert cors["allowed-headers"] == headers, (
        "a header the backend accepts must not be refused at the edge"
    )
    assert cors["exposed-headers"] == exposed, (
        "the browser can only quote X-Request-Id if both doors expose it"
    )


def test_the_two_doors_age_the_preflight_the_same_way():
    cors = _gateway_cors()
    _, _, _, max_age = _backend_lists()
    assert cors["max-age"] == max_age


def test_the_two_doors_share_one_definition_of_a_quotable_id():
    def pattern(path: Path) -> str:
        source = path.read_text(encoding="utf-8")
        found = re.search(r'Pattern\.compile\("([^"]+)"\)', source)
        assert found, f"{path.name} no longer declares an ACCEPTED pattern"
        return found.group(1)

    assert pattern(GATEWAY_ID) == pattern(BACKEND_ID), (
        "the edge mints ids the backend would replace, or the other way around; "
        "one request would then have two ids in the logs"
    )


def test_the_edge_covers_every_route_the_api_documents():
    document = _gateway_document()
    route = document["spring"]["cloud"]["gateway"]["server"]["webflux"]["routes"][0]
    assert "Path=/api/**" in route["predicates"]

    public = re.search(r"\|\s*\*\*Public\*\*\s*`([^`]+)`", API_DOC.read_text(encoding="utf-8"))
    assert public, "docs/API.md no longer publishes a Public surface row"
    assert public.group(1).startswith("/api/"), (
        f"the documented API surface {public.group(1)!r} is not under the edge's /api/** route"
    )


def test_the_edge_strips_the_credential_the_backend_accepts():
    """The backend's CORS list admits `X-Internal-Token`; the edge must not relay it.

    The header is a service-to-service credential. The backend accepts it on
    `/api/internal/**`, and that prefix is refused at the edge (below), but a header a
    browser can write must not even arrive at the backend's door: one future route that
    reads it would turn the browser into a service. The strip is asserted by the same
    text the gateway actually runs, not by a comment claiming it.
    """
    document = _gateway_document()
    filters = document["spring"]["cloud"]["gateway"]["server"]["webflux"]["default-filters"]
    headers = _backend_lists()[1]
    assert "X-Internal-Token" in headers, (
        "the backend stopped accepting the internal token; this gate is now describing a "
        "credential that no longer exists"
    )
    assert any(item.strip() == "RemoveRequestHeader=X-Internal-Token" for item in filters), (
        "the backend accepts a header the edge lets a browser write; the edge must remove "
        "it before forwarding"
    )


def test_the_edge_refuses_the_surface_the_backend_declares_internal():
    """The door the edge closes is the door the backend marks internal.

    Two independently edited files agree on one prefix. If the backend moves its
    service-to-service surface and the guard keeps the old one, the new surface is routed
    to the browser while both modules' own tests stay green.
    """
    backend = BACKEND_SECURITY.read_text(encoding="utf-8")
    declared = re.search(r'requestMatchers\("(/api/internal)/\*\*"\)', backend)
    assert declared, "SecurityConfig no longer declares an /api/internal/** surface"

    guard = re.search(r'INTERNAL_PREFIX\s*=\s*"([^"]+)"', GATEWAY_GUARD.read_text(encoding="utf-8"))
    assert guard, "EdgeSurfaceGuard no longer names the prefix it refuses"
    assert guard.group(1) == declared.group(1), (
        f"the edge refuses {guard.group(1)!r} while the backend reserves "
        f"{declared.group(1)!r}: one of the two doors is answering about the other's surface"
    )
