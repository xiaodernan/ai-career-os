"""Tests for the Epic 15 analytics engines (offline, deterministic)."""

from datetime import datetime, timedelta, timezone

from app.features import analytics as A

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)


def _app(i, status, **ts):
    d = {"id": f"a{i}", "status": status}
    d.update(ts)
    return d


# ---------------- 15.1 funnel ----------------


def test_empty_funnel():
    f = A.pipeline_funnel([])
    assert f["totalApplications"] == 0
    assert f["appliedCount"] == 0
    assert all(s["count"] == 0 for s in f["pipeline"])
    assert f["savedCount"] == 0 and f["rejectedCount"] == 0


def test_funnel_reached_semantics():
    apps = [
        _app(1, "applied"),
        _app(2, "oa"),
        _app(3, "interview"),
        _app(4, "final_round"),
        _app(5, "offer"),
        _app(6, "rejected"),
        _app(7, "saved"),
    ]
    f = A.pipeline_funnel(apps)
    # reached counts are cumulative across the pipeline
    assert f["appliedCount"] == 6  # everything except the saved one
    by_stage = {s["stage"]: s["count"] for s in f["pipeline"]}
    # reached = applications at that stage or any later one (offer app also reached oa/interview/final)
    assert by_stage == {"applied": 6, "oa": 4, "interview": 3,
                        "final_round": 2, "offer": 1}
    assert f["savedCount"] == 1
    assert f["rejectedCount"] == 1


def test_funnel_conversion_rates():
    apps = [_app(i, "applied") for i in range(10)]
    for a in apps[:3]:
        a["status"] = "offer"
    f = A.pipeline_funnel(apps)
    by_stage = {s["stage"]: s for s in f["pipeline"]}
    assert by_stage["offer"]["conversionFromApplied"] == 0.3
    # step conversion offer <- final_round (3 offers, 3 final_round) == 1.0
    assert by_stage["offer"]["stepConversion"] == 1.0


def test_funnel_ignores_unknown_status():
    apps = [_app(1, "applied"), _app(2, "withdrawn"), _app(3, "bogus")]
    f = A.pipeline_funnel(apps)
    assert f["totalApplications"] == 3
    assert f["appliedCount"] == 1


# ---------------- 15.2 response rate ----------------


def test_response_rate_empty():
    r = A.response_rate([])
    assert r["appliedCount"] == 0
    assert r["responseRate"] == 0.0
    assert r["timeInStage"] == {}


def test_response_rate_basic():
    apps = [
        _app(1, "applied"),
        _app(2, "oa"),
        _app(3, "interview"),
        _app(4, "offer"),
        _app(5, "rejected"),
    ]
    r = A.response_rate(apps, now=NOW)
    assert r["appliedCount"] == 5
    # responded = oa(2,3,4=3) + rejected(1) = 4 of 5
    assert r["respondedCount"] == 4
    assert r["responseRate"] == 0.8
    assert r["offerCount"] == 1 and r["offerRate"] == 0.2
    assert r["interviewCount"] == 2 and r["interviewRate"] == 0.4


def test_time_in_stage_durations():
    apps = [
        _app(1, "oa", applied_at="2026-10-01", oa_at="2026-10-04"),       # 3 days
        _app(2, "offer", applied_at="2026-10-01", oa_at="2026-10-05",
             interview_at="2026-10-09", final_round_at="2026-10-12",
             offer_at="2026-10-14"),                                     # 4,8,11,13
        _app(3, "applied"),  # no timestamps -> omitted from durations
    ]
    r = A.response_rate(apps, now=NOW)
    tis = r["timeInStage"]
    assert tis["oa"]["n"] == 2 and tis["oa"]["medianDays"] == 3.5
    assert tis["offer"]["n"] == 1 and tis["offer"]["avgDays"] == 13.0
    # missing timestamps are not fabricated
    assert all(v["n"] >= 1 for v in tis.values())


def test_time_in_stage_handles_unparseable():
    apps = [_app(1, "oa", applied_at="not-a-date", oa_at="2026-10-05")]
    r = A.response_rate(apps, now=NOW)
    # unparseable applied_at -> no duration, but the app still counts toward rates
    assert r["timeInStage"]["oa"]["n"] == 0
    assert r["appliedCount"] == 1 and r["responseRate"] == 1.0


# ---------------- 15.3 insight digest ----------------


def test_insight_digest_flags_stalled():
    apps = [
        _app(1, "applied", applied_at=(NOW - timedelta(days=30)).isoformat()),
        _app(2, "applied", applied_at=(NOW - timedelta(days=3)).isoformat()),
        _app(3, "saved", created_at=(NOW - timedelta(days=40)).isoformat()),
        _app(4, "offer", applied_at=(NOW - timedelta(days=20)).isoformat(),
             offer_at=(NOW - timedelta(days=10)).isoformat()),
    ]
    d = A.insight_digest(apps, now=NOW, stale_days=14)
    stalled_ids = {s["id"] for s in d["stalled"]}
    assert stalled_ids == {"a1", "a3"}  # a2 recent, a4 already moved
    assert d["stalledCount"] == 2
    assert d["activePipeline"] == 3  # applied, offer (saved excluded)
    # submitted = a1(aplied), a2(applied), a4(offer) = 3; a3(saved) excluded
    # reached past OA = a4 only (1 of 3); no rejections -> responded = 1
    assert d["responseRate"] == round(1 / 3, 4)


def test_insight_digest_no_activity_timestamp_excluded_from_stalled():
    apps = [_app(1, "applied")]  # no applied_at/created_at
    d = A.insight_digest(apps, now=NOW, stale_days=14)
    assert d["stalled"] == []  # cannot claim staleness without a date


def test_insight_digest_echoes_optional_composition():
    apps = [_app(1, "offer")]
    d = A.insight_digest(apps, now=NOW, growth_deltas=[{"closed": ["k8s"]}],
                         top_matches=[{"title": "Backend", "score": 0.9}])
    assert d["growthDeltas"] == [{"closed": ["k8s"]}]
    assert d["topMatches"][0]["title"] == "Backend"


def test_insight_digest_empty_signals():
    d = A.insight_digest([], now=NOW)
    assert d["totalApplications"] == 0
    assert any("empty" in s.lower() for s in d["signals"])
