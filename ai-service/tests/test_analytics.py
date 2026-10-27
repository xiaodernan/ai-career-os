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


def test_digest_reads_last_seen_as_the_rows_last_activity():
    """The bridge sends `last_seen` (the row's own update stamp) and the digest must use it.

    The number is called `daysSinceLastActivity`, so an application that was submitted in
    April and annotated yesterday has had activity -- reporting it as stalled for forty days
    is the digest contradicting its own field name while the row that says otherwise sits in
    the very request.
    """
    old = {"applied_at": (NOW - timedelta(days=40)).isoformat(),
           "created_at": (NOW - timedelta(days=45)).isoformat()}
    fresh = dict(old, last_seen=(NOW - timedelta(days=2)).isoformat())

    stalled = [s["id"] for s in A.insight_digest([_app(1, "applied", **old)], now=NOW,
                                                 stale_days=14)["stalled"]]
    touched = A.insight_digest([_app(2, "applied", **fresh)], now=NOW, stale_days=14)

    assert stalled == ["a1"]  # no last_seen: the April date is all the row has
    assert touched["stalled"] == []  # activity two days ago is not a stall
    assert touched["stalledCount"] == 0


def test_digest_ignores_an_unparseable_last_seen():
    """A bad timestamp must not make the row look freshly touched -- or crash the digest."""
    apps = [_app(1, "applied", applied_at=(NOW - timedelta(days=40)).isoformat(),
                 last_seen="yesterday-ish")]
    d = A.insight_digest(apps, now=NOW, stale_days=14)
    assert [s["daysSinceLastActivity"] for s in d["stalled"]] == [40]


# ---------------- 15.3 the stage mix is a distribution ----------------


def _mix_rows():
    """Five applications, one sitting at each of five positions -- including the two the
    funnel reports separately (``saved``, ``rejected``) and one that passed four stages."""
    return [
        _app(1, "applied", applied_at=(NOW - timedelta(days=30)).isoformat()),
        _app(2, "saved", created_at=(NOW - timedelta(days=40)).isoformat()),
        _app(3, "rejected", applied_at=(NOW - timedelta(days=20)).isoformat()),
        _app(4, "offer", applied_at=(NOW - timedelta(days=20)).isoformat(),
             offer_at=(NOW - timedelta(days=10)).isoformat()),
        _app(5, "interview", applied_at=(NOW - timedelta(days=12)).isoformat(),
             interview_at=(NOW - timedelta(days=5)).isoformat()),
    ]


def test_the_digest_stage_mix_counts_every_row_exactly_once():
    """#250: the mix answered "where is each application", and must add up to the rows.

    The analysis card feeds these numbers to ``ShareChart``, which divides each value by the
    sum of the values. Hand it the funnel's reached-counts and five applications produce seven,
    so every bar is drawn as a fraction of a total that no account has -- "applied" reads 20%
    when three quarters of the pipeline is sitting there.
    """
    d = A.insight_digest(_mix_rows(), now=NOW, stale_days=14)
    mix = d["stageCounts"]

    assert mix == {"saved": 1, "applied": 1, "interview": 1, "offer": 1, "rejected": 1}
    assert sum(mix.values()) == len(_mix_rows()) == d["totalApplications"]


def test_the_stage_mix_is_not_the_funnels_reached_count():
    """The two numbers answer different questions, and the digest may not borrow the funnel's.

    The row at ``offer`` also passed applied, OA, interview and final round, so the funnel
    credits it five times and deliberately does not add up. The mix counts it once, at the
    position it holds now. Pinning both directions is what keeps the fix from being made the
    wrong way round: converting the funnel into a partition would silently rewrite 15.1.
    """
    rows = _mix_rows()
    mix = A.insight_digest(rows, now=NOW)["stageCounts"]
    reached = {s["stage"]: s["count"] for s in A.pipeline_funnel(rows)["pipeline"]}

    assert mix["applied"] == 1  # only the application that never got past it
    assert reached["applied"] == 4  # + rejected, offer and interview, which all passed through
    assert sum(mix.values()) == 5
    assert sum(reached.values()) == 10  # cumulative on purpose
    assert set(reached) == {"applied", "oa", "interview", "final_round", "offer"}
    assert {"saved", "rejected"} <= set(mix)  # positions the funnel has no row for


