"""One run must be finalised once: agent_runs accumulates, it does not record.

finish_run writes `input_tokens = input_tokens + $3 ... cost_usd = cost_usd + $6`, so the
row is a running total, not a snapshot. That is only correct while each run reaches a
terminal state exactly once. /agents/chat breaks even that: it finishes the run 'completed'
inside the try and then, if the result cannot be handed to the task bus (`out.to_dict()`
raising on a half-populated turn), falls into the except which finishes the SAME run again
as 'failed' — re-adding latency_ms and overwriting a run whose LLM work really did happen.
Nothing in the data layer enforced one-write-per-run; this does.
"""

import pytest

import app.core.db as db
from app.db import observability


class SqlCapture:
    def __init__(self):
        self.calls = []

    async def __call__(self, query, *args):
        self.calls.append((" ".join(query.split()), args))
        return "UPDATE 1"


@pytest.fixture()
def cap(monkeypatch):
    c = SqlCapture()
    monkeypatch.setattr(db, "execute", c)
    return c


async def test_finish_only_lands_on_a_run_that_is_still_open(cap):
    await observability.finish_run("11111111-1111-1111-1111-111111111111", "failed",
                                   error="boom")

    sql, _args = cap.calls[0]
    guard = sql.split("WHERE", 1)[-1]
    assert "status NOT IN" in guard, (
        "a second finish of the same run must not land: the totals accumulate"
    )
    # both terminal values, matching the only two states this service writes
    assert "'completed'" in guard and "'failed'" in guard


async def test_the_accumulating_columns_stay_accumulating(cap):
    """The guard is the fix; turning += into = would silently lose every earlier write."""
    await observability.finish_run("11111111-1111-1111-1111-111111111111", "completed",
                                   in_tok=120, out_tok=340, cached=60, cost=0.01, latency_ms=900)

    sql, args = cap.calls[0]
    for column in ("input_tokens", "output_tokens", "cached_tokens", "cost_usd", "latency_ms"):
        assert f"{column}={column}+" in sql.replace(" ", ""), f"{column} no longer accumulates"
    assert args[2:7] == (120, 340, 60, 0.01, 900)


async def test_the_guard_is_narrower_than_the_whole_table(cap):
    """`WHERE id=$1` must survive: a predicate that forgets it would finalise every run."""
    await observability.finish_run("11111111-1111-1111-1111-111111111111", "completed")

    sql, args = cap.calls[0]
    guard = sql.split("WHERE", 1)[-1]
    assert "id=$1::uuid" in guard
    assert args[0] == "11111111-1111-1111-1111-111111111111"


async def test_create_run_still_opens_with_the_writable_status(cap):
    """If creation ever stops writing 'running', the guard above blocks every finish."""
    await observability.create_run("22222222-2222-2222-2222-222222222222", "career", "chat")

    sql, _args = cap.calls[0]
    assert "'running'" in sql, "new runs must start in the one status the guard admits"
