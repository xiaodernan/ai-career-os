"""Import planning (Epic 13.2, the "apply" half, internal-only).

``diff_bundles`` says *what changed* between two bundles. ``plan_import`` goes one
step further: given an import bundle (and, optionally, the user's current state as
an ``existing`` bundle) it emits the concrete, idempotent write operations a
backend would execute — ``create`` for new ids, ``update`` for a known id whose
content changed, ``skip`` for a known id whose content did not, and ``delete``
for ids present in ``existing`` but absent from the (authoritative) import. Each
op carries a per-item ``content_hash``.

Pure: no I/O, no DB. The backend bridge (post-10.4) consumes this plan to perform
the actual upserts/deletes. ``validate_bundle`` runs first so a malformed or
tampered bundle is rejected before any op is planned.
"""

from __future__ import annotations

from ..core.errors import IMPORT_BUNDLE_INVALID, raise_refusal
from app.features.export import SECTIONS, content_hash, redacted_sections, validate_bundle

# Sections that are lists of addressable items; ``profile`` is a single object.
_LIST_SECTIONS = tuple(s for s in SECTIONS if s != "profile")

# The fields of a row that a restore does not write: the key it matched on, the
# account that owns the row, and the two stamps the database sets.
#
# They are excluded from the "did this row change" comparison for a reason that
# is not cosmetic: the first apply stamps ``updated_at`` (and a restored row gets
# a fresh ``created_at``), so a comparison that read the stamps would find every
# row it had just written changed, write it again, and never once answer "skip".
# Excluding them makes the comparison cover exactly the fields the apply writes,
# which is what "unchanged" is supposed to mean.
_NOT_WRITTEN = ("id", "user_id", "created_at", "updated_at")


def _identity_hash(item: dict) -> str:
    """The hash a skip is decided on: the row's content, not its bookkeeping."""
    return content_hash({k: v for k, v in item.items() if k not in _NOT_WRITTEN})


def plan_import(bundle: dict, existing: dict | None = None) -> dict:
    """Produce an idempotent write plan for importing ``bundle``.

    Returns a dict shaped::

        {
          "schema_version": str,
          "source_content_hash": str,
          "sections": { <section>: [ {"op","id","content_hash"}, ... ] },
          "op_counts": {"create": int, "update": int, "delete": int,
                        "skip": int, "total": int},
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
        ex_by_id = {it.get("id"): it for it in existing_items}
        ops: list[dict] = []
        present_ids: set = set()
        for it in items:
            iid = it.get("id")
            present_ids.add(iid)
            known = ex_by_id.get(iid)
            if known is None:
                kind = "create"
            elif _identity_hash(it) == _identity_hash(known):
                # The row is already there, and the import would write the same
                # fields over it. "Unchanged rows are skipped" is the promise the
                # preview makes; this is the op that keeps it.
                kind = "skip"
            else:
                kind = "update"
            ops.append({
                "op": kind,
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
        ex_profile = existing_data.get("profile")
        if not isinstance(ex_profile, dict) or not ex_profile:
            profile_op = "create"
        elif _identity_hash(profile) == _identity_hash(ex_profile):
            profile_op = "skip"
        else:
            profile_op = "update"
        plan["sections"]["profile"] = [{
            "op": profile_op,
            "id": profile.get("id"),
            "content_hash": content_hash(profile),
        }]

    all_ops = [op for sec in plan["sections"].values() for op in sec]
    plan["op_counts"] = {
        "create": sum(1 for o in all_ops if o["op"] == "create"),
        "update": sum(1 for o in all_ops if o["op"] == "update"),
        "delete": sum(1 for o in all_ops if o["op"] == "delete"),
        "skip": sum(1 for o in all_ops if o["op"] == "skip"),
        "total": len(all_ops),
    }
    return plan
