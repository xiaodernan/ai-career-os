"""Every /internal/* route must refuse an unauthenticated request at request time.

The dependency-tree gate (`test_every_internal_route_requires_internal_auth`) proves
the auth dependency is *wired*; this drives the live app with TestClient and proves
each route actually *answers* 401 without the token — no reaching a handler, no
touching the database.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute

from app.main import app
from tests.test_internal_contract import _flat_routes

client = TestClient(app, raise_server_exceptions=False)

DUMMY = "00000000-0000-0000-0000-0000000000dd"


def _executable_path(path: str) -> str:
    out = path
    for _ in range(4):
        if "{" not in out:
            break
        start = out.index("{")
        end = out.index("}", start)
        out = out[:start] + DUMMY + out[end + 1 :]
    return out


internal_routes = [
    r for r in _flat_routes()
    if isinstance(r, APIRoute) and r.path.startswith("/internal")
]


def test_internal_route_count_is_large_enough_to_be_meaningful() -> None:
    assert len(internal_routes) >= 50, f"expected >=50 internal routes, got {len(internal_routes)}"


@pytest.mark.parametrize("route", internal_routes, ids=lambda r: f"{sorted(r.methods)[:1]} {r.path}")
def test_route_refuses_unauthenticated(route: APIRoute) -> None:
    # Use every method the route declares; each one must answer 401, not 200/4xx/5xx.
    for method in sorted(route.methods):
        path = _executable_path(route.path)
        response = client.request(method, path)
        assert response.status_code == 401, f"{method.upper()} {path} -> {response.status_code} (expected 401)"
