"""Registered API route paths must be well-formed.

Path hygiene (leading slash, no double slashes, no trailing slash except root) is
cheap to enforce and prevents subtle routing/client mismatches. This gate walks the
live flattened route inventory.
"""

from fastapi.routing import APIRoute

from tests.test_internal_contract import _flat_routes


def test_api_route_paths_are_well_formed() -> None:
    bad = []
    for route in _flat_routes():
        if not isinstance(route, APIRoute):
            continue
        path = route.path
        if not path.startswith("/"):
            bad.append((path, "missing leading /"))
        if "//" in path:
            bad.append((path, "double slash"))
        if path != "/" and path.endswith("/"):
            bad.append((path, "trailing slash"))
    assert not bad, f"malformed route paths: {bad}"
