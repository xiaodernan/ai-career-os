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

# Sections, in display order.
_SECTION_TITLES = {
    "profile": "个人档案",
    "resumes": "简历版本",
    "knowledge": "知识库",
    "job_descriptions": "职位描述",
    "interviews": "模拟面试",
    "memories": "长期记忆",
}


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _clip(text: Any, n: int = 280) -> str:
    s = _esc(text)
    return s if len(s) <= n else s[:n] + "…"


def _row(label: str, value: str) -> str:
    return f'<tr><th>{_esc(label)}</th><td>{value}</td></tr>'


def to_html(bundle: dict) -> str:
    """Render the bundle as a self-contained, print-ready HTML document."""
    data = bundle.get("data", {})
    manifest = bundle.get("manifest", {})
    user = bundle.get("user", {})
    counts = manifest.get("counts", {})

    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append('<html lang="zh"><head><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width, initial-scale=1">'
                 "<title>AI Career OS — 数据导出</title>")
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

    parts.append("<h1>AI Career OS — 数据导出</h1>")
    parts.append(f'<p class="meta">生成时间：{_esc(bundle.get("generated_at","n/a"))}</p>')
    uid = _esc(user.get("id", "n/a"))
    anon = user.get("anonymized")
    if anon:
        parts.append('<p class="note">⚠ 已匿名导出（个人标识字段已移除）</p>')
    parts.append(f'<p class="meta">用户 ID：{uid}' +
                 ('（已匿名）' if anon else '') + '</p>')
    parts.append(f'<p class="meta">Schema：{_esc(manifest.get("schema_version","n/a"))}</p>')
    parts.append(f'<p class="meta">内容哈希：<code>{_esc(manifest.get("content_hash","n/a"))}</code></p>')

    def section(title: str, body: str) -> None:
        parts.append(f"<h2>{_esc(title)}</h2>")
        parts.append(body)

    # Profile
    profile = data.get("profile")
    if profile:
        rows = "".join(
            _row(k, _clip(profile[k], 500))
            for k in ("display_name", "email", "headline", "summary")
            if profile.get(k)
        )
        section(_SECTION_TITLES["profile"], f"<table>{rows}</table>" if rows else "<p>—</p>")

    # Resumes
    resumes = data.get("resumes") or []
    if resumes:
        items = "".join(
            f"<li>{_esc(r.get('resume_title') or r.get('title'))} · "
            f"v{_esc(r.get('version','?'))} · {_clip(r.get('plaintext'))}</li>"
            for r in resumes
        )
        section(_SECTION_TITLES["resumes"], f"<ul>{items}</ul>")

    # Knowledge
    knowledge = data.get("knowledge") or []
    if knowledge:
        items = "".join(
            f"<li>{_esc(d.get('title'))} · {_esc(d.get('media_type'))} · "
            f"{_esc(d.get('status'))}</li>"
            for d in knowledge
        )
        section(_SECTION_TITLES["knowledge"], f"<ul>{items}</ul>")

    # Job descriptions
    jds = data.get("job_descriptions") or []
    if jds:
        items = "".join(
            f"<li>{_esc(j.get('title') or j.get('role'))} @ {_esc(j.get('company') or '')} "
            f"· {_clip(j.get('raw_text') or j.get('text'))}</li>"
            for j in jds
        )
        section(_SECTION_TITLES["job_descriptions"], f"<ul>{items}</ul>")

    # Interviews
    interviews = data.get("interviews") or []
    if interviews:
        items = "".join(
            f"<li>{_esc(s.get('job_title') or '面试')} · "
            f"{len(s.get('turns') or [])} 轮 · {_esc(s.get('status') or '')}</li>"
            for s in interviews
        )
        section(_SECTION_TITLES["interviews"], f"<ul>{items}</ul>")

    # Memories
    memories = data.get("memories") or []
    if memories:
        items = "".join(
            f"<li>[{_esc(m.get('kind'))}] {_clip(m.get('content'))}</li>"
            for m in memories
        )
        section(_SECTION_TITLES["memories"], f"<ul>{items}</ul>")

    parts.append("<hr>")
    stat = " · ".join(f"{_esc(k)}={_esc(v)}" for k, v in counts.items())
    parts.append(f'<p class="meta">统计：{stat}</p>')

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
