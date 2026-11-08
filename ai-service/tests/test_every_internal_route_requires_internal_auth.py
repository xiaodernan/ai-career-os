"""Every `/internal/*` route must require the internal auth dependency.

The backend calls ai-service's internal surface with a shared secret; nothing in that
namespace is meant to be reachable without it. A route added under `/internal` that
forgets `Depends(require_internal)` silently opens an unauthenticated control plane
endpoint. This gate walks the live dependency tree and fails if any internal route
lacks the dependency.
"""

from fastapi.routing import APIRoute

from app.core.deps import require_internal
from app.main import app
from tests.test_internal_contract import _flat_routes


def _has_dep(dependant, fn) -> bool:
    if getattr(dependant, "call", None) is fn:
        return True
    for dep in getattr(dependant, "dependencies", []) or []:
        if _has_dep(dep, fn):
            return True
    return False


def test_every_internal_route_requires_internal_auth() -> None:
    routes = [r for r in _flat_routes() if isinstance(r, APIRoute) and r.path.startswith("/internal")]
    assert len(routes) >= 50, (
        f"expected >=50 internal routes, found {len(routes)} — the inventory may be misread"
    )
    missing = [r.path for r in routes if not _has_dep(r.dependant, require_internal)]
    assert not missing, f"internal routes missing require_internal: {sorted(missing)}"
