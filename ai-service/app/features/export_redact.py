"""Selective section redaction for export (Epic 13.3, the "forgetting" half).

``anonymize`` strips identifying *fields* while keeping every section. Sometimes
the user wants the opposite: keep their identity but drop whole sections before
sharing — e.g. export the resume + knowledge but omit interview transcripts and
long-term memories. This is the section-level counterpart to anonymize and the
privacy "right to be forgotten" at export time.

Pure and internal-only (no route): it returns a new bundle whose ``data`` no
longer carries the dropped sections, with ``manifest.content_hash`` recomputed
over the redacted data (so the bundle stays self-consistent with
``validate_bundle``) and ``manifest.redacted_sections`` recording what was
removed.
"""

from __future__ import annotations

from copy import deepcopy

from app.features.export import SECTIONS, content_hash

# The sections a bundle may carry, read off the one table that defines them --
# so a section the export gained (the backend's `applications` /
# `growth_plans`) can be dropped here too, without a second list to keep in
# step with the first.
VALID_SECTIONS = SECTIONS


def redact_bundle(bundle: dict, drop: list[str] | None = None) -> dict:
    """Return a copy of ``bundle`` with the listed sections removed from ``data``.

    Raises ``ValueError`` if any name in ``drop`` is not a valid section, so a
    typo can never silently drop the wrong (or no) section. The returned bundle
    recomputes its content hash over the redacted data and records what was
    removed in ``manifest.redacted_sections``.
    """
    drop = list(drop or [])
    invalid = [s for s in drop if s not in VALID_SECTIONS]
    if invalid:
        raise ValueError(
            f"Unknown sections to drop: {invalid}. Valid: {list(VALID_SECTIONS)}"
        )

    out = deepcopy(bundle)
    data = out.setdefault("data", {})
    removed: list[str] = []
    for section in drop:
        if section in data:
            data.pop(section)
            removed.append(section)

    manifest = out.setdefault("manifest", {})
    manifest["content_hash"] = content_hash(data)
    manifest["redacted_sections"] = sorted(removed)
    return out
