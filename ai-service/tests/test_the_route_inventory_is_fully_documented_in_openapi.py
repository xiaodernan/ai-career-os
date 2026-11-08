"""Every route the ai-service registers is an operation the OpenAPI schema carries.

The browser-surface audit (`test_browser_surface_audit.py`) asks which served routes
have a browser reader, and the API-doc gates ask whether the documentation rows match
the controllers. Both are *served-surface* questions. This gate is the other half of the
same coin: the surface the *model and the ops scripts* see. A route that serves but whose
OpenAPI entry is missing is a route the generated client, the eval harness's typed client,
and anyone reading the schema cannot name — and a silent gap in the schema is how a route
gets built without ever being observed.
"""

from fastapi.routing import APIRoute

from app.main import app
from tests.test_internal_contract import _flat_routes

_OPERATIONS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def test_every_registered_route_has_an_openapi_operation() -> None:
    routes = _flat_routes()
    assert len(routes) > 0, (
        f"the flat route inventory is empty -- the census cannot be measured, and an empty "
        f"inventory must not be taken as a clean bill of health"
    )
    spec = app.openapi()
    paths = spec.get("paths") or {}
    missing: list[tuple[str, str]] = []
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        method = next((m.lower() for m in sorted(route.methods) if m.lower() in _OPERATIONS), None)
        if method is None or method not in paths.get(route.path, {}):
            missing.append((method or sorted(route.methods)[0], route.path))
    assert not missing, (
        f"registered routes with no OpenAPI operation: {missing}; "
        f"the schema is thinner than the router"
    )
