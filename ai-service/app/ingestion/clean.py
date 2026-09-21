"""Text cleaning for ingestion. Conservative: never remove content, only noise."""

import re
import unicodedata

_PAGE_FOOTER = re.compile(
    r"(?m)^\s*(page\s+\d+(\s+of\s+\d+)?|\d+\s*/\s*\d+|第\s*\d+\s*页(\s*/?\s*共\s*\d+\s*页)?)"
    r"\s*$", re.IGNORECASE)
_SOFT_HYPHEN = re.compile(r"\u00ad")
_HYPHEN_NEWLINE = re.compile(r"(\w)-\n(\w)")
_WS = re.compile(r"[ \t\u00a0]+")
_MANY_BLANK = re.compile(r"\n{3,}")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CTRL.sub("", text)
    text = _SOFT_HYPHEN.sub("", text)
    text = _HYPHEN_NEWLINE.sub(r"\1\2", text)  # de-hyphenate line-wrapped words
    text = _PAGE_FOOTER.sub("\n", text)
    text = _WS.sub(" ", text)
    text = _MANY_BLANK.sub("\n\n", text)
    return text.strip()
