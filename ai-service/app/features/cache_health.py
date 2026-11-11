"""Operational health for the RAG cache (internal-only, read half).

The cache writes a lot of numbers -- hits, misses, writes, evictions, L2 hits,
single-flight joins, breaker trips -- and ``app.rag.caching.describe()`` already
reports them. Until this module, *nothing read those numbers into an answer an
operator or an alert could act on*. They were written and shipped, but never
folded into "is this cache actually earning its keep?". This is that fold.

The honest problem this module exists to name: **a hit rate of 0 means three
different things**, and collapsing them is a dangerous lie::

    off          caching was never switched on (``cache_backend=off``, the default).
                 There is no hot path to judge -- every question recomputes.
    cold         caching is on, but nobody has asked anything yet. Zero is expected
                 and says nothing about whether the cache works.
    ineffective  caching is on and has served real lookups, but none of them hit.
                 This is the expensive one: every write is pure cost, the entries
                 are dead weight, and calling it "healthy because 0 errors" hides
                 a cache that is taxing the product instead of helping it.

Epic 118 proved *in a test* that a second identical question makes zero model
calls. That proof installs a ``MemoryCache`` by hand. In every shipped default
(``cache_backend=off``) the optimisation has never run. Reporting that honestly is
the point of the ``off`` verdict: it is information, not an error, but it stops a
dashboard from claiming a saving that was never switched on.

Precedence (first match wins) -- the ladder from "cannot be helped" to "fine"::

    off          backend disabled; no hot path to judge.
    unknown      the reading itself is untrustworthy (errors/breaker tripped, or
                 the snapshot is malformed). Reported before any rate, because
                 calling an unobservable cache "healthy" is the dangerous lie.
    cold         enabled, but zero lookups: nothing to measure yet.
    ineffective  enabled, enough lookups to measure, hit rate below the warn line:
                 the cache is being consulted and is not paying for its writes.
    healthy      enabled, enough lookups, hit rate at or above the warn line.

Pure functions over plain dicts -- no cache client, no clock of its own, no new
dependency -- so every branch is offline-verifiable. The same shape is what the
``/internal/ops/cache`` endpoint returns and what a future backend Micrometer
gauge can scrape, so the number a dashboard shows and the verdict an alert fires
on cannot drift apart.
"""

from __future__ import annotations

VERDICTS = frozenset({
    "off", "unknown", "cold", "ineffective", "healthy",
})

# A rate over fewer lookups than this is noise: one hit in two calls is 50%, which
# would look "healthy" while being statistically meaningless. Keep it small enough
# that a dev laptop reaches it in a session, large enough that a single warm-up
# call cannot declare victory.
DEFAULT_MIN_LOOKUPS = 20
# Below this hit rate the cache is consulted more often than it answers; the writes
# are not earning back the round trips. A warm RAG cache should clear this easily.
DEFAULT_HIT_RATE_WARN = 0.50


