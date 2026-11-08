"""The career-timeline engine is one ordered, deterministic read (Epic 81).

Merging the product's timestamps into one timeline is a pure partition: the same
events in any order answer the same list, sorted by `(at, kind, refId)` -- the
argument that decides which screen was doing what, without any model call.
"""

from __future__ import annotations

import pytest

from app.features.career_timeline import build_timeline


def test_empty_account_gets_an_honest_empty_timeline():
    assert build_timeline([]) == {"timeline": []}
    assert build_timeline(None) == {"timeline": []}


def test_events_are_sorted_by_time():
    out = build_timeline([
        {"at": "2026-10-03T00:00:00Z", "kind": "note"},
        {"at": "2026-10-01T00:00:00Z", "kind": "match"},
        {"at": "2026-10-02T00:00:00Z", "kind": "application"},
    ])
    assert [e["kind"] for e in out["timeline"]] == ["match", "application", "note"]


def test_ties_break_on_kind_then_ref_id():
    out = build_timeline([
        {"at": "2026-10-01T00:00:00Z", "kind": "note", "refId": "b"},
        {"at": "2026-10-01T00:00:00Z", "kind": "note", "refId": "a"},
        {"at": "2026-10-01T00:00:00Z", "kind": "match", "refId": "z"},
    ])
    assert [e["kind"] for e in out["timeline"]] == ["match", "note", "note"]
    assert [e["refId"] for e in out["timeline"]] == ["z", "a", "b"]


def test_unparseable_at_sorts_first_not_crash():
    out = build_timeline([
        {"at": "someday", "kind": "weird"},
        {"at": "2026-10-02T00:00:00Z", "kind": "match"},
    ])
    assert out["timeline"][0]["kind"] == "weird"
    assert out["timeline"][1]["kind"] == "match"


def test_missing_fields_are_invented_not_crashed():
    out = build_timeline([{"at": "2026-10-01T00:00:00Z"}])
    assert out["timeline"][0]["kind"] == "unknown"
    assert out["timeline"][0]["title"] == ""
    assert out["timeline"][0]["refId"] == ""
    assert out["timeline"][0]["summary"] == ""


def test_input_order_does_not_change_the_answer():
    events = [
        {"at": "2026-10-02T00:00:00Z", "kind": "match", "refId": "m1"},
        {"at": "2026-10-01T00:00:00Z", "kind": "interview", "refId": "i1"},
        {"at": "2026-10-02T00:00:00Z", "kind": "match", "refId": "m0"},
    ]
    assert build_timeline(events)["timeline"] == build_timeline(list(reversed(events)))["timeline"]
