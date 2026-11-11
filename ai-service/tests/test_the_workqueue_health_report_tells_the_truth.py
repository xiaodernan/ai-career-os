"""The work-queue health verdict must tell the truth, not flatter the queue.

This is the pure-function read half of Epic 140. Three observations -- live Redis
numbers, the dead-letter cooldown, and the consumer's in-memory heartbeat -- fold
into one verdict. The claims pinned here are the ones that stop the report from
lying in the ways a naive "are there pending jobs?" check would:

* an unreadable Redis (fail-open zeroes) is *unknown*, never healthy;
* an idle-looking stream behind a dead/stale consumer is *stalled*, not healthy;
* poison sitting in the DLQ or cooling down is *degraded* even while the consumer
  is alive and the PEL is empty;
* a live, clean queue with a non-empty stream is still *healthy* -- XACK leaves
  entries on the stream and the producer re-injects NULL jobs, so stream depth is
  not a backlog by itself;
* ``backend=off`` is *disabled* (informational), not stalled;
* verdict precedence is deterministic: disabled > unknown > stalled > degraded >
  backlogged > healthy.
"""

import pytest

from app.features import work_queue_health as h


NOW = 1_000_000.0
FRESH_HB = {"last_tick": NOW - 10, "delivered": 4, "dead_lettered": 0}


def _snap(*, ok=True, stream_len=0, pending=0, dlq_len=0, dlq_enabled=True):
    return {"ok": ok, "stream_len": stream_len, "pending": pending,
            "dlq_len": dlq_len, "dlq_enabled": dlq_enabled}


def _guard(*, enabled=True, cooldown_s=900, cooled_count=0):
    return {"enabled": enabled, "cooldown_s": cooldown_s,
            "cooled_count": cooled_count}


def _report(snapshot, guard, hb, *, mode="redis", now=NOW, **kw):
    return h.health_report(snapshot, guard, hb, mode=mode, now=now, **kw)


# --------------------------------------------------------------- the verdict ladder
def test_backend_off_is_disabled_not_stalled():
    r = _report(_snap(), _guard(), None, mode="off")
    assert r["verdict"] == "disabled"
    assert r["alerts"], "disabled is informational but still says what is active"
    assert "single-process" in r["alerts"][0]


def test_an_unreadable_redis_is_unknown_even_with_a_fresh_heartbeat():
    """The dangerous lie: fail-open zeroes read as 'empty healthy queue'."""
    r = _report(_snap(ok=False), _guard(), FRESH_HB)
    assert r["verdict"] == "unknown"
    assert r["freshness"]["fresh"] is True, "worker alive, but queue unobservable"
    assert any("unreachable" in a.lower() for a in r["alerts"])


def test_unreadable_redis_and_stale_heartbeat_says_both():
    r = _report(_snap(ok=False), _guard(), {"last_tick": NOW - 9999})
    assert r["verdict"] == "unknown"  # unknown wins, but the alert names both
    assert any("heartbeat" in a.lower() and "redis" in a.lower()
               for a in r["alerts"])


def test_missing_heartbeat_is_stalled_not_healthy():
    r = _report(_snap(), _guard(), None)
    assert r["verdict"] == "stalled"
    assert any("heartbeat" in a.lower() for a in r["alerts"])


def test_stale_heartbeat_behind_an_idle_queue_is_stalled():
    r = _report(_snap(), _guard(), {"last_tick": NOW - 10_000})
    assert r["verdict"] == "stalled"
    assert r["freshness"]["fresh"] is False


def test_dead_letters_degrade_a_live_consumer():
    r = _report(_snap(dlq_len=3), _guard(), FRESH_HB)
    assert r["verdict"] == "degraded"
    assert any("3 dead-lettered" in a for a in r["alerts"])


def test_cooling_job_ids_degrade_even_when_the_dlq_was_trimmed():
    """MAXLEN trimming can zero dlq_len while cooldown still holds poison ids."""
    r = _report(_snap(dlq_len=0), _guard(cooled_count=2), FRESH_HB)
    assert r["verdict"] == "degraded"
    assert any("cooling" in a.lower() for a in r["alerts"])


def test_a_backlog_beyond_the_warn_line_is_backlogged():
    r = _report(_snap(pending=40), _guard(), FRESH_HB, backlog_warn=32)
    assert r["verdict"] == "backlogged"
    assert any("40" in a and "PEL" in a for a in r["alerts"])


