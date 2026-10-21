"""The anonymized export has to actually forget.

The reader has two ways to leave with their data: the **redaction** drops
whole sections, and the **anonymized export** keeps the shape and takes
the people out of it. The docs call the second one "the right-to-be-forgotten
surface", so it has to forget.

It used to forget nothing. It blanked four field names on the profile --
``email``, ``display_name``, ``phone``, ``address`` -- and the profile has
carried none of them for as long as the export has existed, so the button
called "Export anonymized" exported everything: the reader's own uuid, the
links to their profiles, their resume's plaintext, every answer they gave an
interviewer, and (since 1.2.0) the notes they typed and the people they
know, with their email.

This gate holds three things:

* the *profile entity* is checked against the old strip list, so the list
  that used to do nothing cannot quietly start doing something -- and so
  the reason it did nothing is written down rather than remembered;
* the anonymized bundle is checked against a **real-shaped** one, so a
  fixture shaped like the old profile cannot make the test pass again;
* what stays is stated: the shape of the bundle, and the substance of a job
  search, which an export that leaves nothing behind would not be.
"""

from pathlib import Path
import re

import pytest

from app.features import export as ex

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ENTITY = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "auth" / "entity" / "UserProfile.java"


def _entity_columns(path: Path) -> set[str]:
    """The column names an entity declares."""
    source = path.read_text(encoding="utf-8")
    named = set(re.findall(r'@Column\([^)]*name\s*=\s*"([a-z_]+)"', source))
    return named


def _realistic_bundle() -> dict:
    """A bundle shaped like the real one -- the columns the entities declare."""
    raw = {
        "profile": {
            "id": "p1",
            "user_id": "11111111-1111-1111-1111-111111111111",
            "headline": "Senior backend engineer",
            "summary": "I have led payments teams for eight years.",
            "location": "Hangzhou",
            "years_experience": 8,
            "target_roles": ["backend"],
            "target_locations": ["Hangzhou"],
            "links": {"github": "https://github.com/someone"},
            "work_authorization": "yes",
            "preferences": {},
        },
        "resumes": [
            {"id": "r1", "user_id": "11111111-1111-1111-1111-111111111111",
             "label": "Main", "resume_title": "Li Ming -- resume",
             "plaintext": "Li Ming, 13800000000, li.ming@example.com",
             "structured": {"name": "Li Ming"}},
        ],
        "notes": [
            {"id": "n1", "title": "My salary note",
             "content": "I make 50w a year."},
        ],
        "contacts": [
            {"id": "c1", "name": "Li Ming", "role": "Mentor", "company": "Acme",
             "relation": "Mentor", "email": "liming@example.com",
             "notes": "My mentor, from the conference."},
        ],
        "job_descriptions": [{"id": "j1", "title": "Backend", "raw_text": "the posting"}],
        "applications": [
            {"id": "a1", "title": "Backend engineer", "company_name": "Acme",
             "status": "applied", "notes": "I applied after the conference."},
        ],
        "knowledge": [
            {"id": "d1", "user_id": "11111111-1111-1111-1111-111111111111",
             "title": "My notes", "text_excerpt": "Acme pays 40-60w."},
        ],
        "interviews": [
            {"id": "s1", "turns": [
                {"seq": 1, "question": "Tell me about yourself",
                 "content": "I led a payments team."},
            ]},
        ],
        "memories": [{"id": "m1", "kind": "preference", "key": "salary",
                      "content": "I make 50w a year."}],
    }
    return ex.build_bundle("11111111-1111-1111-1111-111111111111", raw)


def test_the_old_strip_list_named_fields_the_profile_does_not_have() -> None:
    # The reason the export forgot nothing: the four names the old answer
    # blanked are not the profile's columns. If the profile ever grows one of
    # them, the list has to grow with it -- and until then, the list is
    # decoration.
    columns = _entity_columns(PROFILE_ENTITY)
    assert columns, "no column was read out of the profile entity: the gate would prove nothing"
    for name in ex.DEFAULT_PII_FIELDS:
        assert name not in columns, (
            f"the profile now carries `{name}`, which the anonymized export used "
            "to strip -- the list of what it removes has to grow before this goes quiet"
        )


def test_the_flag_means_the_file_is_anonymized() -> None:
    """The path the button takes, not the function behind it.

    The flag used to set the two ``anonymized`` markers and nothing else --
    and the printable document prints "（已匿名）" beside the reader's id
    because it believes them. So the file said it was anonymized while
    carrying the reader's uuid, their links, their resume's plaintext and
    every answer they gave an interviewer.

    The strip has to happen where the bundle is built, or the flag is a
    promise the file does not keep.
    """
    raw = _realistic_bundle()["data"]
    bundle = ex.build_bundle("11111111-1111-1111-1111-111111111111", raw, anonymized=True)

    assert bundle["user"]["anonymized"] is True
    assert bundle["manifest"]["anonymized"] is True
    assert bundle["user"]["id"] is None, "the bundle still carries the reader's id"
    assert bundle["data"]["profile"]["user_id"] is None
    assert bundle["data"]["contacts"][0]["name"] is None
    assert bundle["data"]["contacts"][0]["email"] is None
    assert bundle["data"]["notes"][0]["content"] is None
    assert bundle["data"]["resumes"][0]["plaintext"] is None
    assert bundle["data"]["interviews"][0]["turns"][0]["content"] is None
    assert bundle["data"]["memories"][0]["content"] is None
    assert ex.validate_bundle(bundle) == [], (
        f"the anonymized bundle is not a valid bundle: {ex.validate_bundle(bundle)}"
    )


