"""Deployment preflight (forward Epic 18.1, offline).

A production deploy has a handful of failure modes that are invisible until traffic
arrives: the offline providers are still selected, the internal token is still the
repo's published default (so anyone can call ``/internal/*``), the database URL still
points at the dev password, or the LLM key is empty. Each of those boots fine and
fails badly.

This module answers "is this configuration safe to run?" as a *pure* function over a
settings object or dict, so the answer is unit-testable without a database, a network,
or a running server. ``python -m app.ops.preflight`` runs it against the live settings
and exits non-zero on any blocking failure, which is what a deploy script gates on.

Two severities:

* ``fail`` -- must not ship (offline providers in prod, the default token, dev DB creds,
  a missing API key). ``ok`` is false when any ``fail`` is present.
* ``warn`` -- legal but suspicious (not running as prod, a localhost backend URL).

The known-default constants below are asserted against ``Settings``'s real defaults by
the test suite, so a change to config.py cannot silently make a stale default look safe.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

# The published defaults from app/core/config.py. Compared by the preflight to spot a
# deploy that never overrode them; the test suite pins these against Settings().
DEFAULT_INTERNAL_TOKEN = "shared-secret-between-backend-and-ai-service"
DEFAULT_DATABASE_URL = "postgresql://career_os:dev_pg_pass_9f3k@localhost:5432/career_os"

PROVIDERS_NEEDING_KEY = {"openai_compat", "openai", "anthropic"}


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    severity: str  # "fail" | "warn"
    detail: str


def _get(settings, name: str, default=""):
    if isinstance(settings, dict):
        return settings.get(name, default)
    return getattr(settings, name, default)


def _embedding_key(settings) -> str:
    return (_get(settings, "embedding_api_key", "")
            or _get(settings, "llm_api_key", ""))


def _is_prod(settings) -> bool:
    return str(_get(settings, "app_env", "dev")).lower() == "prod"


def _check(name: str, ok: bool, severity: str, detail: str) -> Check:
    return Check(name=name, ok=ok, severity=severity, detail=detail)


def run_preflight(settings) -> dict:
    """Return ``{ok, checks, failures, warnings}`` for a settings object or dict."""
    prod = _is_prod(settings)
    llm = str(_get(settings, "llm_provider", "")).lower()
    embed = str(_get(settings, "embedding_provider", "")).lower()
    token = str(_get(settings, "internal_api_token", ""))
    db_url = str(_get(settings, "database_url", ""))
    backend_url = str(_get(settings, "backend_base_url", ""))
    pool_min = _get(settings, "db_pool_min", 0)
    pool_max = _get(settings, "db_pool_max", 0)

    checks: list[Check] = []

    checks.append(_check(
        "app_env_is_prod", prod, "warn",
        "running as prod" if prod else f"app_env is {_get(settings, 'app_env')!r}, not 'prod'"))

    # offline providers are a dev/test convenience and are refused in prod
    checks.append(_check(
        "llm_provider_not_mock", not (prod and llm == "mock"), "fail",
        "real LLM provider" if llm != "mock" else "LLM_PROVIDER=mock (offline) is not shippable"))
    checks.append(_check(
        "embedding_provider_not_hash", not (prod and embed == "hash"), "fail",
        "real embedding provider" if embed != "hash"
        else "EMBEDDING_PROVIDER=hash (offline) is not shippable"))

    # the published default token means every internal route is effectively public
    checks.append(_check(
        "internal_token_overridden", not (prod and token == DEFAULT_INTERNAL_TOKEN), "fail",
        "internal token is the published default -- /internal/* would be unauthenticated"
        if (prod and token == DEFAULT_INTERNAL_TOKEN) else "internal token is set"))

    # the dev database password must never reach prod
    checks.append(_check(
        "database_url_not_default", not (prod and db_url == DEFAULT_DATABASE_URL), "fail",
        "database URL is the dev default (dev_pg_pass_9f3k)"
        if (prod and db_url == DEFAULT_DATABASE_URL) else "database URL is overridden"))

    # a provider that needs a key must have one (embedding falls back to the LLM key)
    llm_key_missing = prod and llm in PROVIDERS_NEEDING_KEY and not _get(settings, "llm_api_key")
    checks.append(_check(
        "llm_api_key_present", not llm_key_missing, "fail",
        "LLM key is empty for a keyed provider" if llm_key_missing else "LLM key present or not required"))
    embed_key_missing = prod and embed in PROVIDERS_NEEDING_KEY and not _embedding_key(settings)
    checks.append(_check(
        "embedding_api_key_present", not embed_key_missing, "fail",
        "embedding key is empty for a keyed provider" if embed_key_missing
        else "embedding key present or not required"))

    checks.append(_check(
        "backend_url_not_localhost",
        not (prod and "localhost" in backend_url), "warn",
        "backend URL still points at localhost"
        if (prod and "localhost" in backend_url) else "backend URL is routable"))

    checks.append(_check(
        "db_pool_sane", pool_max >= pool_min, "fail",
        f"db_pool_max ({pool_max}) < db_pool_min ({pool_min})" if pool_max < pool_min
        else f"pool {pool_min}..{pool_max}"))

    failures = [c for c in checks if not c.ok and c.severity == "fail"]
    warnings = [c for c in checks if not c.ok and c.severity == "warn"]
    return {
        "ok": not failures,
        "checks": [asdict(c) for c in checks],
        "failures": [asdict(c) for c in failures],
        "warnings": [asdict(c) for c in warnings],
    }


def main(argv: list[str] | None = None) -> int:
    from app.core.config import get_settings

    report = run_preflight(get_settings())
    print(json.dumps(report, indent=2))
    if report["ok"]:
        print(f"preflight: OK ({len(report['warnings'])} warning(s))")
        return 0
    print(f"preflight: {len(report['failures'])} blocking failure(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
