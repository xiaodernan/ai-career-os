"""The cache verdict must tell the truth, especially when the number is 0.

Epic 118 proved a second identical question makes zero model calls -- but only by
installing a MemoryCache by hand. Every shipped default is ``cache_backend=off``,
so that saving has never run. And ``describe()`` has always reported counters that
nothing read. Epic 143's read half folds those counters into a verdict, and this
file pins the honesty of that fold.

The central discipline (same as Epic 140's "0 is ambiguous"): **a hit rate of 0
is three different states** and must never collapse into one:

* ``off`` -- never enabled, no hot path to judge;
* ``cold`` -- enabled, nobody has asked yet;
* ``ineffective`` -- enabled, real lookups, not one hit (pure write cost).

Everything here is a pure function over a dict: no cache, no Redis, no clock, no
I/O. Every branch is offline-verifiable.
"""

import pytest

from app.features import cache_health as h

MIN = h.DEFAULT_MIN_LOOKUPS


def _snap(*, backend="memory", enabled=True, hits=0, misses=0, writes=0,
          errors=0, evictions=0, l2_hits=0, **extra):
    data = {
        "backend": backend,
        "enabled": enabled,
        "stats": {"hits": hits, "misses": misses, "writes": writes,
                  "errors": errors, "evictions": evictions, "l2_hits": l2_hits},
    }
    data.update(extra)
    return data


# ------------------------------------------------------- 0 is three different states
def test_an_off_cache_is_not_reported_as_healthy_or_effective():
    """The shipped default is off; reporting 'healthy' would claim a saving that
    was never switched on. It is information, not an error."""
    verdict, alerts = h.classify(_snap(backend="off", enabled=False), mode="off")
    assert verdict == "off"
    assert alerts and "never been" in alerts[0].lower()


def test_an_enabled_cache_with_no_lookups_is_cold_not_ineffective():
    """Zero lookups is expected on a fresh deployment; it says nothing about
    whether the cache wastes writes. 'cold' is honest, 'ineffective' is a lie."""
    verdict, alerts = h.classify(_snap(hits=0, misses=0, writes=7), mode="memory")
    assert verdict == "cold"
    assert alerts


def test_a_cache_that_is_consulted_but_never_hits_is_ineffective():
    """The expensive case: real lookups, zero answers, pure write cost. Calling
    this 'healthy because there are no errors' is the dangerous lie."""
    verdict, alerts = h.classify(_snap(hits=0, misses=MIN + 5, writes=MIN + 5),
                                mode="memory")
    assert verdict == "ineffective"
    assert any("write" in a.lower() for a in alerts)


def test_a_low_rate_below_the_warn_line_is_ineffective():
    verdict, _ = h.classify(_snap(hits=2, misses=MIN + 8), mode="memory")
    assert verdict == "ineffective"


# ------------------------------------------------------- the good path
def test_a_warm_cache_with_a_high_hit_rate_is_healthy():
    verdict, alerts = h.classify(_snap(hits=MIN, misses=2), mode="memory")
    assert verdict == "healthy"
    assert alerts == []


def test_a_hit_rate_exactly_on_the_warn_line_is_healthy():
    """Boundary: >= the warn line passes, no off-by-one that flatters nobody."""
    verdict, _ = h.classify(_snap(hits=10, misses=10), mode="memory",
                            hit_rate_warn=0.5)
    assert verdict == "healthy"


# ------------------------------------------------------- small samples are not victories
def test_two_lookups_one_hit_is_still_cold_not_healthy():
    """1/2 = 50% would pass the rate line, but two calls prove nothing. A warm-up
    call must not declare the cache a success."""
    verdict, _ = h.classify(_snap(hits=1, misses=1), mode="memory")
    assert verdict == "cold"


def test_min_lookups_is_tunable_and_respected():
    verdict, _ = h.classify(_snap(hits=4, misses=1), mode="memory", min_lookups=3)
    assert verdict == "healthy"