def test_a_clean_live_queue_is_healthy():
    r = _report(_snap(), _guard(), FRESH_HB)
    assert r["verdict"] == "healthy"
    assert r["alerts"] == []


def test_stream_depth_alone_does_not_mean_backlog():
    """XACK removes from the PEL, not the stream; a busy stream is normal."""
    r = _report(_snap(stream_len=500, pending=0), _guard(), FRESH_HB)
    assert r["verdict"] == "healthy"
    assert r["queue"]["stream_len"] == 500


# --------------------------------------------------------------- precedence
def test_precedence_degraded_beats_backlogged():
    """Poison matters more than a backlog; both may be present at once."""
    r = _report(_snap(pending=99, dlq_len=1), _guard(), FRESH_HB)
    assert r["verdict"] == "degraded"


def test_precedence_stalled_beats_degraded():
    r = _report(_snap(dlq_len=1), _guard(), {"last_tick": NOW - 10_000})
    assert r["verdict"] == "stalled"


def test_precedence_unknown_beats_stalled_beats_poison():
    r = _report(_snap(ok=False, dlq_len=9), _guard(cooled_count=9),
                {"last_tick": NOW - 10_000})
    assert r["verdict"] == "unknown"


# --------------------------------------------------------------- freshness detail
def test_freshness_boundary_is_inclusive():
    at = h.freshness({"last_tick": NOW - 300}, now=NOW, stale_after_s=300)
    assert at["fresh"] is True, "exactly at the line is still fresh"
    just_past = h.freshness({"last_tick": NOW - 301}, now=NOW, stale_after_s=300)
    assert just_past["fresh"] is False


def test_future_heartbeat_is_clamped_to_zero_age():
    """Clock skew must not make a heartbeat look younger than now."""
    f = h.freshness({"last_tick": NOW + 500}, now=NOW)
    assert f["age_s"] == 0.0 and f["fresh"] is True


def test_malformed_heartbeat_has_no_liveness_signal():
    for hb in ({"last_tick": "nonsense"}, {"last_tick": None}, {}, "not a dict"):
        f = h.freshness(hb, now=NOW)
        assert f["fresh"] is False and f["age_s"] is None


# --------------------------------------------------------------- honesty / robustness
def test_every_verdict_is_in_the_declared_set():
    cases = [
        _report(_snap(), _guard(), None, mode="off"),
        _report(_snap(ok=False), _guard(), FRESH_HB),
        _report(_snap(), _guard(), None),
        _report(_snap(dlq_len=1), _guard(), FRESH_HB),
        _report(_snap(pending=99), _guard(), FRESH_HB),
        _report(_snap(), _guard(), FRESH_HB),
    ]
    assert {c["verdict"] for c in cases} == h.VERDICTS


def test_raw_readings_are_returned_alongside_the_verdict():
    """A chart/alert needs the exact number, not just the word 'degraded'."""
    r = _report(_snap(stream_len=7, pending=2, dlq_len=3, dlq_enabled=True, ok=True),
                _guard(enabled=True, cooldown_s=600, cooled_count=4), FRESH_HB)
    assert r["queue"] == {"stream_len": 7, "pending": 2, "dlq_len": 3,
                          "dlq_enabled": True, "ok": True}
    assert r["guard"] == {"enabled": True, "cooldown_s": 600, "cooled_count": 4}
    assert r["freshness"]["fresh"] is True
    assert r["backend"] == "redis"


def test_untrusted_readings_are_coerced_to_zero():
    """A None / string / negative from a half-broken reader cannot inflate a count."""
    r = _report(_snap(pending="oops", dlq_len=-1, stream_len=None),
                _guard(cooled_count="many"), FRESH_HB)
    assert r["queue"]["pending"] == 0
    assert r["queue"]["dlq_len"] == 0
    assert r["queue"]["stream_len"] == 0
    assert r["guard"]["cooled_count"] == 0
    assert r["verdict"] == "healthy"


def test_a_non_dict_snapshot_is_treated_as_unreadable():
    r = h.health_report(None, None, FRESH_HB, mode="redis", now=NOW)
    assert r["verdict"] == "unknown"


def test_mode_is_normalised():
    for mode in ("REDIS", " Redis ", "redis"):
        r = _report(_snap(), _guard(), FRESH_HB, mode=mode)
        assert r["verdict"] == "healthy" and r["backend"] == "redis"
