"""Operational health for the Redis-Streams embed work queue (internal-only).

The queue and the dead-letter cooldown guard both *write* state into Redis, but
until this module nothing *read* it back into an answer an operator or an alert
can act on. This is the read half: a deterministic fold of three independent
observations into one verdict + a list of actionable alerts.

Three observations, deliberately kept separate because they answer different
questions and fail in different ways:

* ``snapshot`` -- live Redis readings (``XLEN`` / ``XPENDING``) with an ``ok``
  bit. ``ok=False`` means Redis itself is unreachable, so every number in the
  snapshot is a fail-open zero and *none of them can be trusted*.
* ``guard`` -- the dead-letter cooldown: how many job ids are suppressed, and
  for how long. A non-zero count means poison jobs were seen recently and are
  being held back from re-injection.
* ``heartbeat`` -- an in-memory snapshot the consumer loop writes each tick.
  This is the liveness signal that Redis cannot give: an idle stream looks
  identical whether a healthy worker just drained it or the worker died an hour
  ago. Freshness (``now - last_tick``) is what tells them apart.

The verdict precedence encodes the honest answer to "is this queue working?"::

    disabled   the work queue backend is off; there is nothing to watch (info).
    unknown    Redis is unreachable -- the numbers are zeroes we cannot trust.
               Reported before anything else that uses those numbers, because
               calling an unobservable queue "healthy" is the dangerous lie.
    stalled    Redis reads fine but the consumer heartbeat is missing or stale:
               a dead worker behind an idle-looking queue.
    degraded   a live consumer, but dead letters are sitting in the DLQ or job
               ids are cooling down: poison is being contained, not resolved.
    backlogged a live, clean consumer, but PEL/stream depth exceeds the warn
               line: work is arriving faster than it is being drained.
    healthy    live consumer, no poison, no meaningful backlog.

Epic 144 adds ``delayed_len`` to the snapshot: jobs parked in the backoff ZSET,
waiting out a retry window. It is reported as a first-class number but, like
``stream_len``, deliberately does NOT change the verdict — a parked job is
expected work-in-waiting, not degradation. It exists so the delay set can never
become a silent black hole (a job there is on no stream/PEL/DLQ); a sustained
climb with a fresh heartbeat is a chart/operator signal, not a false alarm.

Pure functions over plain dicts -- no Redis client, no clock of its own (``now``
is passed in), no new dependency -- so every branch is offline-verifiable. The
same shape is what the ``/internal/ops/workqueue`` endpoint returns and what a
future backend Micrometer gauge can scrape, so the number a dashboard shows and
the verdict an alert fires on cannot drift apart.
"""

from __future__ import annotations

VERDICTS = frozenset({
    "disabled", "unknown", "stalled", "degraded", "backlogged", "healthy",
})

DEFAULT_STALE_AFTER_S = 300   # 5 min without a tick = the loop has stopped
DEFAULT_BACKLOG_WARN = 32     # ~2 embed batches (batch=16) still pending


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


def freshness(heartbeat: dict | None, *, now: float,
              stale_after_s: float = DEFAULT_STALE_AFTER_S) -> dict:
    """How old is the consumer's last tick, and is it still alive?

    ``heartbeat`` is ``{"last_tick": <epoch>, "delivered": <int>,
    "dead_lettered": <int>}`` or None when the loop has never run. A missing or
    malformed tick is ``fresh=False`` with ``age_s=None`` -- "we have no liveness
    signal", which the verdict treats as stalled, not as healthy.

    ``age_s`` is clamped at 0 so a clock skew (a heartbeat stamped in the future)
    cannot make a dead worker look young.
    """
    hb = heartbeat if isinstance(heartbeat, dict) else {}
    last = _num(hb.get("last_tick"))
    if last is None:
        return {"fresh": False, "age_s": None, "last_tick": None,
                "stale_after_s": stale_after_s}
    age = max(0.0, now - last)
    return {
        "fresh": age <= stale_after_s,
        "age_s": round(age, 1),
        "last_tick": last,
        "stale_after_s": stale_after_s,
    }