# ------------------------------------------------------- the write-side is never ignored
def test_writes_are_reported_even_when_the_rate_is_high():
    """The report carries writes alongside hits: a cache cannot hide its cost
    behind a good-looking rate."""
    report = h.health_report(_snap(hits=MIN, misses=2, writes=MIN + 9), mode="memory")
    assert report["cache"]["writes"] == MIN + 9
    assert report["verdict"] == "healthy"


# ------------------------------------------------------- transport faults -> unknown
def test_backend_errors_are_unknown_not_healthy():
    verdict, alerts = h.classify(_snap(hits=MIN, misses=2, errors=1), mode="redis")
    assert verdict == "unknown"
    assert any("error" in a.lower() for a in alerts)


def test_a_tripped_breaker_is_unknown_with_an_actionable_alert():
    snap = _snap(hits=MIN, misses=2, breaker={"trips": 1, "open": True,
                                              "cooldown_s": 5.0})
    verdict, alerts = h.classify(snap, mode="redis")
    assert verdict == "unknown"
    assert any("breaker" in a.lower() for a in alerts)


# ------------------------------------------------------- layered: the shared layer matters
def test_a_tripped_shared_redis_is_seen_even_when_the_front_layer_looks_clean():
    """A layered cache's root counters are logical and can look healthy while its
    only shared layer is down. The fold must walk the tree, not the root."""
    snap = {
        "backend": "layered", "enabled": True,
        "stats": {"hits": MIN, "misses": 2, "errors": 0, "writes": MIN + 2},
        "local": {"backend": "memory", "enabled": True,
                  "stats": {"hits": MIN, "misses": 2, "errors": 0}},
        "shared": {"backend": "redis", "enabled": True,
                   "stats": {"hits": 0, "misses": 0, "errors": 3},
                   "breaker": {"trips": 2, "open": True, "cooldown_s": 5.0}},
    }
    report = h.health_report(snap, mode="redis")
    assert report["verdict"] == "unknown"
    assert report["cache"]["errors"] == 3, "shared-layer errors were not aggregated"
    assert report["cache"]["breaker_trips"] == 2


def test_l2_hits_are_reported_as_the_fleet_cheap_signal():
    """l1 hits help one process; l2 hits mean another replica computed it. Only
    the second makes a fleet cheap, so the raw figure must travel with the verdict."""
    snap = _snap(hits=MIN, misses=2, l2_hits=6)
    report = h.health_report(snap, mode="redis")
    assert report["cache"]["l2_hits"] == 6
    assert report["verdict"] == "healthy"


# ------------------------------------------------------- malformed input is unknown, never healthy
@pytest.mark.parametrize("snap", [
    None,
    "not a dict",
    {},                              # no stats
    {"enabled": True, "stats": 42},  # stats not a dict
    {"enabled": True, "stats": {"hits": "lots", "misses": None}},
])
def test_an_unreadable_snapshot_is_unknown_not_healthy(snap):
    verdict, alerts = h.classify(snap, mode="redis")
    assert verdict == "unknown"
    assert alerts


def test_health_report_never_raises_on_garbage_and_keeps_the_full_shape():
    report = h.health_report({"enabled": True, "stats": {"hits": "x"}}, mode="redis")
    assert report["verdict"] == "unknown"
    assert {"verdict", "alerts", "backend", "enabled", "cache",
            "single_flight", "thresholds"} <= set(report)


# ------------------------------------------------------- vocabulary and shape
def test_every_verdict_is_in_the_declared_vocabulary():
    for snap in (_snap(enabled=False), _snap(), _snap(hits=MIN, misses=2),
                 _snap(errors=1), _snap(hits=1, misses=1)):
        assert h.classify(snap, mode="memory")[0] in h.VERDICTS


def test_the_report_carries_single_flight_facts_alongside_the_rate():
    """The nine followers that waited are the stampede the cache absorbed; that
    number must be visible next to the hit rate, not lost."""
    snap = _snap(hits=MIN, misses=2,
                 single_flight={"leaders": 3, "joined": 9, "inflight": 0})
    report = h.health_report(snap, mode="memory")
    assert report["single_flight"] == {"leaders": 3, "joined": 9, "inflight": 0}
