"""Unit tests for ingestion clean + chunking (pure logic, no DB)."""

from app.ingestion.chunking import chunk_document, count_tokens, split_sections
from app.ingestion.clean import clean


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