def test_a_status_outside_the_pipeline_vocabulary_is_counted_under_its_own_name():
    """A row missing from a distribution is the same lie as a row counted twice.

    ``withdrawn`` is what a candidate who withdrew has in the status column, and a row whose
    status was never written is a row the reader still has. Neither may vanish from the chart:
    the first is reported under its own spelling, the second under ``unset``, and the two land
    after the known positions so the pipeline order survives.
    """
    rows = [*_mix_rows()[:2], _app(6, "withdrawn"), _app(7, "")]
    d = A.insight_digest(rows, now=NOW)

    assert d["stageCounts"]["withdrawn"] == 1
    assert d["stageCounts"]["unset"] == 1
    assert sum(d["stageCounts"].values()) == len(rows) == d["totalApplications"]
    assert list(d["stageCounts"]) == ["saved", "applied", "unset", "withdrawn"]


def test_the_mix_is_ordered_by_the_position_order_the_product_teaches():
    """The chart draws rows in the order the dict gives them, so the order is a claim.

    Alphabetical would put ``offer`` under ``final_round``'s neighbour and ``rejected`` between
    ``oa`` and ``saved``; the board's own stage order is the one a reader follows.
    """
    rows = [_app(i, s) for i, s in enumerate(["offer", "rejected", "saved", "applied",
                                              "final_round", "oa", "interview"], start=1)]
    mix = A.insight_digest(rows, now=NOW)["stageCounts"]

    assert list(mix) == A.STAGES
    assert list(mix) != sorted(mix)


def test_a_rejected_application_is_not_missing_from_the_mix():
    """The count the rejection rate is made of used to be absent from the stage card.

    ``rejectedCount`` exists on the funnel and ``responseRate`` counts a no as a reply, so a
    digest that showed every stage except the one most applications end at contradicted its own
    headline numbers -- and left the page's ``rejected`` colour branch with nothing to colour.
    """
    rows = [_app(1, "rejected"), _app(2, "rejected"), _app(3, "offer")]
    mix = A.insight_digest(rows, now=NOW)["stageCounts"]

    assert mix == {"offer": 1, "rejected": 2}
    assert sum(mix.values()) == 3


def test_durations_time_a_stage_a_rejected_application_reached():
    """The funnel and the durations answer different questions, on purpose.

    A rejection credits `applied` only -- the row's current status is all the funnel can
    vouch for. But the transition log says this candidate did reach an interview, and how
    long that took is a fact about their pipeline whether or not it ended in a no.
    """
    apps = [_app(1, "rejected", applied_at="2026-10-01",
                 interview_at="2026-10-08")]
    rates = A.response_rate(apps, now=NOW)
    funnel = A.pipeline_funnel(apps)

    assert funnel["appliedCount"] == 1  # reached applied
    assert {s["stage"]: s["count"] for s in funnel["pipeline"]}["interview"] == 0
    assert rates["timeInStage"]["interview"]["n"] == 1
    assert rates["timeInStage"]["interview"]["avgDays"] == 7.0


def test_insight_digest_echoes_optional_composition():
    apps = [_app(1, "offer")]
    d = A.insight_digest(apps, now=NOW, growth_deltas=[{"closed": ["k8s"]}],
                         top_matches=[{"title": "Backend", "score": 0.9}])
    assert d["growthDeltas"] == [{"closed": ["k8s"]}]
    assert d["topMatches"][0]["title"] == "Backend"


def test_insight_digest_empty_signals():
    d = A.insight_digest([], now=NOW)
    assert d["totalApplications"] == 0
    assert any("漏斗是空的" in s for s in d["signals"])


# ---------------- 15.3 the stall clock only counts time that has passed ----------------


def test_a_row_stamped_only_in_the_future_is_not_aged_as_silence():
    """#251: ``sorted([start, end])`` read a submission dated next month as forty days quiet.

    ``applied_at`` is the one timestamp the engine gets from the caller's own import bundle,
    and ``ImportService.time`` parses whatever ISO string is there. Sorting the pair made the
    sign disappear, so the analysis page printed "40d" under "Stalled applications" and the
    digest asserted an application had gone quiet that has not been applied to yet.
    """
    future = (NOW + timedelta(days=40)).isoformat()
    d = A.insight_digest([_app(1, "applied", applied_at=future)], now=NOW, stale_days=14)

    assert d["stalled"] == []
    assert d["stalledCount"] == 0
    assert not any("没有动静" in s for s in d["signals"])


