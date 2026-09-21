"""Document text extraction: PDF / DOCX / TXT / MARKDOWN. All inputs are untrusted."""

import io
import re
import zipfile


class ParseError(Exception):
    pass


def extract_text(data: bytes, media_type: str) -> str:
    mt = (media_type or "").lower()
    if "pdf" in mt:
        return _pdf(data)
    if "wordprocessingml" in mt or mt.endswith(".docx"):
        return _docx(data)
    if "markdown" in mt or "text" in mt or "plain" in mt:
        return _txt(data)
    # fall back on sniffing
    if data[:5] == b"%PDF-":
        return _pdf(data)
    if data[:2] == b"PK":
        return _docx(data)
    return _txt(data)


def _pdf(data: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as e:
                raise ParseError("encrypted PDF") from e
        pages = []
        for p in reader.pages[:60]:
            pages.append(p.extract_text() or "")
        text = "\n\n".join(pages)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"pdf parse failed: {e}") from e
    if not text.strip():
        raise ParseError("no extractable text (scanned image PDF is not supported yet)")
    return text


def _docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    except (KeyError, zipfile.BadZipFile) as e:
        raise ParseError(f"docx parse failed: {e}") from e
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return _unescape(text)


def _unescape(t: str) -> str:
    import html

    return html.unescape(t)


def _txt(data: bytes) -> str:
    for enc in ("utf-8", "utf-16", "gbk", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ParseError("cannot decode text file")
