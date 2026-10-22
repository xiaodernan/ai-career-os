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


def _row(label: str, value: str) -> str:
    return f'<tr><th>{_esc(label)}</th><td>{value}</td></tr>'


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
    parts.append(
        "body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,"
        "sans-serif;color:#1a1a1a;line-height:1.5;max-width:820px;margin:24px auto;"
        "padding:0 20px;}"
        "h1{font-size:22px;margin:0 0 4px;}"
        "h2{font-size:16px;border-bottom:2px solid #1a1a1a;margin:28px 0 10px;"
        "padding-bottom:4px;}"
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

    parts.append("<hr>")
    stat = " · ".join(f"{_esc(k)}={_esc(v)}" for k, v in counts.items())
    parts.append(f'<p class="meta">{_esc(words["stats"])}: {stat}</p>')

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
