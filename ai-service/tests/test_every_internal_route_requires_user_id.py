"""Every /internal/* route must refuse a request that carries the token but not X-User-Id.

`require_internal` validates the shared internal token, then demands `X-User-Id`:
without it the caller cannot be scoped to the data it touches, so the route answers
400 before any handler runs. This drives the live app and asserts 400 for every
`/internal` route and every declared method — no database, no side effects.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute

from app.core.config import get_settings
from app.main import app
from tests.test_internal_contract import _flat_routes

TOKEN = get_settings().internal_api_token
DUMMY = "00000000-0000-0000-0000-0000000000dd"
client = TestClient(app, raise_server_exceptions=False)


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


@pytest.mark.parametrize("route", internal_routes, ids=lambda r: f"{sorted(r.methods)[:1]} {r.path}")
def test_route_refuses_missing_user_id(route: APIRoute) -> None:
    for method in sorted(route.methods):
        path = _executable_path(route.path)
        response = client.request(method, path, headers={"X-Internal-Token": TOKEN})
        assert response.status_code == 400, f"{method.upper()} {path} -> {response.status_code} (expected 400)"