def classify(snapshot: dict, guard: dict, fresh: dict, *, mode: str,
             backlog_warn: int = DEFAULT_BACKLOG_WARN) -> tuple[str, list[str]]:
    """The verdict + actionable alerts, given already-normalised readings.

    Precedence is the docstring's ladder. Alerts are sentences an operator can
    act on (or an alert rule can carry), never bare metric names.
    """
    backend = (mode or "").strip().lower()
    if backend != "redis":
        return "disabled", [
            "Work queue backend is not 'redis'; job embedding uses the "
            "single-process DB scan. There is no consumer group to watch."
        ]

    alerts: list[str] = []

    # Redis unreachable: every number from the snapshot is a fail-open zero and
    # must not be interpreted. Report this before the freshness / depth checks.
    if not snapshot.get("ok", False):
        if not fresh["fresh"]:
            alerts.append(
                "Redis is unreachable AND the consumer heartbeat is stale or "
                "missing: the embed pipeline is not observable and may be stopped."
            )
        else:
            alerts.append(
                "Redis is unreachable; queue depth and DLQ counts cannot be "
                "read. The consumer heartbeat is still fresh, so the worker is "
                "alive but flying blind (it falls open to the DB scan)."
            )
        return "unknown", alerts

    # Redis is readable from here on, so the depth numbers mean something.
    if not fresh["fresh"]:
        age = fresh["age_s"]
        age_txt = "missing" if age is None else f"{age}s old"
        alerts.append(
            f"Consumer heartbeat is {age_txt} (stale after "
            f"{fresh['stale_after_s']}s). The queue looks idle but no worker has "
            f"reported a tick: check that embed_loop_distributed is running."
        )
        return "stalled", alerts

    dlq_len = _int(snapshot.get("dlq_len"))
    cooled = _int(guard.get("cooled_count"))
    pending = _int(snapshot.get("pending"))
    stream_len = _int(snapshot.get("stream_len"))

    if dlq_len:
        alerts.append(
            f"{dlq_len} dead-lettered job(s) are sitting in the DLQ. They failed "
            f"past the delivery limit and are suppressed by the cooldown guard; "
            f"inspect them, fix the underlying rows, then release their cooldown."
        )
    if cooled:
        alerts.append(
            f"{cooled} job id(s) are cooling down and will not be re-injected by "
            f"the producer until their window lapses (or an operator releases "
            f"them). Non-zero means recent poison; it self-heals on expiry."
        )
    if dlq_len or cooled:
        return "degraded", alerts

    if pending >= backlog_warn:
        alerts.append(
            f"{pending} message(s) are pending in the consumer group's PEL "
            f"(warn line {backlog_warn}). Work is not being drained fast enough."
        )
        return "backlogged", alerts

    # stream_len is intentionally NOT a health signal on its own. XACK removes a
    # message from the PEL, not the stream, and the producer re-injects still-NULL
    # jobs each tick, so a non-empty stream is normal for a healthy queue. Only
    # PEL depth (pending) means "work not yet done".
    return "healthy", alerts


def health_report(snapshot: dict, guard: dict, heartbeat: dict | None, *, mode: str,
                  now: float, stale_after_s: float = DEFAULT_STALE_AFTER_S,
                  backlog_warn: int = DEFAULT_BACKLOG_WARN) -> dict:
    """Fold the three observations into one report: verdict, alerts, raw readings.

    The raw numbers are returned alongside the verdict so a dashboard can chart
    them and an alert can name the exact value that tripped it -- the verdict is
    a summary, never the only copy of the facts.
    """
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    guard = guard if isinstance(guard, dict) else {}
    fresh = freshness(heartbeat, now=now, stale_after_s=stale_after_s)
    verdict, alerts = classify(snapshot, guard, fresh, mode=mode,
                               backlog_warn=backlog_warn)
    return {
        "verdict": verdict,
        "alerts": alerts,
        "freshness": fresh,
        "queue": {
            "stream_len": _int(snapshot.get("stream_len")),
            "pending": _int(snapshot.get("pending")),
            "dlq_len": _int(snapshot.get("dlq_len")),
            "dlq_enabled": bool(snapshot.get("dlq_enabled")),
            # Epic 144: the backoff delay set is first-class raw observability so a
            # parked job is never a silent black hole. Like stream_len, it is
            # reported but does NOT by itself flip the verdict: a normal backoff
            # window is expected work-in-waiting, not degradation. A persistent
            # climb is something an operator charts, not an alert we cry wolf on.
            "delayed_len": _int(snapshot.get("delayed_len")),
            "delayed_enabled": bool(snapshot.get("delayed_enabled")),
            "ok": bool(snapshot.get("ok", False)),
        },
        "guard": {
            "enabled": bool(guard.get("enabled")),
            "cooldown_s": _int(guard.get("cooldown_s")),
            "cooled_count": _int(guard.get("cooled_count")),
        },
        "backend": (mode or "").strip().lower(),
    }
