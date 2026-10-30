"""Print-ready rendering of an export bundle (Epic 13.1, the "human-readable" half).

``export.to_markdown`` is a quick text view. This module produces a *print-ready*
HTML document (A4, page-break-friendly, monochrome) suitable for a browser "Save
as PDF" or for the optional ``to_pdf`` converter. Every field is HTML-escaped so a
resume snippet containing ``<script>`` can never become executable markup — the
bundle is user data and is treated as untrusted on render, exactly like generated
text is treated as untrusted on display elsewhere in this product.

Internal-only (no route): the backend bridge exposes the export endpoint and the
PDF converter dependency (weasyprint) is optional and imported lazily so the
module imports cleanly without it.
"""

from __future__ import annotations

import html
from typing import Any

# The section names and the document's words live in one table, in every
# language the readable half ships in -- see ``export_words``.
from app.features import export_words as words_mod


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _clip(text: Any, n: int = 280) -> str:
    s = _esc(text)
    return s if len(s) <= n else s[:n] + "…"


def _dict_obj(value: Any) -> dict:
    """A mapping value, else an empty dict -- a None or wrong-typed key can't crash."""
    return value if isinstance(value, dict) else {}


def _dicts(rows: Any) -> list:
    """The dict rows of a list, tolerating None and non-dict / non-list input.

    A section in an export bundle can be null or carry a junk entry; iterating
    it raw would render (or crash on) a string key, so each section funnels
    through here first."""
    return [r for r in (rows or []) if isinstance(r, dict)]


def _str(value: Any) -> str:
    """A field as display text; None and whitespace are empty, never "None"."""
    return str(value).strip() if value is not None else ""


def _strings(values: Any) -> list[str]:
    """The non-blank strings of a list (bullets, skills, courses)."""
    return [_str(v) for v in (values or []) if _str(v)]


def _row(label: str, value: str) -> str:
    return f'<tr><th>{_esc(label)}</th><td>{value}</td></tr>'


# The print chrome both documents share: A4-friendly, monochrome, and safe to
# break between rows rather than through them. It lived inside to_html until
# the single-version print view (19.5) needed the same layout; one copy, so a
# page that prints well in one document prints well in the other.
_PRINT_CSS = (
    "body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,"
    "sans-serif;color:#1a1a1a;line-height:1.5;max-width:820px;margin:24px auto;"
    "padding:0 20px;}"
    "h1{font-size:22px;margin:0 0 4px;}"
    "h2{font-size:16px;border-bottom:2px solid #1a1a1a;margin:28px 0 10px;"
    "padding-bottom:4px;}"
    "h3{font-size:14px;margin:16px 0 2px;}"
    ".meta{color:#666;font-size:13px;margin:0;}"
    ".meta code{background:#f3f3f3;padding:1px 4px;border-radius:3px;word-break:break-all;}"
    "table{border-collapse:collapse;width:100%;margin:6px 0;font-size:14px;}"
    "th,td{border:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top;}"
    "th{background:#f7f7f7;width:160px;font-weight:600;}"
    "ul{margin:6px 0;padding-left:18px;}"
    "li{margin:3px 0;}"
    ".note{color:#b00;font-size:13px;}"
    "@media print{body{max-width:none;margin:0;}"
    "h2{page-break-after:avoid;}tr,li{page-break-inside:avoid;}}"
)


