"""Fail-open collection for the read-only cache health endpoint (Epic 143).

``read_health()`` is the single seam between the HTTP layer and the cache's own
``describe()``. It returns the exact dict ``cache_health.health_report`` produces,
so the endpoint adds nothing but auth -- and a future backend scraper folds the
same numbers into a Micrometer gauge.

Design constraints honoured here:

* **No I/O, no pool.** Unlike the work queue (whose numbers live in Redis and need
  a short-lived connection), every number here is a process-local counter the
  cache already keeps. Reading it is a dict copy, so the endpoint cannot add
  latency to the hot path or fail because Redis is down. A dead Redis shows up
  as ``breaker_trips`` in the counters, not as a connection attempt here.
* **Two truths, both reported.** ``mode`` comes straight from
  ``Settings.cache_backend`` (the operator's *intent*, one author). ``describe()``
  reports what the process *actually built*. They can differ -- a ``redis``
  request with an unusable URL degrades to memory -- and hiding that difference
  is how a fleet thinks it shares a cache when each replica computes alone. The
  pure fold decides the verdict; this seam refuses to reconcile the two away.
* **Total fail-open.** ``describe()` raises, a malformed counter, a future
  refactor -- every path returns a well-formed *unknown* report, never raises
  into the request. An observer that can 500 is an observer that can take down
  the service it is meant to watch.
"""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.features import cache_health as health
from app.rag import caching

log = logging.getLogger("ops.cache_status")


def _mode() -> str:
    """The operator's configured cache backend, read from its one author."""
    try:
        return str(getattr(get_settings(), "cache_backend", "off") or "off").strip().lower()
    except Exception:
        return "unknown"


def read_health() -> dict:
    """Collect the cache's own describe() and return the health report dict.

    Completely fail-open: the pure health function is total over dicts, and any
    exception in collection degrades to an *unknown* report rather than 500ing
    the control-plane endpoint.
    """
    mode = _mode()
    try:
        snapshot = caching.describe()
    except Exception as e:
        log.warning("cache health read failed (%s); reporting unknown", e)
        report = health.health_report({}, mode=mode)
        report["observation_error"] = f"describe-failed:{type(e).__name__}"
        return report

    report = health.health_report(snapshot, mode=mode)
    # Report the backend the process actually built alongside the configured mode.
    # A mismatch (configured redis, running memory) is the honest, actionable fact.
    actual = snapshot.get("backend") if isinstance(snapshot, dict) else None
    if actual and str(actual).strip().lower() != mode:
        report["degraded_to"] = str(actual).strip().lower()
    return report
