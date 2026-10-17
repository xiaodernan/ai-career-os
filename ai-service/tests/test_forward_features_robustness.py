"""Hostile-input robustness for the forward engines.

This repo has been bitten repeatedly by jsonb nulls and type drift -- a present key whose
value is null, a numeric field arriving as a string. The forward engines consume data the
backend assembles, so a single bad row must *degrade*, never raise and take the whole report
down. These tests push None / {} / wrong types / null fields through every engine and assert
a well-formed result; the two parsers must raise ``ValueError`` (a clear "bad input"), never
leak an ``AttributeError``/``TypeError`` from a ``.encode``/``.get`` on the wrong type.
"""

import pytest

from app.features import analytics, ingestion, monitoring

# A battery of shapes a backend could plausibly hand over, including the null-present keys
# that have caused real bugs in this repo.
HOSTILE = [
    None,
    [],
    [None],
    [{}],
    [None, {}, "x", 42],
    [{"id": None, "status": None}],
    [{"id": "a", "status": "applied", "applied_at": None, "oa_at": "garbage"}],
    [{"id": "a", "status": "offer", "cost_usd": "nope", "latency_ms": "x",
      "input_tokens": None, "output_tokens": "y", "applied_at": ""}],
]


# ---------------- engines degrade, never raise ----------------


@pytest.mark.parametrize("apps", HOSTILE)
def test_analytics_never_raise(apps):
    assert isinstance(analytics.pipeline_funnel(apps), dict)
    assert isinstance(analytics.response_rate(apps), dict)
    assert isinstance(analytics.insight_digest(apps), dict)


@pytest.mark.parametrize("rows", HOSTILE)
def test_ingestion_never_raise(rows):
    assert isinstance(ingestion.dedupe_postings(rows), dict)
    assert isinstance(ingestion.freshness_sweep(rows), dict)
    assert isinstance(ingestion.plan_ingest(rows), dict)


@pytest.mark.parametrize("runs", HOSTILE)
def test_monitoring_never_raise(runs):
    assert isinstance(monitoring.summarize_runs(runs), dict)
    assert isinstance(monitoring.cost_by(runs, "agent"), dict)
    assert isinstance(monitoring.health_report(runs), dict)


def test_detect_regressions_never_raise():
    assert monitoring.detect_regressions({}, {}) == []
    assert monitoring.detect_regressions({"a": None}, {"a": "x"}) == []


# ---------------- normalize tolerates non-dicts ----------------


@pytest.mark.parametrize("bad", [None, "x", 42, [], ("t",), {"title": None}])
def test_normalize_posting_tolerates_non_dict(bad):
    out = ingestion.normalize_posting(bad)
    assert isinstance(out, dict) and out["title"] == ""


# ---------------- parsers fail cleanly ----------------


@pytest.mark.parametrize("bad", [None, 123, "", "   ", "<rss><channel></rss>", "{not json"])
def test_parsers_raise_value_error_not_a_type_error(bad):
    with pytest.raises(ValueError):
        ingestion.parse_feed(bad)
    with pytest.raises(ValueError):
        ingestion.parse_json_board(bad)


def test_plan_ingest_rejects_a_dict_feed():
    # a dict is neither XML text nor a posting list -- say so, do not iterate its keys
    with pytest.raises(ValueError):
        ingestion.plan_ingest({"jobs": []})


def test_plan_ingest_none_is_an_empty_plan():
    plan = ingestion.plan_ingest(None)
    assert plan["counts"] == {"incoming": 0, "create": 0, "update": 0,
                              "close": 0, "duplicates": 0}


def test_plan_ingest_ignores_non_dict_rows_in_a_list():
    plan = ingestion.plan_ingest([None, "x", {"title": "T", "company": "C"}])
    assert plan["counts"]["create"] == 1
