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


def test_both_contracts_are_declared_once():
    assert len(set(FINALIZE_FIELDS)) == len(FINALIZE_FIELDS) == 9
    assert len(set(STUDY_ITEM_FIELDS)) == len(STUDY_ITEM_FIELDS) == 3
    # The panel's own header line asks for these three; a rename here and not there is a blank card.
    assert "recommended_study" in FINALIZE_FIELDS