def test_the_anonymized_export_takes_the_people_out() -> None:
    bundle = _realistic_bundle()
    out = ex.anonymize(bundle)

    profile = out["data"]["profile"]
    for field in ("user_id", "links", "summary"):
        assert profile[field] is None, f"the profile still carries its `{field}`"

    contact = out["data"]["contacts"][0]
    for field in ("name", "role", "company", "relation", "email", "notes"):
        assert contact[field] is None, f"the contact still carries its `{field}`"

    note = out["data"]["notes"][0]
    for field in ("title", "content"):
        assert note[field] is None, f"the note still carries its `{field}`"

    resume = out["data"]["resumes"][0]
    for field in ("user_id", "label", "resume_title", "plaintext", "structured"):
        assert resume[field] is None, f"the resume still carries its `{field}`"

    turn = out["data"]["interviews"][0]["turns"][0]
    for field in ("question", "content"):
        assert turn[field] is None, f"the transcript still carries its `{field}`"

    memory = out["data"]["memories"][0]
    for field in ("key", "content"):
        assert memory[field] is None, f"the memory still carries its `{field}`"

    application = out["data"]["applications"][0]
    assert application["notes"] is None, "the application still carries what the reader wrote"

    document = out["data"]["knowledge"][0]
    for field in ("user_id", "text_excerpt"):
        assert document[field] is None, f"the document still carries its `{field}`"

    assert out["user"]["id"] is None, "the envelope still carries the reader's id"
    assert out["user"]["anonymized"] is True
    assert out["manifest"]["anonymized"] is True


def test_the_anonymized_export_keeps_the_shape_and_the_substance() -> None:
    # The other half of the claim: an export that leaves nothing behind is
    # not an export. The counts still say what was there, the ids are still
    # ids, and the substance of a job search -- the posting, the headline,
    # the years -- is still in it.
    bundle = _realistic_bundle()
    out = ex.anonymize(bundle)

    assert out["manifest"]["counts"] == bundle["manifest"]["counts"], (
        "the anonymized export changed the counts: the reader cannot tell what "
        "the file holds"
    )
    assert out["data"]["profile"]["headline"] == bundle["data"]["profile"]["headline"]
    assert out["data"]["profile"]["location"] == bundle["data"]["profile"]["location"]
    assert out["data"]["job_descriptions"] == bundle["data"]["job_descriptions"], (
        "the posting is not the reader's own material: an anonymized export still "
        "carries it"
    )
    assert out["data"]["notes"][0]["id"] == bundle["data"]["notes"][0]["id"]


def test_the_anonymized_export_leaves_the_original_alone() -> None:
    bundle = _realistic_bundle()
    before = bundle["data"]["contacts"][0]["name"]
    ex.anonymize(bundle)
    assert bundle["data"]["contacts"][0]["name"] == before, (
        "the anonymized export changed the bundle it was given: the reader's own "
        "data was edited by a copy"
    )


def test_the_anonymized_export_re_stamps_the_hash() -> None:
    # The hash covers the data, so a bundle whose data changed carries a hash
    # of the old data -- and the import path would refuse it as tampered.
    bundle = _realistic_bundle()
    out = ex.anonymize(bundle)
    assert out["manifest"]["content_hash"] != bundle["manifest"]["content_hash"]
    assert ex.validate_bundle(out) == [], (
        f"the anonymized export is not a valid bundle: {ex.validate_bundle(out)}"
    )


@pytest.mark.parametrize("section", sorted(ex.ANONYMIZED_FIELDS))
def test_the_policy_names_fields_the_bundle_actually_carries(section: str) -> None:
    # The policy is written in the bundle's own field names, so a field the
    # bundle does not carry is a field the strip silently does nothing about
    # -- and the reader is still carrying it.
    bundle = _realistic_bundle()
    rows = bundle["data"].get(section)
    if isinstance(rows, dict):
        # The profile is the one section that is a single object.
        rows = [rows]
    if not isinstance(rows, list) or not rows:
        pytest.skip(f"the realistic bundle carries no {section} rows")
    for field in ex.ANONYMIZED_FIELDS[section]:
        assert field in rows[0], (
            f"the policy strips `{section}.{field}`, which the bundle does not "
            "carry: the strip does nothing and the reader keeps it"
        )
