"""Unit tests for Outreach message drafting (forward Epic 11.2).

The message is phrased by the model, but what it may cite is chosen
deterministically and validated -- the same no-fabrication rule tailoring and cover
letters enforce. These tests pin the evidence selection and the validator that
strips any skill the profile does not support.
"""

from app.features import outreach as outreach_mod
from app.features.outreach import (allowed_evidence, compose, draft_message,
                                   pick_evidence)

RESUME = {"skills": [{"name": "Java"}, {"name": "k8s"}],
          "projects": [{"name": "Payments Rewrite"}],
          "experience": [{"title": "Backend Engineer"}]}


# ---------------- pick_evidence ----------------


def test_pick_evidence_normalizes_skills_and_takes_project_highlight():
    ev = pick_evidence(RESUME)
    assert ev["skills"] == ["Java", "Kubernetes"]
    assert ev["highlight"] == "Payments Rewrite"


def test_pick_evidence_falls_back_to_experience_title():
    ev = pick_evidence({"skills": [], "projects": [], "experience": [{"title": "SRE"}]})
    assert ev["highlight"] == "SRE"


def test_pick_evidence_empty_resume():
    assert pick_evidence({}) == {"skills": [], "highlight": ""}
    assert pick_evidence(None) == {"skills": [], "highlight": ""}


# ---------------- allowed_evidence ----------------


def test_allowed_evidence_includes_skills_and_highlight():
    allowed = allowed_evidence(pick_evidence(RESUME))
    assert allowed == {"Java", "Kubernetes", "Payments Rewrite"}


# ---------------- compose: the no-fabrication validator ----------------


def test_compose_strips_evidence_the_profile_does_not_support():
    out = {"subject": "Hello", "body": "body text",
           "evidenceUsed": ["Java", "Fabricated Skill", "kubernetes"]}
    res = compose({"name": "Ada"}, "referral", out, pick_evidence(RESUME))
    assert res["evidenceUsed"] == ["Java", "Kubernetes"]     # fabricated one dropped
    assert res["subject"] == "Hello" and res["body"] == "body text"
    assert res["contactName"] == "Ada" and res["purpose"] == "referral"


def test_compose_with_no_resume_cites_nothing():
    out = {"subject": "Hi", "body": "b", "evidenceUsed": ["Java"]}
    res = compose({"name": "Ada"}, "intro", out, pick_evidence({}))
    assert res["evidenceUsed"] == []
    assert res["allowedEvidence"] == []


def test_compose_truncates_a_long_subject_and_strips_whitespace():
    out = {"subject": "  " + "x" * 300 + "  ", "body": "  body  ", "evidenceUsed": []}
    res = compose({"name": "Ada"}, "referral", out, pick_evidence(RESUME))
    assert len(res["subject"]) == 200 and res["body"] == "body"


# ---------------- draft_message wiring (LLM stubbed) ----------------


async def test_draft_message_composes_and_validates(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"subject": "Referral?", "body": "Hi Ada, ...",
                "evidenceUsed": ["Java", "Ghost Skill"]}

    monkeypatch.setattr(outreach_mod, "ask_json", fake_ask_json)
    res = await draft_message({"name": "Ada", "role": "EM", "company": "Acme"},
                              "referral", RESUME, user_id="u-1")
    assert res["subject"] == "Referral?"
    assert res["evidenceUsed"] == ["Java"]          # "Ghost Skill" stripped
    assert res["contactName"] == "Ada"
    assert "Kubernetes" in res["allowedEvidence"]
