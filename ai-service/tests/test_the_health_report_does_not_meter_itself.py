"""Epic 176 — the meter must not meter itself.

`POST /internal/features/health-report` reads the run history and answered with a
run row of its own for every poll: the live route minted a ``monitoring``-agent row
per fetch, so every dashboard view inflated the next view's ``totalRuns`` and left a
zero-token row for the report's own arithmetic to count — the numbers looked like
more activity the more they were read.

This file pins the fix at the route boundary, through the same harness the HTTP
contract tests use: with the run-id short-circuit *absent*, a spy on
``observability.create_run`` proves the health report opens no run, and proves the
spy works by watching a route that legitimately needs one open it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db import observability
from app.main import app

TOKEN = get_settings().internal_api_token
USER = "00000000-0000-0000-0000-0000000000aa"
RUN = "00000000-0000-0000-0000-0000000000bb"
AUTH = {"X-Internal-Token": TOKEN, "X-User-Id": USER}

client = TestClient(app)


@pytest.fixture()
def spy(monkeypatch):
    """Count the runs opened and swallow the writes, without a database."""
    opened: list[dict] = []

    async def count_run(*args, **kwargs):
        opened.append({"args": args, "kwargs": kwargs})
        return RUN

    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(observability, "create_run", count_run)
    monkeypatch.setattr(observability, "finish_run", noop)
    return opened


def test_the_health_report_mints_no_run(spy):
    # No X-Run-Id: the short-circuit that used to hide the mint from the harness.
    r = client.post("/internal/features/health-report",
                    json={"runs": [{"status": "completed", "latency_ms": 10,
                                    "input_tokens": 1000, "cached_tokens": 900}]},
                    headers=AUTH)
    assert r.status_code == 200
    assert spy == [], ("the report opened a run for reading the runs it lists; "
                       f"the dashboard's own polls would count as activity: {spy}")


def test_the_report_still_answers_with_identical_shape_and_numbers(spy):
    r = client.post("/internal/features/health-report",
                    json={"runs": [{"status": "completed", "latency_ms": 10,
                                    "input_tokens": 6000, "cached_tokens": 5000},
                                   {"status": "failed", "latency_ms": 2000,
                                    "input_tokens": 4000, "cached_tokens": 3000}]},
                    headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"summary", "regressions", "alerts", "verdict"}
    summary = body["summary"]
    assert summary["totalRuns"] == 2
    assert summary["totalCachedTokens"] == 8000
    assert summary["cacheHitRatio"] == round(8000 / 10000, 4)


def test_a_route_that_needs_a_run_still_opens_one(spy):
    # Positive control for the spy: a job the engine does real work for (a deterministic
    # dedupe over a batch) does open a run. If this fails, the spy is blind, not the fix.
    r = client.post("/internal/features/dedupe-jobs",
                    json={"postings": [
                        {"id": "a", "company": "C", "title": "T", "location": "L"},
                        {"id": "b", "company": "C", "title": "T", "location": "L"},
                    ]},
                    headers=AUTH)
    assert r.status_code == 200
    assert spy, "the dedupe ran without opening the run the board tracks"