def test_a_future_stamp_does_not_hide_a_row_that_really_did_go_quiet():
    """Dropping the impossible moment must not drop the row: the honest date still ages it.

    The same row carries a ``created_at`` from 45 days ago. Letting a future ``applied_at``
    win the max and then refusing to age it would remove a genuinely stalled application from
    the card -- the defect fixed one way and re-imported as its opposite.
    """
    row = _app(1, "applied", applied_at=(NOW + timedelta(days=40)).isoformat(),
               created_at=(NOW - timedelta(days=45)).isoformat())
    d = A.insight_digest([row], now=NOW, stale_days=14)

    assert [s["daysSinceLastActivity"] for s in d["stalled"]] == [45]
    assert d["stalledCount"] == 1


def test_the_stall_clock_still_ages_a_row_that_went_quiet_for_real():
    """Counterweight: the future is excluded, the past is not.

    An exclusion written as ``d >= ref`` or as a blanket guard clause passes the two cases
    above by emptying the list for everybody. This row is forty days old and stays listed.
    """
    d = A.insight_digest([_app(1, "applied", applied_at=(NOW - timedelta(days=40)).isoformat())],
                         now=NOW, stale_days=14)

    assert [s["daysSinceLastActivity"] for s in d["stalled"]] == [40]


def test_a_stage_entered_before_the_application_is_not_timed_as_a_reply():
    """An impossible transition is two clocks disagreeing, not a fast response.

    The bridge reads the stage moment out of the status-transition log and the submission
    moment out of the row, and the import path rewrites only the row -- so an application can
    genuinely carry an interview that predates its own ``applied_at``. Sorting timed it as a
    seven-day reply and put it in the average.
    """
    apps = [_app(1, "interview", applied_at="2026-10-08T00:00:00+00:00",
                 interview_at="2026-10-01T00:00:00+00:00")]
    r = A.response_rate(apps, now=NOW)

    assert r["timeInStage"]["interview"]["n"] == 0
    assert r["timeInStage"]["interview"]["avgDays"] is None
    # the row is still an application that got a reply: only the duration is refused
    assert r["appliedCount"] == 1 and r["interviewCount"] == 1


def test_a_stage_stamp_past_the_clock_is_not_an_elapsed_duration():
    """``now`` is read, not decorative: it bounds the end of the pair.

    With a clock at the stamp date the same row times fifty days and reports n 1, so the
    second leg is the witness that the bound is what refuses it. A caller posting rows to
    ``/analysis/response-rate`` owns no clock this engine may trust.
    """
    stage_future = (NOW + timedelta(days=10)).isoformat()
    applied = (NOW - timedelta(days=40)).isoformat()
    apps = [_app(1, "offer", applied_at=applied, offer_at=stage_future)]

    bounded = A.response_rate(apps, now=NOW)
    later = A.response_rate(apps, now=NOW + timedelta(days=30))

    assert bounded["timeInStage"]["offer"]["n"] == 0
    assert later["timeInStage"]["offer"]["n"] == 1
    assert later["timeInStage"]["offer"]["avgDays"] == 50.0


def test_days_between_refuses_the_impossible_pair_and_measures_the_elapsed_one():
    """The helper's own truth table, so a revert to ``sorted`` is a red test not a review.

    Direction is what the function is for: elapsed days from start to end, never the distance
    between two moments whoever arrives first.
    """
    past = NOW - timedelta(days=40)

    assert A._days_between(past, NOW, NOW) == 40.0
    assert A._days_between(NOW, NOW, NOW) == 0.0
    assert A._days_between(NOW, past, NOW) is None           # start after end
    assert A._days_between(past, NOW + timedelta(days=5), NOW) is None  # end past the clock
    assert A._days_between(None, NOW, NOW) is None
    assert A._days_between(past, None, NOW) is None
