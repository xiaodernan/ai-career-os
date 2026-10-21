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

from app.features.export import SECTIONS, content_hash, section_counts

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

    The counts are recomputed too, and for the same reason the hash is: a
    manifest that still claims the dropped rows contradicts the data sitting
    next to it. The counts are what the export screen shows as badges and
    what the printable document ends with, so a stale count tells the reader
    their knowledge base is still in the file they are about to share.

    The dropped section is *absent* from ``data`` rather than emptied, and
    ``manifest.redacted_sections`` says why: a withheld section and a section
    that was always empty are different facts, and only the manifest tells
    them apart.
    """
    drop = list(drop or [])
    invalid = [s for s in drop if s not in VALID_SECTIONS]
    if invalid:
        raise ValueError(
            f"Unknown sections to drop: {invalid}. Valid: {list(VALID_SECTIONS)}"
        )

    out = deepcopy(bundle) if isinstance(bundle, dict) else {}
    data = out.get("data")
    if not isinstance(data, dict):
        data = {}
        out["data"] = data
    removed: list[str] = []
    for section in drop:
        if section in data:
            data.pop(section)
            removed.append(section)

    manifest = out.get("manifest")
    if not isinstance(manifest, dict):
        manifest = {}
        out["manifest"] = manifest
    manifest["content_hash"] = content_hash(data)
    # The counts are recomputed for the same reason the hash is: a manifest
    # that still claims the dropped rows is a manifest the bundle's own
    # data contradicts. The reader sees these counts as badges on the
    # export screen and as the last line of the printable document, so a
    # stale count says "your knowledge base is still in here" right after
    # the reader asked for it to be gone.
    manifest["counts"] = section_counts(data)
    manifest["redacted_sections"] = sorted(removed)
    return out