def _int(value) -> int:
    """Coerce an untrusted reading to a non-negative int (0 on nonsense)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return n if n > 0 else 0


def _num(value) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f


def classify(snapshot: dict, *, mode: str, min_lookups: int = DEFAULT_MIN_LOOKUPS,
             hit_rate_warn: float = DEFAULT_HIT_RATE_WARN) -> tuple[str, list[str]]:
    """The verdict + actionable alerts, given a ``caching.describe()``-shaped dict.

    ``snapshot`` is the raw describe output; it may be malformed (a cache that
    failed to build, a future refactor). A snapshot we cannot read is ``unknown``,
    never ``healthy`` -- the same discipline Epic 140 applies to an unreadable
    Redis. Alerts are sentences an operator can act on, never bare metric names.
    """
    backend = (mode or "").strip().lower()

    if not isinstance(snapshot, dict):
        return "unknown", [
            "The cache health observation could not read a snapshot; cache state "
            "is unknown. Check the /internal/rag/cache endpoint directly."
        ]

    stats = snapshot.get("stats")
    if not isinstance(stats, dict):
        return "unknown", [
            "The cache snapshot has no readable counters; cache state is unknown."
        ]

    # A counter whose value is not a number is *unreadable*, not zero. Coercing a
    # malformed `hits`/`misses` to 0 would report a broken cache as "cold" (nobody
    # has asked yet) -- the same lie as calling an unobservable queue healthy. Guard
    # the two fields the whole rate is derived from before any rate is computed.
    for field in ("hits", "misses"):
        if field in stats and not isinstance(stats[field], (int, float)):
            return "unknown", [
                f"The cache counter '{field}' is not a number "
                f"({type(stats[field]).__name__}); the hit rate cannot be trusted. "
                f"Check the cache backend's describe() output."
            ]

    # `enabled` is a fact the backend reports about itself, not a guess from the
    # mode string. A `redis` request with an unusable URL degrades to memory but
    # stays enabled; only NullCache (off) reports enabled=False.
    if not bool(snapshot.get("enabled", False)):
        return "off", [
            f"Cache backend is '{backend or 'off'}' -- caching has never been "
            f"switched on in this deployment. Epic 118's 'the second question is "
            f"free' optimisation is not running: every question recomputes the "
            f"full pipeline. This is the shipped default, reported so a dashboard "
            f"cannot claim a saving that was never enabled."
        ]

    alerts: list[str] = []
    # Errors are a transport fact, and in a layered cache they are recorded on
    # the *shared* Redis layer, not on LayeredCache's own logical counters. Sum
    # the whole describe tree or a dead Redis looks like a clean run of misses.
    errors = _total_errors(snapshot)
    trips = _breaker_trips(snapshot)
    if errors or trips:
        if errors:
            alerts.append(
                f"{errors} cache backend error(s) were counted. The cache fails "
                f"open, so answers are still correct, but those lookups silently "
                f"became recomputes."
            )
        if trips:
            alerts.append(
                f"{trips} Redis breaker trip(s): a failed connection made the "
                f"cache serve misses for a cooldown window instead of one timeout "
                f"per request. Inspect REDIS_URL / the shared layer."
            )
        return "unknown", alerts

    hits = _int(stats.get("hits"))
    misses = _int(stats.get("misses"))
    lookups = hits + misses
    rate = round(hits / lookups, 4) if lookups else 0.0

    if lookups == 0:
        return "cold", [
            f"Cache backend '{backend}' is enabled but has served 0 lookups. "
            f"Nothing has asked the cache a question yet, so there is no hit rate "
            f"to judge. If this persists under real traffic, check that retrieval "
            f"actually goes through the cache seam."
        ]

    if lookups < max(1, int(min_lookups)):
        return "cold", [
            f"Cache backend '{backend}' has served only {lookups} lookups "
            f"(needs {min_lookups} before a hit rate means anything). Too early "
            f"to claim the cache is working or wasting writes."
        ]

    if rate < hit_rate_warn:
        alerts.append(
            f"{lookups} lookups at a {round(rate * 100, 1)}% hit rate, below the "
            f"{round(hit_rate_warn * 100, 1)}% warn line. The cache is being "
            f"consulted but is not answering often enough to pay for its "
            f"{_int(stats.get('writes'))} write(s); check key stability, TTL, and "
            f"whether invalidation is firing every request."
        )
        return "ineffective", alerts

    return "healthy", alerts


def _walk(snapshot: dict):
    """Yield each layer's describe dict, front to back, then the root itself.

    ``LayeredCache.describe()`` nests its ``local`` / ``shared`` backends. A
    Redis breaker trip or a RESP error is recorded on the shared layer, so a fold
    that only reads the root's logical counters would report a clean hit rate
    while the fleet's only shared cache is down -- the exact lie Epic 143 exists
    to prevent.
    """
    for key in ("local", "shared"):
        child = snapshot.get(key)
        if isinstance(child, dict):
            yield from _walk(child)
    yield snapshot


def _breaker_trips(snapshot: dict) -> int:
    """Sum breaker trips across every layer (a layered shared layer included)."""
    total = 0
    for layer in _walk(snapshot):
        total += _int(layer.get("breaker_trips"))
        breaker = layer.get("breaker")
        if isinstance(breaker, dict):
            total += _int(breaker.get("trips"))
    return total


def _total_errors(snapshot: dict) -> int:
    """Sum backend errors across every layer, not just the root's logical stats."""
    total = 0
    for layer in _walk(snapshot):
        stats = layer.get("stats")
        if isinstance(stats, dict):
            total += _int(stats.get("errors"))
    return total


def health_report(snapshot: dict, *, mode: str,
                  min_lookups: int = DEFAULT_MIN_LOOKUPS,
                  hit_rate_warn: float = DEFAULT_HIT_RATE_WARN) -> dict:
    """Fold a ``caching.describe()`` reading into one report.

    The raw numbers and the single-flight / embedding facts travel alongside the
    verdict so a dashboard can chart them and an alert can name the exact value
    that tripped it. The verdict is a summary, never the only copy of the facts.
    """
    snap = snapshot if isinstance(snapshot, dict) else {}
    stats = snap.get("stats") if isinstance(snap.get("stats"), dict) else {}
    hits = _int(stats.get("hits"))
    misses = _int(stats.get("misses"))
    lookups = hits + misses
    rate = round(hits / lookups, 4) if lookups else 0.0

    verdict, alerts = classify(snap, mode=mode, min_lookups=min_lookups,
                               hit_rate_warn=hit_rate_warn)
    flight = snap.get("single_flight") if isinstance(snap.get("single_flight"), dict) else {}
    return {
        "verdict": verdict,
        "alerts": alerts,
        "backend": (mode or "").strip().lower(),
        "enabled": bool(snap.get("enabled", False)),
        "cache": {
            "lookups": lookups,
            "hits": hits,
            "misses": misses,
            "writes": _int(stats.get("writes")),
            "errors": _total_errors(snap),
            "evictions": _int(stats.get("evictions")),
            "l2_hits": _int(stats.get("l2_hits")),
            "hit_rate": rate,
            "breaker_trips": _breaker_trips(snap),
        },
        "single_flight": {
            "leaders": _int(flight.get("leaders")),
            "joined": _int(flight.get("joined")),
            "inflight": _int(flight.get("inflight")),
        },
        "thresholds": {
            "min_lookups": max(1, int(min_lookups)),
            "hit_rate_warn": hit_rate_warn,
        },
    }
