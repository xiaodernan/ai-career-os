"""The observer heartbeat is the liveness signal Redis cannot provide.

An idle work-queue stream looks identical whether a healthy consumer just drained
it or the consumer died an hour ago. ``queue_observer`` is the single-writer slot
the embed loop stamps after each complete pass; the read-only ops endpoint folds
its freshness into the health verdict (Epic 140). These tests pin the properties
that make it a trustworthy witness rather than a second source of truth:

* a missing heartbeat is ``None`` (never ticked), not an exception;
* ``snapshot_heartbeat`` returns a *copy* -- a reader cannot mutate the slot;
* counts are coerced to non-negative ints (a bad stat cannot corrupt the witness);
* ``now`` is injectable so freshness is deterministic offline;
* ``reset`` clears everything; and the loop actually wires ``record_tick`` after a
  complete pass (source contract), so the endpoint is not watching a slot nobody
  writes.

No Redis, no clock racing, no new dependency: this is an in-memory module.
"""

import pytest

from app.ops import queue_observer


@pytest.fixture(autouse=True)
def _clean():
    queue_observer.reset()
    yield
    queue_observer.reset()


def test_a_loop_that_never_ran_has_no_heartbeat():
    assert queue_observer.snapshot_heartbeat() is None


def test_record_tick_stamps_wall_clock_now_and_throughput():
    queue_observer.record_tick(delivered=4, reclaimed=1, dead_lettered=2, now=1000.0)
    hb = queue_observer.snapshot_heartbeat()
    assert hb == {"last_tick": 1000.0, "delivered": 4,
                  "reclaimed": 1, "dead_lettered": 2}


def test_the_default_clock_is_a_number_near_now():
    import time
    before = time.time()
    queue_observer.record_tick(delivered=1)
    after = time.time()
    last = queue_observer.snapshot_heartbeat()["last_tick"]
    assert before <= last <= after


def test_snapshot_is_a_copy_that_cannot_mutate_the_slot():
    queue_observer.record_tick(delivered=3, now=500.0)
    hb = queue_observer.snapshot_heartbeat()
    hb["delivered"] = 999
    hb["last_tick"] = 0
    again = queue_observer.snapshot_heartbeat()
    assert again["delivered"] == 3 and again["last_tick"] == 500.0


def test_counts_are_clamped_to_non_negative_ints():
    queue_observer.record_tick(delivered=-5, reclaimed="7", dead_lettered=None, now=1.0)
    hb = queue_observer.snapshot_heartbeat()
    assert hb["delivered"] == 0
    assert hb["reclaimed"] == 7
    assert hb["dead_lettered"] == 0


def test_each_tick_replaces_the_last_one_not_appends():
    queue_observer.record_tick(delivered=1, now=10.0)
    queue_observer.record_tick(delivered=9, now=20.0)
    hb = queue_observer.snapshot_heartbeat()
    assert hb["last_tick"] == 20.0 and hb["delivered"] == 9


def test_reset_clears_the_heartbeat():
    queue_observer.record_tick(delivered=4, now=1.0)
    queue_observer.reset()
    assert queue_observer.snapshot_heartbeat() is None


def test_the_distributed_loop_stamps_a_heartbeat_after_a_complete_pass():
    """Source contract: the ops endpoint must be watching a slot that is written.

    Pinning the call site (rather than running the 60s loop) keeps this offline and
    deterministic while still catching the regression where someone removes the
    heartbeat entirely and the endpoint silently reports 'stalled' forever.
    """
    import inspect
    from app.ops import embed_workers

    src = inspect.getsource(embed_workers.embed_loop_distributed)
    assert "queue_observer.record_tick(" in src
    # It must be stamped on the successful path, with the drain's real stats.
    assert "delivered=stats.delivered" in src
    assert "dead_lettered=stats.dead_lettered" in src


def test_record_tick_has_no_redis_or_await_dependency():
    """A heartbeat write is pure in-memory state -- it cannot fail on Redis down."""
    assert not inspect_iscoroutine(queue_observer.record_tick)


def inspect_iscoroutine(fn):
    import inspect
    return inspect.iscoroutinefunction(fn)
