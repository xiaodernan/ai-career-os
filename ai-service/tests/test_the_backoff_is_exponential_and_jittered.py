"""The retry delay must give a recovering provider breathing room, not a herd.

This pins the pure-function backoff of Epic 144. The two claims that stop the
retries from being either too aggressive or still-synchronised:

* the *ceiling* grows exponentially but is capped — a transient blip self-heals
  while a persistent outage does not turn into an hour-long sleep, and a corrupted
  ``attempts`` field cannot make ``base << attempts`` allocate a giant integer;
* the *actual delay* is a uniform draw over ``[0, ceiling]`` — full jitter, which
  is what de-correlates N workers that failed on the same blip. A fixed value
  (even an exponential one) would make them all retry on the same tick and keep
  the provider down: the retry storm this Epic exists to break.

Every branch is deterministic here: no Redis, no clock, no real randomness (an
injectable rng). The impure scheduling is pinned separately in the queue tests.
"""

import pytest

from app.core import backoff


# --------------------------------------------------------------- the ceiling curve
def test_ceiling_grows_exponentially_with_the_attempt_number():
    base = 100
    assert [backoff.ceiling_ms(a, base_ms=base, cap_ms=10**9)
            for a in (1, 2, 3, 4, 5)] == [100, 200, 400, 800, 1600]


def test_ceiling_is_capped_so_a_persistent_failure_never_sleeps_forever():
    # Past the cap, every larger attempt returns exactly the cap.
    assert backoff.ceiling_ms(1, base_ms=500, cap_ms=2000) == 500
    assert backoff.ceiling_ms(2, base_ms=500, cap_ms=2000) == 1000
    assert backoff.ceiling_ms(3, base_ms=500, cap_ms=2000) == 2000
    assert backoff.ceiling_ms(9, base_ms=500, cap_ms=2000) == 2000


def test_attempt_zero_or_negative_is_treated_as_the_first_retry():
    for a in (0, -1, -999):
        assert backoff.ceiling_ms(a, base_ms=100, cap_ms=10**6) == 100


def test_a_huge_attempts_field_cannot_blow_up_the_shift_guard():
    """A poison message with attempts=10**9 must not allocate a giant integer.

    The cap wins long before the shift does; clamping the exponent keeps the
    computation O(1) regardless of what a corrupted/deliberately hostile field
    says. This is a malformed-input denial-of-service guard.
    """
    assert backoff.ceiling_ms(10**9, base_ms=500, cap_ms=30_000) == 30_000
    assert backoff.full_jitter_ms(10**9, base_ms=500, cap_ms=30_000,
                                  rng=lambda: 1.0) == 30_000


# --------------------------------------------------------------- off is honest zero
def test_base_zero_means_off_even_for_large_attempts():
    for a in (1, 5, 10**6):
        assert backoff.ceiling_ms(a, base_ms=0) == 0
        assert backoff.full_jitter_ms(a, base_ms=0, rng=lambda: 0.5) == 0


def test_nonpositive_cap_disables_backoff_instead_of_scheduling_in_the_past():
    # A negative cap must not leak a negative (already-due) delay; off is 0.
    for cap in (0, -1, -100):
        assert backoff.ceiling_ms(3, base_ms=500, cap_ms=cap) == 0
        assert backoff.full_jitter_ms(3, base_ms=500, cap_ms=cap,
                                      rng=lambda: 0.5) == 0


# --------------------------------------------------------------- full jitter bounds
def test_full_jitter_spans_the_whole_ceiling_not_around_a_fixed_value():
    """Full jitter is [0, ceiling], NOT ceiling/2 ± ceiling/4.

    The extremes matter: a jitter that never reaches 0 keeps a small delay from
    ever being drawn, and one that never reaches the ceiling never gives the
    provider the full breathing room the cap allows.
    """
    kw = dict(attempts=3, base_ms=100, cap_ms=10**6)  # ceiling = 400
    assert backoff.full_jitter_ms(rng=lambda: 0.0, **kw) == 0
    assert backoff.full_jitter_ms(rng=lambda: 0.5, **kw) == 200
    assert backoff.full_jitter_ms(rng=lambda: 0.999, **kw) == 399
    assert backoff.full_jitter_ms(rng=lambda: 1.0, **kw) == 400


def test_equal_attempts_with_different_draws_retry_at_different_times():
    """The anti-herd claim: identical failures no longer retry on one tick."""
    kw = dict(attempts=2, base_ms=1000, cap_ms=30_000)  # ceiling 2000ms
    draws = (0.05, 0.2, 0.5, 0.8, 0.95)
    delays = [backoff.full_jitter_ms(rng=lambda u=u: u, **kw) for u in draws]
    assert len(set(delays)) == len(draws), "retries must de-synchronise"
    assert all(0 <= d <= 2000 for d in delays)


def test_full_jitter_is_deterministic_when_rng_is_injected():
    seq = iter([0.1, 0.9, 0.3])
    got = [backoff.full_jitter_ms(3, base_ms=100, cap_ms=10**6,
                                  rng=lambda: next(seq)) for _ in range(3)]
    assert got == [40, 360, 120]  # ceiling 400 * each draw


def test_default_rng_stays_inside_the_ceiling():
    """Without injection the real RNG must still respect the bounds."""
    for _ in range(200):
        d = backoff.full_jitter_ms(4, base_ms=250, cap_ms=30_000)  # ceiling 2000
        assert 0 <= d <= 2000


# --------------------------------------------------------------- hostile rng / input
@pytest.mark.parametrize("bad", [-5.0, -0.01, 1.01, 99.0])
def test_a_hostile_rng_cannot_escape_the_ceiling(bad):
    d = backoff.full_jitter_ms(3, base_ms=100, cap_ms=10**6, rng=lambda: bad)
    assert 0 <= d <= 400


@pytest.mark.parametrize("bad", [None, "nonsense", object()])
def test_a_non_numeric_rng_result_degrades_to_zero_not_a_crash(bad):
    # A broken rng yields a 0 delay (retry next tick) rather than raising into
    # drain() and losing the job's retry path entirely.
    assert backoff.full_jitter_ms(3, base_ms=100, cap_ms=10**6,
                                  rng=lambda: bad) == 0


def test_delay_is_always_an_int_in_milliseconds():
    for a in (1, 3, 7):
        d = backoff.full_jitter_ms(a, base_ms=333, cap_ms=30_000,
                                   rng=lambda: 0.37)
        assert isinstance(d, int)
        assert 0 <= d <= backoff.ceiling_ms(a, base_ms=333)
