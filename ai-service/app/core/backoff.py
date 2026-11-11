"""Exponential backoff with full jitter, as a pure function (Epic 144).

The problem
-----------
Before Epic 144, a failed job on the Redis work queue is re-queued with ``XADD``
straight back onto the main stream. ``claim()`` uses ``XREADGROUP >``, which reads
*every not-yet-delivered entry immediately* — so the retry is claimed again on the
very next tick, with zero delay. With ``max_deliveries=5``, a transient provider
blip that would have healed in 30 seconds can burn all five attempts and be
dead-lettered within five ticks. The DlqGuard cooldown (Epic 139) only covers the
*post*-dead-letter window; nothing paced the retries *before* it.

The fix has two parts, and both matter:

* **Exponential ceiling** ``min(cap, base * 2**(attempts-1))`` — give a recovering
  provider ever-longer breathing room instead of hammering it at a fixed rate.
* **Full jitter** — draw the actual delay uniformly from ``[0, ceiling]``. This is
  the part people get wrong. A *fixed* backoff (even an exponential one) makes all
  workers that failed on the same blip retry at the *same* instant, producing a
  synchronised **retry storm** (a thundering herd) that keeps the provider down.
  Full jitter de-correlates them: with N workers, retries spread across the whole
  window, so the provider sees a roughly constant trickle, not N spikes. This is
  the result from AWS's "Exponential Backoff And Jitter" (Marc Brooker, 2015) and
  it is why jitter is not decoration — a pure exponential without it can be *worse*
  than no backoff under load.

Why a pure function
-------------------
No clock of its own (the caller passes ``attempts`` and injects ``rng``), no Redis
client, no I/O, no dependency on ``resp`` or ``workqueue``. Every branch — the
ceiling clamp, the cap, the jitter bounds, the overflow guard — is offline-testable
without a fake pool or a real Redis. The one impure seam (``random.random``) is
injectable, so tests pin the *shape* of the distribution deterministically.
"""
from __future__ import annotations

import random
from typing import Callable

# Defaults are measurement constants, NOT config knobs (the same discipline as
# Epic 143): a deployment tunes the *base* via Settings, while the cap and the
# shape of the curve live here so they cannot drift between callers.
DEFAULT_CAP_MS = 30_000            # never sleep longer than 30s before a retry
DEFAULT_BASE_MS = 500              # first retry draws from [0, 500ms]
_MAX_SHIFT = 40                    # 2**40 > 1e12ms (~31y); beyond this the cap wins

Rng = Callable[[], float]


def ceiling_ms(attempts: int, *, base_ms: int, cap_ms: int = DEFAULT_CAP_MS) -> int:
    """The deterministic upper bound ``min(cap, base * 2**(attempts-1))``.

    ``attempts`` is the number of *prior* failed deliveries (1 = the first retry),
    and is clamped to at least 1. ``base_ms <= 0`` means "backoff disabled" and
    returns 0, so a caller can fold this in unconditionally when the feature is
    off. ``cap_ms <= 0`` likewise disables it rather than returning a negative
    delay (a negative delay would schedule a job in the past — a silent lie).

    The exponent is capped at ``_MAX_SHIFT`` *before* the shift. Without that
    guard, a poison job whose ``attempts`` field were corrupted to a huge number
    would make ``base << attempts`` allocate an enormous integer and burn CPU —
    a denial of service from a malformed message. Past the shift where the cap
    already wins, clamping changes nothing about the returned ceiling.
    """
    n = max(1, int(attempts))
    if base_ms <= 0 or cap_ms <= 0:
        return 0
    shift = min(n - 1, _MAX_SHIFT)
    return min(cap_ms, base_ms * (1 << shift))


def full_jitter_ms(attempts: int, *, base_ms: int, cap_ms: int = DEFAULT_CAP_MS,
                   rng: Rng | None = None) -> int:
    """The actual delay: a uniform draw from ``[0, ceiling_ms(...)]``.

    Full jitter (not "equal +/− jitter") is what breaks retry synchronisation:
    two workers with the same ``attempts`` and different draws retry at different
    times. The draw is clamped to ``[0.0, 1.0]`` so a hostile or buggy ``rng``
    cannot return a negative delay (schedule in the past) or a delay above the
    ceiling (silently defeat the cap). ``rng`` defaults to ``random.random`` but is
    injectable so the interval can be pinned in tests.
    """
    cap = ceiling_ms(attempts, base_ms=base_ms, cap_ms=cap_ms)
    if cap <= 0:
        return 0
    draw = (rng or random.random)()
    try:
        u = float(draw)
    except (TypeError, ValueError):
        u = 0.0
    u = min(max(u, 0.0), 1.0)          # [0.0, 1.0], hostile-rng safe
    return int(u * cap)
