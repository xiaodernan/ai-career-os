"""Unit tests for the print-ready export renderer (Epic 13.1, human-readable half).

Holds: section coverage, XSS-safe escaping (user data is untrusted on render),
anonymized marking, and — only when the optional weasyprint dep is present —
the PDF path. The HTML output is the always-available deliverable; PDF is gated.
"""

import pytest

from app.features import export as ex
from app.features import export_render as rnd


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
    }
    return ex.build_bundle("u1", raw, anonymized=anonymized)


def test_to_html_contains_title_and_all_sections():
    html = rnd.to_html(_bundle())
    assert "AI Career OS" in html
    assert html.startswith("<!doctype html>")
    for title in ("个人档案", "简历版本", "知识库", "职位描述", "模拟面试", "长期记忆"):
        assert title in html


def test_to_html_escapes_user_content():
    html = rnd.to_html(_bundle())
    # The injected script must be neutralised, never emitted raw.
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_to_html_marks_anonymized():
    html = rnd.to_html(_bundle(anonymized=True))
    assert "已匿名" in html


def test_to_html_emits_profile_table_and_list_sections():
    html = rnd.to_html(_bundle())
    # profile rendered as a table (has <table>), resumes as a list (has <ul>)
    assert "<table>" in html
    assert "<ul>" in html


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
