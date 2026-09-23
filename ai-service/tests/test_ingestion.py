"""Unit tests for ingestion clean + chunking (pure logic, no DB)."""

import io
import zipfile

import pytest

from app.ingestion import parsers
from app.ingestion.chunking import chunk_document, count_tokens, split_sections
from app.ingestion.clean import clean
from app.ingestion.parsers import ParseError, _docx, _txt, extract_text


def test_clean_dehyphenates_and_strips_noise():
    raw = "Devel-\noper experience\r\n\x00soft­ware\r"
    out = clean(raw)
    assert out == "Developer experience\nsoftware"


def test_clean_strips_page_footers_en_and_cn():
    raw = "First line.\nPage 3 of 12\nSecond line.\n第 4 页 / 共 10 页\nThird line."
    out = clean(raw)
    assert "Page 3" not in out
    assert "第 4 页" not in out
    assert "First line." in out and "Second line." in out and "Third line." in out


def test_clean_collapses_whitespace():
    out = clean("a   b \u00a0c\n\n\n\n\nd")
    assert out == "a b c\n\nd"


RESUME_MIXED = """## Experience
Senior Engineer, TechCorp
- Led payments team
专业技能
- Java, Spring Boot, MySQL, Redis
教育背景
- 本科，计算机科学
"""


def test_split_sections_recognizes_en_and_cn_headers():
    sections = split_sections(RESUME_MIXED)
    paths = [p for p, _ in sections]
    assert paths == ["Experience", "专业技能", "教育背景"]
    exp = dict(sections)["Experience"]
    assert any("TechCorp" in b for b in exp)


def test_split_sections_falls_back_to_top():
    sections = split_sections("just one line\nand another")
    assert sections[0][0] == "_top"


def test_split_sections_ignores_headers_inside_bullets():
    sections = split_sections("- Summary of achievements here\n- second bullet")
    assert sections[0][0] == "_top"


def test_chunk_document_ordinals_and_tokens():
    chunks = chunk_document(RESUME_MIXED)
    assert chunks
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    for c in chunks:
        assert c.token_count == count_tokens(c.text) > 0
    paths = {c.section_path for c in chunks}
    assert paths == {"Experience", "专业技能", "教育背景"}


def test_chunk_document_packs_oversized_section_with_overlap():
    para = ("The quick brown fox jumps over the lazy dog. " * 40).strip()
    text = f"Experience\n{para}\n"
    chunks = chunk_document(text, target=60, overlap=10)
    assert len(chunks) > 1
    for c in chunks:
        # sentence-split then packed: tolerate one target of slack from the packer
        assert c.token_count <= 60 * 2.5
    # overlapping tail: last words of chunk i appear at the start of chunk i+1
    tail_words = chunks[0].text.split()[-8:]
    assert " ".join(tail_words) in chunks[1].text


def test_chunk_document_keeps_section_path_for_citations():
    text = "项目经历\n- 基于 Spring Boot 的网关系统，使用 Redis 缓存\n"
    chunks = chunk_document(text)
    assert chunks[0].section_path == "项目经历"
    assert chunks[0].kind == "bullet_group"


# ---------------- parsers.extract_text dispatch routing ----------------


@pytest.fixture
def sentinel_probe(monkeypatch):
    # route markers: prove which private handler a given (media_type, bytes) reaches
    monkeypatch.setattr(parsers, "_pdf", lambda data: "PDF")
    monkeypatch.setattr(parsers, "_docx", lambda data: "DOCX")
    monkeypatch.setattr(parsers, "_txt", lambda data: "TXT")


def test_extract_text_routes_by_content_type(sentinel_probe):
    assert extract_text(b"whatever", "application/pdf") == "PDF"
    assert extract_text(b"whatever", "APPLICATION/PDF") == "PDF"  # case-insensitive
    docx_mt = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert extract_text(b"", docx_mt) == "DOCX"
    assert extract_text(b"", "report.docx") == "DOCX"  # .docx suffix
    assert extract_text(b"", "text/markdown") == "TXT"
    assert extract_text(b"", "text/plain") == "TXT"
    assert extract_text(b"", "") == "TXT"  # unknown media -> sniff -> txt


def test_extract_text_sniffs_magic_bytes_when_type_unhelpful(sentinel_probe):
    assert extract_text(b"%PDF-1.7 ...", "application/octet-stream") == "PDF"
    assert extract_text(b"PK\x03\x04 zip", "application/octet-stream") == "DOCX"
    assert extract_text(b"just words", "application/octet-stream") == "TXT"


# ---------------- parsers._docx XML -> text (pure, in-memory zip) ----------------


def _docx_bytes(document_xml: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", document_xml)
    return buf.getvalue()


def test_docx_renders_tabs_breaks_paragraphs_and_unescapes():
    xml = ("<w:document><w:body>"
           "<w:p><w:r><w:t>Hello</w:t></w:r><w:tab/>"
           "<w:r><w:t>World &amp; Co</w:t></w:r><w:br/>"
           "<w:r><w:t>AfterBreak</w:t></w:r></w:p>"
           "<w:p><w:r><w:t>SecondPara</w:t></w:r></w:p>"
           "</w:body></w:document>")
    out = _docx(_docx_bytes(xml))
    assert "Hello" in out and "World & Co" in out  # &amp; unescaped
    assert "&amp;" not in out and "<w:" not in out and "<w:t>" not in out  # tags stripped
    assert "\t" in out  # <w:tab/> -> tab
    assert "AfterBreak" in out and "SecondPara" in out
    assert out.splitlines()[0].startswith("Hello")


def test_docx_missing_document_part_raises_parse_error():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/other.xml", "<x/>")
    with pytest.raises(ParseError):
        _docx(buf.getvalue())


def test_docx_non_zip_bytes_raises_parse_error():
    with pytest.raises(ParseError):
        _docx(b"this is not a zip archive")


# ---------------- parsers._txt encoding cascade (locks the BOM-gating fix) ----------------


def test_txt_decodes_utf8_and_ascii_unchanged():
    assert _txt("求职简历平台".encode("utf-8")) == "求职简历平台"
    assert _txt(b"plain english resume") == "plain english resume"
    assert _txt(b"") == ""


def test_txt_decodes_gbk_chinese_without_corruption():
    # Regression: before the fix utf-16 (tried before gbk) swallowed even-length gbk
    # bytes into mojibake; a Chinese-platform GBK resume now decodes cleanly.
    assert _txt("求职简历平台".encode("gbk")) == "求职简历平台"


def test_txt_decodes_latin1_text_without_corruption():
    # Regression: utf-16 used to grab these even-length bytes as CJK garbage.
    assert _txt(b"caf\xe9 na\xefve") == "café naïve"


def test_txt_honors_utf16_only_when_bom_present():
    assert _txt("hello world".encode("utf-16")) == "hello world"  # utf-16 adds a BOM
    # BOM-less UTF-16 is intentionally NOT sniffed (it is indistinguishable from other
    # 8-bit encodings by magic bytes); the fix trades the old always-mis-decodes-even-
    # bytes behaviour for explicit, BOM-driven detection.
    assert _txt("简历".encode("utf-16-le")) != "简历"  # no BOM -> not claimed by utf-16


def test_txt_never_raises_on_stray_bytes():
    # latin-1 is the final fallback and cannot fail: arbitrary bytes always yield a str
    assert isinstance(_txt(b"\x00\x01\xfe\xff\x80\x81 random"), str)
