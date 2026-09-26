"""The interview report's contract, as data -- and the guard that keeps the data and the prompt
pointing at the same list.

`app/features/interview.py::FINALIZE_FIELDS` names what a finalize answer carries, because
`EvaluationItem.summary` is a free `Map<String, Object>` and nothing else in the repo states those
keys. They are the source the browser's report reader will be checked against, which only means
anything while the prompt still asks for them: an LLM answers what it was asked, so the prompt is
the producer and a field that leaves the prompt has to leave the tuple in the same change.
"""

from app.features.interview import FINALIZE_FIELDS, STUDY_ITEM_FIELDS


def test_the_finalize_prompt_asks_for_every_declared_field():
    from app.features.interview import FINALIZE_SYSTEM

    missing = [name for name in FINALIZE_FIELDS if f'"{name}"' not in FINALIZE_SYSTEM]
    assert missing == [], f"the report contract names {missing}, which the prompt no longer asks"


def test_the_study_item_fields_are_the_prompt_sownested_shape():
    from app.features.interview import FINALIZE_SYSTEM

    # `recommended_study` is the one list of objects in the report, and the panel renders a card per
    # item, so its three names are contract too -- inside the same prompt string.
    assert [name for name in STUDY_ITEM_FIELDS if f'"{name}"' not in FINALIZE_SYSTEM] == []


def test_no_name_is_declared_twice_or_in_both_contracts():
    # Uniqueness, without pinning a count: asserting `len == 9` made this test a second copy of the
    # tuple's own contents, so a mutant that added an unasked field went red here as well as in the
    # prompt guard -- two assertions covering one fact, and the magic number is the weaker one.
    assert len(set(FINALIZE_FIELDS)) == len(FINALIZE_FIELDS)
    assert len(set(STUDY_ITEM_FIELDS)) == len(STUDY_ITEM_FIELDS)
    # The report's own fields and the study card's are different levels of one answer; a name in both
    # would let a reader satisfy the card-level read from the report-level map by accident.
    assert not set(FINALIZE_FIELDS) & set(STUDY_ITEM_FIELDS)
