"""The reply reader (roadmap 37.2).

The tracker files a forwarded letter by what it says, so the reading has two
halves that fail differently: the deterministic cue passes must hold on their
own -- a clear rejection is read the same in every run, in either language --
and the model must never be able to overrule them. The outage rule is the third:
a letter whose words settled the intent survives a dead provider, and one whose
words did not raises rather than inventing a reading, because the bridge stores
"no intent" and keeps the letter.
"""

import pytest

from app.features import reply_classify as rc


@pytest.mark.parametrize("text", [
    "We regret to inform you that we will not be moving forward with your application.",
    "Unfortunately, we cannot offer you a position at this time.",
    "很遗憾 您未能进入下一轮面试",
    "经过评估 我们决定不予录用",
])
def test_a_no_is_a_rejection_even_when_it_says_offer_or_interview(text):
    assert rc.rule_intent(text) == "rejection"


@pytest.mark.parametrize("text", [
    "We would like to schedule a call to discuss your experience.",
    "Could you share your availability for a phone screen next week?",
    "您好 想和您约个时间进行视频面试",
])
def test_a_request_to_talk_is_an_interview(text):
    assert rc.rule_intent(text) == "interview"


def test_an_offer_outranks_the_interview_it_recounts():
    text = ("Following your interview, we are pleased to offer you the Backend "
            "Engineer position at Acme. The compensation package is attached.")
    assert rc.rule_intent(text) == "offer"

    assert rc.rule_intent("恭喜 我们决定录用您") == "offer"


@pytest.mark.parametrize("text", [
    "We have received your application and will be in touch soon.",
    "已收到您的申请 后续会另行通知",
])
def test_an_acknowledgement_is_info(text):
    assert rc.rule_intent(text) == "info"


def test_a_letter_with_no_cue_is_left_to_the_model():
    assert rc.rule_intent("Hello Ada, thanks for reaching out. Best, Sam") is None


def test_the_rules_reading_beats_the_models_when_they_disagree():
    out = rc.compose_reading(
        "rejection", {"intent": "interview", "company": " Acme ",
                      "role": "Backend Engineer"})
    assert out == {"intent": "rejection", "company": "Acme", "role": "Backend Engineer"}


def test_an_invented_intent_is_other_and_the_names_stay_strings():
    out = rc.compose_reading(None, {"intent": "spam", "company": None, "role": 7})
    assert out == {"intent": "other", "company": "", "role": ""}


def test_a_reading_with_no_model_answer_at_all_is_a_valid_answer():
    assert rc.compose_reading(None, None) == {"intent": "other", "company": "",
                                              "role": ""}


async def test_a_settled_reading_survives_a_dead_provider(monkeypatch):
    async def down(*args, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(rc, "ask_json", down)

    out = await rc.classify_reply("Unfortunately, we cannot offer you the role.")
    assert out == {"intent": "rejection", "company": "", "role": ""}


async def test_an_unsettled_reading_raises_when_the_provider_is_dead(monkeypatch):
    async def down(*args, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(rc, "ask_json", down)

    with pytest.raises(RuntimeError):
        await rc.classify_reply("Hello Ada, thanks for reaching out.")


async def test_the_model_fills_what_the_rules_left_open(monkeypatch):
    async def fake(req, **kwargs):
        assert "classify one recruiter reply" in req.messages[0].content.lower()
        return {"intent": "interview", "company": "Acme", "role": "Backend Engineer"}

    monkeypatch.setattr(rc, "ask_json", fake)

    out = await rc.classify_reply("Can we talk next week?")
    assert out == {"intent": "interview", "company": "Acme", "role": "Backend Engineer"}


async def test_the_model_does_not_overrule_the_words(monkeypatch):
    async def fake(req, **kwargs):
        return {"intent": "interview", "company": "Acme", "role": "Backend Engineer"}

    monkeypatch.setattr(rc, "ask_json", fake)

    out = await rc.classify_reply("Unfortunately, we cannot offer you the role.")
    assert out["intent"] == "rejection"
    assert out["company"] == "Acme"