def to_html(bundle: dict, locale: str | None = None) -> str:
    """Render the bundle as a self-contained, print-ready HTML document.

    ``locale`` is the reader's language. The document was Chinese-only, so
    an English reader's printable document was a Chinese document; the words
    now come from the shared table, and the caller says which language it
    wants. An unknown language is English rather than a guess.
    """
    words = words_mod.words(locale)
    titles = words_mod.section_titles(locale)

    bundle = bundle if isinstance(bundle, dict) else {}
    data = _dict_obj(bundle.get("data"))
    manifest = _dict_obj(bundle.get("manifest"))
    user = _dict_obj(bundle.get("user"))
    counts = _dict_obj(manifest.get("counts"))

    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append(f'<html lang="{words_mod.normalize_locale(locale)}"><head><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width, initial-scale=1">'
                 f"<title>{_esc(words['title'])}</title>")
    parts.append("<style>")
    parts.append(_PRINT_CSS)
    parts.append("</style></head><body>")

    parts.append(f"<h1>{_esc(words['title'])}</h1>")
    parts.append(f'<p class="meta">{_esc(words["generated"])}: {_esc(bundle.get("generated_at","n/a"))}</p>')
    uid = _esc(user.get("id", "n/a"))
    anon = user.get("anonymized")
    if anon:
        parts.append(f'<p class="note">{_esc(words["anonymous"])}</p>')
    parts.append(f'<p class="meta">{_esc(words["userId"])}: {uid}' +
                 (f' {_esc(words["anonymized"])}' if anon else '') + '</p>')
    parts.append(f'<p class="meta">{_esc(words["schema"])}: {_esc(manifest.get("schema_version","n/a"))}</p>')
    parts.append(f'<p class="meta">{_esc(words["contentHash"])}: <code>{_esc(manifest.get("content_hash","n/a"))}</code></p>')

    def section(title: str, body: str) -> None:
        parts.append(f"<h2>{_esc(title)}</h2>")
        parts.append(body)

    # Profile
    profile = _dict_obj(data.get("profile"))
    if profile:
        rows = "".join(
            _row(k, _clip(profile[k], 500))
            for k in ("display_name", "email", "headline", "summary")
            if profile.get(k)
        )
        section(titles["profile"], f"<table>{rows}</table>" if rows else "<p>—</p>")

    # Resumes
    resumes = _dicts(data.get("resumes"))
    if resumes:
        items = "".join(
            f"<li>{_esc(r.get('resume_title') or r.get('title'))} · "
            f"v{_esc(r.get('version','?'))} · {_clip(r.get('plaintext'))}</li>"
            for r in resumes
        )
        section(titles["resumes"], f"<ul>{items}</ul>")

    # Knowledge
    knowledge = _dicts(data.get("knowledge"))
    if knowledge:
        items = "".join(
            f"<li>{_esc(d.get('title'))} · {_esc(d.get('media_type'))} · "
            f"{_esc(d.get('status'))}</li>"
            for d in knowledge
        )
        section(titles["knowledge"], f"<ul>{items}</ul>")

    # Job descriptions
    jds = _dicts(data.get("job_descriptions"))
    if jds:
        items = "".join(
            f"<li>{_esc(j.get('title') or j.get('role'))} @ {_esc(j.get('company') or '')} "
            f"· {_clip(j.get('raw_text') or j.get('text'))}</li>"
            for j in jds
        )
        section(titles["job_descriptions"], f"<ul>{items}</ul>")

    # Interviews
    interviews = _dicts(data.get("interviews"))
    if interviews:
        items = "".join(
            f"<li>{_esc(s.get('job_title') or words['interview'])} · "
            f"{len(s.get('turns') or [])} {words['rounds']} · {_esc(s.get('status') or '')}</li>"
            for s in interviews
        )
        section(titles["interviews"], f"<ul>{items}</ul>")

    # Memories
    memories = _dicts(data.get("memories"))
    if memories:
        items = "".join(
            f"<li>[{_esc(m.get('kind'))}] {_clip(m.get('content'))}</li>"
            for m in memories
        )
        section(titles["memories"], f"<ul>{items}</ul>")

    # Applications — the pipeline the candidate actually worked.
    apps = _dicts(data.get("applications"))
    if apps:
        items = "".join(
            f"<li>{_esc(a.get('title'))} · {_esc(a.get('company_name') or '')} · "
            f"{_esc(a.get('status') or '')}"
            + (f" · {_esc(a.get('applied_at'))}" if a.get("applied_at") else "")
            + "</li>"
            for a in apps
        )
        section(titles["applications"], f"<ul>{items}</ul>")

    # Growth runs — one row per report the candidate built.
    plans = _dicts(data.get("growth_plans"))
    if plans:
        items = "".join(
            f"<li>{_esc(p.get('target_role'))} · {words['coverage']} "
            f"{_esc(round(float(p.get('coverage') or 0) * 100))}%"
            + (f" · {_esc(p.get('created_at'))}" if p.get("created_at") else "")
            + "</li>"
            for p in plans
        )
        section(titles["growth_plans"], f"<ul>{items}</ul>")

    # The notes the reader typed and the people they know. They were in the
    # bundle from 1.2.0 and missing from the document, so the readable export
    # left out the two tables the reader wrote into.
    notes = _dicts(data.get("notes"))
    if notes:
        items = "".join(
            f"<li>{_esc(n.get('title') or '')} · {_clip(n.get('content'))}</li>"
            for n in notes
        )
        section(titles["notes"], f"<ul>{items}</ul>")

    contacts = _dicts(data.get("contacts"))
    if contacts:
        items = "".join(
            f"<li>{_esc(c.get('name') or '')}"
            + (f" · {_esc(c.get('company'))}" if c.get("company") else "")
            + (f" · {_esc(c.get('relation'))}" if c.get("relation") else "")
            + (f" · {_clip(c.get('notes'))}" if c.get("notes") else "")
            + "</li>"
            for c in contacts
        )
        section(titles["contacts"], f"<ul>{items}</ul>")

    # The copilot chats (1.3.0): a title and the size of its transcript.
    chats = _dicts(data.get("conversations"))
    if chats:
        items = "".join(
            f"<li>{_esc(c.get('title') or '')} · "
            f"{len(c.get('messages') or [])} {_esc(words['messages'])}</li>"
            for c in chats
        )
        section(titles["conversations"], f"<ul>{items}</ul>")

    parts.append("<hr>")
    stat = " · ".join(f"{_esc(k)}={_esc(v)}" for k, v in counts.items())
    parts.append(f'<p class="meta">{_esc(words["stats"])}: {stat}</p>')

    parts.append("</body></html>")
    return "\n".join(parts)


