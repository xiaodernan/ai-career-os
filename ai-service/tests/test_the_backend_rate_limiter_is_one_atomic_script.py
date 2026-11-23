"""The backend's per-minute bucket is one atomic Redis decision, not four round trips.

The gateway's edge budget (RedisBudget) has held its ceiling in one Lua script since
Epic 120, but the backend's sliding-window limiter still issued ZREMRANGEBYSCORE,
ZCOUNT, ZADD and EXPIRE as four separate commands. Two callers — production runs three
backend replicas behind many Tomcat threads — could both read ``live < limit``, both add,
and exceed the configured ceiling under exactly the concurrency it exists to bound.

This is a source gate, not a socket test: it reads the limiter as text and asserts the
decision lives in one ``redis.execute(script, ...)`` call over one key, with the trim,
count and add inside the script. A future refactor back to ``opsForZSet().count(...)`` in
the admission path reintroduces the race and reddens this file — the same shape the
repo's other "a gate measures the population it can see" checks take. No LLM, no Redis,
no network: it runs in the offline gate sweep.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIMITER = (
    REPO_ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros"
    / "ratelimit" / "RedisSlidingWindowRateLimiter.java"
)


def _source() -> str:
    assert LIMITER.exists(), f"the backend limiter moved: {LIMITER}"
    return LIMITER.read_text(encoding="utf-8")


def _method_body(source: str, name: str) -> str:
    """The Java method's body, read between its signature and the next method's javadoc."""
    start = source.index(f"public boolean {name}(")
    end = source.find("/**", start)
    return source[start:end if end > 0 else len(source)]


def test_the_admission_path_uses_one_atomic_script_call():
    src = _source()
    body = _method_body(src, "tryAcquire")
    assert "DefaultRedisScript" in src, "the limiter must declare a RedisScript"
    assert "redis.execute(" in body, "the decision must be one script execution"
    assert body.count("redis.execute(") == 1, "one decision, not a sequence of commands"
    assert "List.of(key)" in body, "one key per bucket"
    # The race was reading the count through opsForZSet in the admission path. It is fine
    # in `remaining` (a separate, non-authoritative status read), but not in tryAcquire.
    assert "opsForZSet()" not in body, "a ZSET read in tryAcquire reopens the race"
    assert "removeRangeByScore" not in body, "the trim must be inside the script, not a round trip"


def test_the_script_carries_the_whole_decision():
    src = _source()
    script = src[src.index("static final String SCRIPT"):src.index("private final StringRedisTemplate")]
    for call in ("ZREMRANGEBYSCORE", "ZCARD", "ZADD", "PEXPIRE"):
        assert call in script, f"the script is missing {call}"
    assert "return 0" in script and "return 1" in script, "the script answers admit/refuse"
    # Five redis.call invocations: trim, count, refusal-TTL, add, admission-TTL.
    assert len(re.findall(r"redis\.call", script)) == 5


def test_fail_open_is_preserved():
    """An outage must not lock users out — the backend's historical contract."""
    body = _method_body(_source(), "tryAcquire")
    assert "catch (RuntimeException" in body, "Redis failure must be caught"
    assert body.count("return true") >= 2, "both the empty-answer and the outage paths fail open"
