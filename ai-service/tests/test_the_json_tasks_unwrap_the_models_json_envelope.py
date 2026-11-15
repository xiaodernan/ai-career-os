"""The structured twin of the interview-opening fix: every JSON task unwraps the envelope.

The golden journey (scripts/journey_api.py) showed the relay answering the tailor
endpoint with a one-key envelope — `{"message": "<the real JSON>"}`. The outer
reply is valid JSON, `_coerce_json` parsed it faithfully, and every caller read
an empty shape. This test holds the seam every structured task reads: `_coerce_json`
returns the *inner* object when — and only when — the envelope is unambiguous.
"""

import json

import pytest

from app.core.ai import _coerce_json


def test_the_envelope_the_journey_measured_is_unwrapped():
    inner = {"changes": [{"section": "experience", "before": "a", "after": "b"}],
             "summary": "Composed.", "skillOrder": ["java"], "notes": []}
    reply = json.dumps({"message": json.dumps(inner)})
    assert _coerce_json(reply) == inner


def test_the_envelope_unwinds_even_when_an_outer_fence_was_used():
    reply = "```json\n" + json.dumps({"answer": "{\"tailor\": {\"accepted\": 3}}"}) + "\n```"
    assert _coerce_json(reply) == {"tailor": {"accepted": 3}}


def test_the_envelope_unwinds_when_the_answer_field_is_fenced():
    reply = json.dumps({"message": "```json\n{\"profile\": {\"headline\": \"engineer\"}}\n```"})
    assert _coerce_json(reply) == {"profile": {"headline": "engineer"}}


def test_a_plain_reply_is_returned_identically():
    reply = {"changes": [], "summary": "clean"}
    assert _coerce_json(json.dumps(reply)) == reply


def test_two_keys_is_not_an_envelope_even_when_one_is_message():
    reply = {"message": "hello", "other": "world"}
    assert _coerce_json(json.dumps(reply)) == reply


def test_an_envelope_key_carries_free_text_it_is_preserved():
    reply = {"message": "Here is the summary you asked for, no JSON in it at all."}
    assert _coerce_json(json.dumps(reply)) == reply


def test_an_envelope_key_carrying_an_array_is_preserved():
    reply = {"content": "[1, 2, 3]"}
    assert _coerce_json(json.dumps(reply)) == reply


def test_an_unknown_answer_field_is_not_an_envelope_even_if_it_carries_json():
    reply = {"hint": "{\"changes\": []}"}
    assert _coerce_json(json.dumps(reply)) == reply


def test_the_envelope_with_a_nested_object_inside_survives():
    inner = {"match": {"score": 88, "gaps": [{"name": "kubernetes", "importance": "must"}]}}
    reply = json.dumps({"response": json.dumps(inner)})
    assert _coerce_json(reply) == inner


def test_the_repair_retry_sees_the_same_unwrap_because_it_uses_the_same_seam():
    # The self-repair retry calls _coerce_json too — the fix belongs to both paths.
    reply = "some prose around the answer\n" + json.dumps({"reply": "{\"verdict\": \"ready\"}"})
    assert _coerce_json(reply) == {"verdict": "ready"}


def test_a_non_dict_reply_still_raises_for_the_repair_retry():
    with pytest.raises(json.JSONDecodeError):
        _coerce_json("[1, 2, 3]")