def resume_to_html(resume: dict, locale: str | None = None, *, title: str = "",
                   subtitle: str = "", text: str = "") -> str:
    """One resume version as a print-ready document (19.5).

    The bundle's printable half renders every resume as one clipped bullet;
    that is a record of the search, not a resume to send. This renders a single
    version's structured body section by section, in the same print chrome and
    the same word table, so the tailoring surface can go "tailor -> print/PDF"
    without exporting the whole bundle.

    A version with no structured body (an upload that was never parsed) prints
    its stored plaintext instead of an empty page, and a version with neither
    says so with a dash rather than pretending to be a document. Every field is
    the reader's data and is escaped, like the bundle renderer's.
    """
    headings = words_mod.resume_titles(locale)
    resume = resume if isinstance(resume, dict) else {}
    profile = _dict_obj(resume.get("profile"))
    name = _str(profile.get("name")) or _str(title)
    document_title = name or _str(subtitle) or "Resume"

    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append(f'<html lang="{words_mod.normalize_locale(locale)}"><head><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width, initial-scale=1">'
                 f"<title>{_esc(document_title)}</title>")
    parts.append("<style>")
    parts.append(_PRINT_CSS)
    parts.append(".contact{color:#444;font-size:13px;margin:0 0 2px;}"
                 ".plain{white-space:pre-wrap;}")
    parts.append("</style></head><body>")

    parts.append(f"<h1>{_esc(document_title)}</h1>")
    headline = _str(profile.get("headline"))
    if headline:
        parts.append(f'<p class="contact">{_esc(headline)}</p>')
    contact = " · ".join(
        _str(profile.get(key)) for key in ("email", "phone", "location")
        if _str(profile.get(key))
    )
    if contact:
        parts.append(f'<p class="contact">{_esc(contact)}</p>')
    if _str(subtitle):
        parts.append(f'<p class="meta">{_esc(_str(subtitle))}</p>')

    written = 0

    def section(key: str, body: str) -> None:
        nonlocal written
        written += 1
        parts.append(f"<h2>{_esc(headings[key])}</h2>")
        parts.append(body)

    summary = _str(profile.get("summary"))
    if summary:
        section("summary", f"<p>{_esc(summary)}</p>")

    rows: list[str] = []
    for item in _dicts(resume.get("experience")):
        heading = " — ".join(
            part for part in (_str(item.get("title")), _str(item.get("company"))) if part
        )
        bullets = _strings(item.get("bullets"))
        if not heading and not bullets and not _str(item.get("summary")):
            continue
        chunk = f"<h3>{_esc(heading)}</h3>" if heading else ""
        when = " – ".join(
            part for part in (_str(item.get("start")), _str(item.get("end"))) if part
        )
        meta = " · ".join(part for part in (when, _str(item.get("location"))) if part)
        if meta:
            chunk += f'<p class="meta">{_esc(meta)}</p>'
        item_summary = _str(item.get("summary"))
        if item_summary:
            chunk += f"<p>{_esc(item_summary)}</p>"
        if bullets:
            chunk += "<ul>" + "".join(f"<li>{_esc(b)}</li>" for b in bullets) + "</ul>"
        rows.append(chunk)
    if rows:
        section("experience", "".join(rows))

    rows = []
    for item in _dicts(resume.get("projects")):
        heading = _str(item.get("name"))
        bullets = _strings(item.get("bullets"))
        tech = _strings(item.get("tech"))
        if not heading and not bullets and not tech:
            continue
        chunk = f"<h3>{_esc(heading)}</h3>" if heading else ""
        meta = " · ".join(
            part for part in (_str(item.get("role")), _str(item.get("period"))) if part
        )
        if meta:
            chunk += f'<p class="meta">{_esc(meta)}</p>'
        if bullets:
            chunk += "<ul>" + "".join(f"<li>{_esc(b)}</li>" for b in bullets) + "</ul>"
        if tech:
            chunk += f'<p class="meta">{_esc(", ".join(tech))}</p>'
        rows.append(chunk)
    if rows:
        section("projects", "".join(rows))

    rows = []
    for item in _dicts(resume.get("education")):
        school = _str(item.get("school"))
        degree = ", ".join(
            part for part in (_str(item.get("degree")), _str(item.get("field"))) if part
        )
        years = " – ".join(
            part for part in (_str(item.get("startYear")), _str(item.get("endYear"))) if part
        )
        gpa = _str(item.get("gpa"))
        courses = _strings(item.get("courses"))
        if not school and not degree and not years and not gpa and not courses:
            continue
        chunk = f"<h3>{_esc(school)}</h3>" if school else ""
        meta = " · ".join(
            part for part in (degree, years, f"{headings['gpa']} {gpa}" if gpa else "") if part
        )
        if meta:
            chunk += f'<p class="meta">{_esc(meta)}</p>'
        if courses:
            chunk += "<ul>" + "".join(f"<li>{_esc(c)}</li>" for c in courses) + "</ul>"
        rows.append(chunk)
    if rows:
        section("education", "".join(rows))

    # The parse schema writes skills as rows (name + category); a hand-edited or
    # model-written body sometimes carries bare strings, and both are the same
    # skill list to the reader -- so both print, the strings under no heading.
    grouped: dict[str, list[str]] = {}
    for item in resume.get("skills") or []:
        if isinstance(item, dict):
            skill, category = _str(item.get("name")), _str(item.get("category"))
        else:
            skill, category = _str(item), ""
        if skill:
            grouped.setdefault(category, []).append(skill)
    if grouped:
        items = "".join(
            f"<li>{_esc(category + ': ' if category else '')}"
            f"{_esc(', '.join(names))}</li>"
            for category, names in grouped.items()
        )
        section("skills", f"<ul>{items}</ul>")

    achievements = _strings(resume.get("achievements"))
    if achievements:
        section("achievements",
                "<ul>" + "".join(f"<li>{_esc(a)}</li>" for a in achievements) + "</ul>")

    if written == 0:
        fallback = _str(text)
        parts.append(f'<div class="plain">{_esc(fallback)}</div>' if fallback else "<p>—</p>")

    parts.append("</body></html>")
    return "\n".join(parts)


def html_to_pdf(html_text: str) -> bytes:
    """Render HTML to PDF bytes using weasyprint (optional dependency)."""
    try:
        import weasyprint  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on optional dep
        raise RuntimeError(
            "PDF rendering requires the optional 'weasyprint' dependency. "
            "Install it (pip install weasyprint) or save the HTML via a browser. "
            "The HTML output of to_html is already print-ready."
        ) from exc
    return weasyprint.HTML(string=html_text).write_pdf()


def to_pdf(bundle: dict) -> bytes:
    """Render the bundle directly to PDF bytes (see :func:`html_to_pdf`)."""
    return html_to_pdf(to_html(bundle))
