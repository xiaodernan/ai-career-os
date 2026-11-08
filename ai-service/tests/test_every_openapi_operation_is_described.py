"""Every OpenAPI operation should carry a summary or description.

The schema is the machine-readable contract for the internal surface (clients, eval
harnesses, ops tooling). An operation with no summary/description is a route that
exists but explains nothing — a documentation gap that tends to persist because
nothing fails when it is empty. The route-inventory gate ensures operations exist;
this ensures they are described.
"""

from app.main import app

_HTTP = {"get", "post", "put", "patch", "delete"}


def test_every_openapi_operation_has_summary_or_description() -> None:
    spec = app.openapi()
    paths = spec.get("paths") or {}
    assert paths, "OpenAPI paths are empty"
    missing = []
    for path, methods in paths.items():
        for method, op in (methods or {}).items():
            if method.lower() not in _HTTP or not isinstance(op, dict):
                continue
            if not (op.get("summary") or op.get("description")):
                missing.append(f"{method.upper()} {path}")
    assert not missing, f"OpenAPI operations missing summary/description: {missing}"
