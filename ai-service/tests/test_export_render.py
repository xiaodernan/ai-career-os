"""Unit tests for the print-ready export renderer (Epic 13.1, human-readable half).

Holds: section coverage, XSS-safe escaping (user data is untrusted on render),
anonymized marking, and — only when the optional weasyprint dep is present —
the PDF path. The HTML output is the always-available deliverable; PDF is gated.
"""

import pytest

from app.features import export as ex
from app.features import export_render as rnd
from app.features import export_words as words_mod


def _bundle(anonymized: bool = False) -> dict:
    raw = {
        "profile": {
            "id": "u1", "email": "a@b.com", "display_name": "Ada",
            "headline": "Backend Engineer",
            "summary": "Built <script>alert(1)</script> things",
        },
        "resumes": [{"id": "r1", "resume_title": "Main", "version": 2,
                     "plaintext": "Exp at X"}],
        "knowledge": [{"id": "d1", "title": "Notes",
                       "media_type": "text/markdown", "status": "ready"}],
        "job_descriptions": [{"id": "j1", "title": "BE", "company": "Acme",
                              "raw_text": "JD text"}],
        "interviews": [{"id": "s1", "job_title": "BE", "status": "done",
                        "turns": [{"seq": 1}]}],
        "memories": [{"id": "m1", "kind": "preference",
                      "content": "Prefers remote"}],
        "conversations": [{"id": "v1", "title": "The search",
                           "messages": [
                               {"role": "user", "content": "find backend roles"},
                               {"role": "assistant", "content": "Here are three"},
                           ]}],
        "saved_searches": [{"id": "q1", "name": "Hangzhou senior backend",
                            "criteria": {"city": "Hangzhou", "min_years": 5}}],
        "ingestion_feeds": [{"id": "f1", "name": "Acme careers",
                             "url": "https://acme.example/careers/feed.xml",
                             "source": "rss", "enabled": True}],
    }
    return ex.build_bundle("u1", raw, anonymized=anonymized)


def test_to_html_contains_title_and_all_sections():
    bundle = _bundle()
    html = rnd.to_html(bundle)
    assert "AI Career OS" in html
    assert html.startswith("<!doctype html>")
    # Every section the bundle carries has a heading in the document, and the
    # names are asked for rather than written down -- the table has both
    # languages, and the document is in one of them.
    titles = words_mod.section_titles("en")
    zh_html = rnd.to_html(bundle, "zh")
    zh_titles = words_mod.section_titles("zh")
    for section, rows in bundle["data"].items():
        if not rows:
            continue
        assert titles[section] in html, f"the document has no heading for {section}"
        assert zh_titles[section] in zh_html, f"the Chinese document has no heading for {section}"


def test_to_html_escapes_user_content():
    html = rnd.to_html(_bundle())
    # The injected script must be neutralised, never emitted raw.
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_to_html_marks_anonymized():
    html = rnd.to_html(_bundle(anonymized=True))
    assert words_mod.words("en")["anonymized"] in html
    assert words_mod.words("zh")["anonymized"] in rnd.to_html(_bundle(anonymized=True), "zh")


def test_to_html_emits_profile_table_and_list_sections():
    html = rnd.to_html(_bundle())
    # profile rendered as a table (has <table>), resumes as a list (has <ul>)
    assert "<table>" in html
    assert "<ul>" in html


def test_to_html_carries_the_chats_with_their_transcript_lengths():
    # The chat's own title, and how much conversation is behind it: the
    # document is a look at the search, and a chat with no length is a
    # title whose substance the reader cannot see.
    html = rnd.to_html(_bundle(), "en")
    assert "The search" in html
    assert "The search · 2 messages" in html


def test_to_html_carries_the_standing_choices():
    # The saved search as the question it is -- its name and its filters on
    # one line -- and the feed as the source it points at, on or off.
    html = rnd.to_html(_bundle(), "en")
    assert "Hangzhou senior backend · city=Hangzhou · min_years=5" in html
    assert ("Acme careers · https://acme.example/careers/feed.xml · rss · "
            + words_mod.words("en")["enabled"]) in html


def test_to_html_carries_hash_and_schema():
    b = _bundle()
    html = rnd.to_html(b)
    assert b["manifest"]["content_hash"] in html
    assert b["manifest"]["schema_version"] in html


def test_html_to_pdf_requires_optional_dependency():
    pytest.importorskip("weasyprint")
    b = _bundle()
    pdf = rnd.to_pdf(b)
    assert pdf[:4] == b"%PDF"
