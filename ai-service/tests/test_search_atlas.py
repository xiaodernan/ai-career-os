"""Epic 438 — the atlas is a map of the reader's OWN rows, not a painted backdrop.

It must always show the whole world (so an empty territory is visible rather than
silently dropped), count only real rows, and never let one language leak into the
other. It is pure: no database, no model, no network — the whole test file runs
offline in milliseconds.
"""

from __future__ import annotations

from app.features.search_atlas import REGIONS, search_atlas

IDS = [region[0] for region in REGIONS]


def test_every_region_is_drawn_even_when_the_world_is_empty() -> None:
    for locale in ("en", "zh"):
        atlas = search_atlas({}, locale=locale)
        assert [r["id"] for r in atlas["regions"]] == IDS
        assert atlas["total_evidence"] == 0
        assert atlas["locale"] == locale
        assert all(r["count"] == 0 for r in atlas["regions"])
        assert all(r["explored"] is False for r in atlas["regions"])
        assert all("{" not in r["note"] for r in atlas["regions"]), "an unfilled placeholder leaked"


def test_counts_come_from_the_rows_and_nowhere_else() -> None:
    payload = {
        "applications": [{"id": "1"}, {"id": "2"}],
        "jobs": [{"id": "j"}],
        "interviews": [{"id": "i"}],
        "letters": [],
        "notes": [{"id": "n"}] * 4,
        "contacts": [{"id": "c"}],
        "offers": [],
    }
    atlas = search_atlas(payload)
    assert [r["count"] for r in atlas["regions"]] == [2, 1, 1, 0, 4, 1, 0]
    assert atlas["total_evidence"] == 9
    assert [r["explored"] for r in atlas["regions"]] == [
        True, True, True, False, True, True, False
    ]
    assert "2 applications" in atlas["regions"][0]["note"]
    assert "4 notes" in atlas["regions"][4]["note"]


def test_a_paged_envelope_counts_its_items_not_its_metadata() -> None:
    payload = {"applications": {"items": [1, 2, 3], "total": 300, "page": 0}}
    atlas = search_atlas(payload)
    assert atlas["regions"][0]["count"] == 3
    assert atlas["total_evidence"] == 3


def test_malformed_fields_are_silence_not_a_crash() -> None:
    atlas = search_atlas({
        "applications": None,
        "jobs": "not a list",
        "interviews": 42,
        "notes": {"items": "wrong type"},
        "offers": {"total": 7},
    })
    assert atlas["total_evidence"] == 0
    assert all(r["explored"] is False for r in atlas["regions"])
    assert search_atlas(None)["total_evidence"] == 0
    assert search_atlas("not a mapping")["locale"] == "en"


def test_the_two_languages_are_pure() -> None:
    payload = {"applications": [1], "notes": [2]}
    en = search_atlas(payload, locale="en")
    zh = search_atlas(payload, locale="zh")
    assert all(not any("\u4e00" <= ch <= "\u9fff" for ch in r["title"] + r["note"])
               for r in en["regions"]), "English carried a Han character"
    assert all(not any(word in r["note"].lower() for word in ("the ", "are ", "no "))
               for r in zh["regions"]), "Chinese carried an English sentence"
    assert all(any("\u4e00" <= ch <= "\u9fff" for ch in r["title"] + r["note"])
               for r in zh["regions"]), "Chinese region lost its own words"


def test_the_map_is_deterministic_and_locales_do_not_move_counts() -> None:
    payload = {"applications": [1, 2], "letters": [1]}
    a = search_atlas(payload, locale="en")
    b = search_atlas(payload, locale="en")
    c = search_atlas(payload, locale="zh")
    assert a == b
    assert [r["count"] for r in a["regions"]] == [r["count"] for r in c["regions"]]
    assert a["total_evidence"] == c["total_evidence"] == 3
