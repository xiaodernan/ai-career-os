"""One run must be finalised once, and finalised with the usage it actually spent.

agent_runs is a running total, not a snapshot: finish_run writes
`input_tokens = input_tokens + $3 ... cost_usd = cost_usd + $6`. Two things follow, and both
were missing. Each run must reach a terminal state exactly once — /agents/chat finishes
'completed' inside the try and, if the result cannot be handed to the task bus, finishes the
SAME run again as 'failed', re-adding latency and overwriting a run whose work happened. And
the totals must come from somewhere: the copilot turn (the priciest path in the product, up to
eight model calls) passes only a latency, so the rollup columns stayed at zero while
ai_usage_events held every token — the dashboard and activity page read the zero.
"""

import pytest

import app.core.db as db
from app.db import observability

RUN = "11111111-1111-1111-1111-111111111111"
LEDGER = (1200, 340, 60, 0.0421)


class SqlCapture:
    def __init__(self):
        self.calls = []

    async def execute(self, query, *args):
        self.calls.append((" ".join(query.split()), args))
        return "UPDATE 1"

    async def fetchrow(self, query, *args):
        self.calls.append((" ".join(query.split()), args))
        return LEDGER

    def updates(self):
        return [c for c in self.calls if c[0].startswith("UPDATE agent_runs")]

    def ledger_reads(self):
        return [c for c in self.calls if "ai_usage_events" in c[0]]


@pytest.fixture()
def cap(monkeypatch):
    c = SqlCapture()
    monkeypatch.setattr(db, "execute", c.execute)
    monkeypatch.setattr(db, "fetchrow", c.fetchrow)
    return c


async def test_finish_only_lands_on_a_run_that_is_still_open(cap):
    await observability.finish_run(RUN, "failed", error="boom")

    sql, _args = cap.updates()[0]
    guard = sql.split("WHERE", 1)[-1]
    assert "status NOT IN" in guard, (
        "a second finish of the same run must not land: the totals accumulate"
    )
    # both terminal values, matching the only two states this service writes
    assert "'completed'" in guard and "'failed'" in guard


async def test_the_accumulating_columns_stay_accumulating(cap):
    """The guard is the fix; turning += into = would silently lose every earlier write."""
    await observability.finish_run(RUN, "completed", in_tok=120, out_tok=340, cached=60,
                                   cost=0.01, latency_ms=900)

    sql, args = cap.updates()[0]
    for column in ("input_tokens", "output_tokens", "cached_tokens", "cost_usd", "latency_ms"):
        assert f"{column}={column}+" in sql.replace(" ", ""), f"{column} no longer accumulates"
    assert args[2:7] == (120, 340, 60, 0.01, 900)


async def test_the_guard_is_narrower_than_the_whole_table(cap):
    """`WHERE id=$1` must survive: a predicate that forgets it would finalise every run."""
    await observability.finish_run(RUN, "completed")

    sql, args = cap.updates()[0]
    assert "id=$1::uuid" in sql.split("WHERE", 1)[-1]
    assert args[0] == RUN


async def test_a_run_that_reported_no_usage_is_totalled_from_its_own_events(cap):
    await observability.finish_run(RUN, "completed", latency_ms=900)

    assert len(cap.ledger_reads()) == 1, "the rollup must be read from the ledger"
    assert cap.ledger_reads()[0][1] == (RUN,)
    _sql, args = cap.updates()[0]
    assert args[2:6] == LEDGER, "the run's real usage must reach the rollup columns"


async def test_explicit_usage_from_the_caller_is_not_queried_or_double_counted(cap):
    await observability.finish_run(RUN, "completed", in_tok=10, out_tok=5)

    assert not cap.ledger_reads(), "a caller that owns the figures must not also pull the ledger"
    _sql, args = cap.updates()[0]
    assert args[2:4] == (10, 5)


async def test_a_run_with_nothing_recorded_totals_zero(cap, monkeypatch):
    async def empty(query, *args):
        return (0, 0, 0, 0.0)

    monkeypatch.setattr(db, "fetchrow", empty)

    await observability.finish_run(RUN, "failed", error="provider down")

    _sql, args = cap.updates()[0]
    assert args[2:6] == (0, 0, 0, 0.0)
    assert args[1] == "failed"


async def test_create_run_still_opens_with_the_writable_status(cap):
    """If creation ever stops writing 'running', the guard above blocks every finish."""
    await observability.create_run("22222222-2222-2222-2222-222222222222", "career", "chat")

    sql, _args = cap.calls[0]
    assert "'running'" in sql, "new runs must start in the one status the guard admits"
