"""Two dependency failures at once — the fault-tolerance shape of the stress brief.

``_suppressed`` merges two "do not re-enqueue yet" reads (the dead-letter guard
and the backoff queue). Both are optimisations over the DB scan, so when either
one fails it must fail OPEN honestly: no exception escapes, no plausible-looking
list of ids is invented, the other source is not blanked, and the failure is
logged with a traceback rather than swallowed. No DB, Redis, Docker, LLM or
socket — only asyncio and two tiny fake objects.
"""

from __future__ import annotations

import asyncio
import logging

from app.ops import embed_workers


class _DownGuard:
    enabled = True

    async def active(self) -> set[str]:
        raise RuntimeError("dlq key unreadable")


class _DownQueue:
    async def parked_ids(self) -> set[str]:
        raise RuntimeError("zset read failed")


class _HealthyGuard:
    enabled = True

    async def active(self) -> set[str]:
        return {"real-cooldown-id"}


def test_both_sources_down_suppress_nothing_and_log_both(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="ops.embed_workers"):
        out = asyncio.run(embed_workers._suppressed(_DownQueue(), _DownGuard()))

    # An outage costs suppression, never recall: the honest fallback is the
    # empty set, not a guessed list or an exception that breaks the producer.
    assert out == set()
    msgs = [r.message for r in caplog.records if r.name == "ops.embed_workers"]
    assert any("dlq guard active()" in m for m in msgs)
    assert any("parked_ids()" in m for m in msgs)
    assert all(r.exc_info for r in caplog.records if r.name == "ops.embed_workers")


def test_one_source_down_does_not_blank_the_other(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="ops.embed_workers"):
        out = asyncio.run(embed_workers._suppressed(_DownQueue(), _HealthyGuard()))

    # The reads are independent: a dead queue must not erase the guard's real
    # cooldown ids, which would re-open the retry storm for the healthy source.
    assert out == {"real-cooldown-id"}
    msgs = [r.message for r in caplog.records if r.name == "ops.embed_workers"]
    assert any("parked_ids()" in m for m in msgs)
