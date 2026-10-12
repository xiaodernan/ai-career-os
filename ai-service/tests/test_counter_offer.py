"""Unit tests for counter-offer drafting (forward Epic 12.4).

The anchor and the reasons are deterministic; the model only phrases them. These
tests pin the anchor rule (upper quartile, else median, never below the offer) and
the composition, and drive the drafting coroutine with the LLM stubbed.
"""

from app.features import counter_offer as co
from app.features.counter_offer import compose, draft_counter_offer, target_ask

REPORT = {"sampleSize": 4, "currency": "CNY",
          "percentiles": {"min": 100, "p25": 175, "p50": 250, "p75": 325, "max": 400}}


# ---------------- target_ask ----------------


def test_target_ask_anchors_at_upper_quartile():
    assert target_ask(200, REPORT) == 325
    assert target_ask(300, REPORT) == 325


def test_target_ask_never_below_the_offer():
    assert target_ask(350, REPORT) == 350          # p75 < offer -> ask the offer itself
    assert target_ask(400, REPORT) == 400


def test_target_ask_falls_back_to_median_without_p75():
    report = {"sampleSize": 1, "percentiles": {"p50": 300, "max": 300}}
    assert target_ask(250, report) == 300


def test_target_ask_without_data_is_the_offer():
    assert target_ask(250, {"sampleSize": 0, "percentiles": {}}) == 250


# ---------------- compose ----------------


def test_compose_reports_ask_increase_and_rationale():
    out = compose(200, REPORT, {"subject": "Counter", "body": "Hi"})
    assert out["askAmount"] == 325
    assert out["increasePct"] == 62.5
    assert out["assessment"]["verdict"] == "within_market"
    assert out["rationale"]                    # deterministic talking points
    assert out["subject"] == "Counter" and out["body"] == "Hi"


def test_compose_without_data_is_honest():
    out = compose(200, {"sampleSize": 0, "percentiles": {}},
                  {"subject": "s", "body": "b"})
    assert out["askAmount"] == 200 and out["increasePct"] == 0.0
    assert out["assessment"]["verdict"] == "unknown"


# ---------------- draft_counter_offer wiring (LLM stubbed) ----------------


async def test_draft_counter_offer_composes(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"subject": "On the offer", "body": "Thank you for the offer..."}

    monkeypatch.setattr(co, "ask_json", fake_ask_json)
    res = await draft_counter_offer(200, REPORT, match_score=0.8, user_id="u-1")
    assert res["subject"] == "On the offer"
    assert res["askAmount"] == 325
    assert res["assessment"]["verdict"] == "within_market"
    assert res["rationale"]
