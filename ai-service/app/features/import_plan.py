"""Import planning (Epic 13.2, the "apply" half, internal-only).

``diff_bundles`` says *what changed* between two bundles. ``plan_import`` goes one
step further: given an import bundle (and, optionally, the user's current state as
an ``existing`` bundle) it emits the concrete, idempotent write operations a
backend would execute — ``create`` for new ids, ``update`` for known ids, and
``delete`` for ids present in ``existing`` but absent from the (authoritative)
import. Each op carries a per-item ``content_hash`` so the backend can skip a
write when the payload is unchanged.

Pure: no I/O, no DB. The backend bridge (post-10.4) consumes this plan to perform
the actual upserts/deletes. ``validate_bundle`` runs first so a malformed or
tampered bundle is rejected before any op is planned.
"""

from __future__ import annotations

from ..core.errors import IMPORT_BUNDLE_INVALID, raise_refusal
from app.features.export import SECTIONS, content_hash, redacted_sections, validate_bundle

# Sections that are lists of addressable items; ``profile`` is a single object.
_LIST_SECTIONS = tuple(s for s in SECTIONS if s != "profile")


def plan_import(bundle: dict, existing: dict | None = None) -> dict:
    """Produce an idempotent write plan for importing ``bundle``.

    Returns a dict shaped::

        {
          "schema_version": str,
          "source_content_hash": str,
          "sections": { <section>: [ {"op","id","content_hash"}, ... ] },
          "op_counts": {"create": int, "update": int, "delete": int, "total": int},
        }

    Raises ``ValueError`` if the bundle fails ``validate_bundle``.
    """
    errors = validate_bundle(bundle)
    if errors:
        raise raise_refusal(IMPORT_BUNDLE_INVALID.with_detail({"errors": errors}))

    data = bundle.get("data")
    data = data if isinstance(data, dict) else {}
    existing_data = {}
    if isinstance(existing, dict):
        ed = existing.get("data")
        existing_data = ed if isinstance(ed, dict) else {}

    # A section the sharer redacted is withheld, not empty. The bundle makes
    # no claim about it, so the plan must make none either -- and a plan
    # that read "no rows here" as "delete every row there" would destroy
    # the target's own data on the strength of a section the sharer chose
    # not to share. So the redacted sections get no ops at all.
    withheld = redacted_sections(bundle)

    plan: dict = {
        "schema_version": bundle["schema_version"],
        "source_content_hash": bundle["manifest"]["content_hash"],
        "sections": {},
    }

    for section in _LIST_SECTIONS:
        if section in withheld:
            continue
        items = [it for it in (data.get(section) or []) if isinstance(it, dict)]
        existing_items = [it for it in (existing_data.get(section) or [])
                          if isinstance(it, dict)]
        ex_ids = {it.get("id") for it in existing_items}
        ops: list[dict] = []
        present_ids: set = set()
        for it in items:
            iid = it.get("id")
            present_ids.add(iid)
            ops.append({
                "op": "update" if iid in ex_ids else "create",
                "id": iid,
                "content_hash": content_hash(it),
            })
        for it in existing_items:
            if it.get("id") not in present_ids:
                ops.append({"op": "delete", "id": it.get("id"), "content_hash": None})
        plan["sections"][section] = ops

    # profile is a single object. A redacted profile is absent, so there is
    # nothing to plan for it -- the same rule as the list sections above,
    # reached by a different road.
    profile = data.get("profile")
    if isinstance(profile, dict) and profile:
        ex_profile_present = bool(existing_data.get("profile"))
        plan["sections"]["profile"] = [{
            "op": "update" if ex_profile_present else "create",
            "id": profile.get("id"),
            "content_hash": content_hash(profile),
        }]

    all_ops = [op for sec in plan["sections"].values() for op in sec]
    plan["op_counts"] = {
        "create": sum(1 for o in all_ops if o["op"] == "create"),
        "update": sum(1 for o in all_ops if o["op"] == "update"),
        "delete": sum(1 for o in all_ops if o["op"] == "delete"),
        "total": len(all_ops),
    }
    return plan
