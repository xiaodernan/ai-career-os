"""Structure-aware chunking.

Splits cleaned text into sections (by heading lines / resume section keywords /
markdown headers), then packs blocks into ~target-token chunks with sentence-boundary
overlap, preserving a section_path for citations (e.g. "Experience > Internship").
"""

import re
from dataclasses import dataclass, field

_RESUME_HEADERS = {
    "experience", "work experience", "professional experience", "employment",
    "internship", "internships", "projects", "project experience", "education",
    "skills", "technical skills", "achievements", "awards", "honors", "publications",
    "certificates", "certifications", "summary", "objective", "profile",
    "coursework", "activities", "languages", "interests", "research",
    "工作经历", "实习经历", "项目经历", "教育背景", "教育经历", "专业技能", "技能",
    "个人总结", "荣誉奖项", "获奖", "证书", "校园活动", "研究方向", "主修课程",
}
_MD_HEADER = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
_ALLCAPS_LINE = re.compile(r"^[A-Z][A-Z\s/&+.-]{2,40}$")
_CN_SECTION = re.compile(r"^(【.+】|[一二三四五六七八九十]+[、.．]\s*\S{2,12})$")
_BULLET = re.compile(r"^\s*([-•●▪*·]|\d+[.)、])\s+")
_SENT_END = re.compile(r"(?<=[.!?。！？;；])\s+")

_enc = None


def count_tokens(text: str) -> int:
    global _enc
    if _enc is None:
        try:
            import tiktoken

            _enc = tiktoken.get_encoding("o200k_base")
        except Exception:
            _enc = False
    if _enc:
        return len(_enc.encode(text))
    # estimate: latin ~4 chars/token, CJK ~1.4 chars/token
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    return int((len(text) - cjk) / 4 + cjk / 1.4) or 1


@dataclass
class Chunk:
    ordinal: int
    text: str
    section_path: str
    kind: str  # section|bullet_group|paragraph
    token_count: int = 0
    meta: dict = field(default_factory=dict)


def _normalize_header(s: str) -> str | None:
    key = s.strip().lower().rstrip(":：")
    key = re.sub(r"[^\w\u4e00-\u9fff /&+-]", "", key)
    if key in _RESUME_HEADERS:
        return s.strip()
    if _CN_SECTION.match(s.strip()) or _ALLCAPS_LINE.match(s.strip()):
        return s.strip()
    if len(key) <= 28 and _MD_HEADER.search(s):
        return key.title()
    return None


def split_sections(text: str) -> list[tuple[str, list[str]]]:
    """Return [(section_path, [blocks...])]. Blocks = paragraphs/bullet groups."""
    sections: list[tuple[str, list[str]]] = []
    current = ""
    buf: list[str] = []

    def flush():
        if buf and any(b.strip() for b in buf):
            sections.append((current or "_top", list(buf)))
            buf.clear()

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        header = None
        m = _MD_HEADER.match(line)
        if m:
            header = m.group(2).strip()
        elif _normalize_header(line) and count_tokens(line) < 12 and not _BULLET.match(line):
            header = line
        if header:
            flush()
            current = header
            continue
        buf.append(line)
    flush()
    if not sections:
        sections = [("_top", text.split("\n"))]
    return sections


def chunk_document(text: str, target: int = 350, overlap: int = 50) -> list[Chunk]:
    chunks: list[Chunk] = []
    ordinal = 0
    for path, blocks in split_sections(text):
        # pack consecutive lines into ~target-sized pieces, sentence-split oversized
        lines: list[str] = []
        for b in blocks:
            if count_tokens(b) > target * 1.6:
                lines.extend(_sentence_split(b, target))
            else:
                lines.append(b)
        buf = ""
        for line in lines:
            candidate = (buf + "\n" + line).strip() if buf else line
            if count_tokens(candidate) > target and buf:
                ordinal = _emit(chunks, ordinal, buf, path)
                buf = _overlap_tail(buf, overlap) + ("\n" + line if line else "")
            else:
                buf = candidate
        if buf.strip():
            ordinal = _emit(chunks, ordinal, buf, path)
    return chunks


def _emit(chunks: list[Chunk], ordinal: int, text: str, path: str) -> int:
    kind = "bullet_group" if _BULLET.search(text) else "section" if path != "_top" else "paragraph"
    chunks.append(Chunk(ordinal=ordinal, text=text.strip(), section_path=path, kind=kind,
                        token_count=count_tokens(text)))
    return ordinal + 1


def _sentence_split(text: str, target: int) -> list[str]:
    sents = _SENT_END.split(text)
    out, buf = [], ""
    for s in sents:
        if not s.strip():
            continue
        if count_tokens(buf + " " + s) > target and buf:
            out.append(buf.strip())
            buf = s
        else:
            buf = (buf + " " + s).strip()
    if buf.strip():
        out.append(buf.strip())
    return out


def _overlap_tail(text: str, overlap_tokens: int) -> str:
    words = text.split()
    tail = " ".join(words[-max(15, overlap_tokens):])
    return tail
