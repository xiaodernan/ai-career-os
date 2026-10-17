"""Restore-plan CLI (forward Epic 13.2, offline).

``python -m app.ops.restore_plan backup.json [--existing current.json]`` reads an
export bundle, validates it, and prints the idempotent import plan -- per section, the
``create`` / ``update`` / ``delete`` operations with their content hashes -- **without
touching a database**. An operator can dry-run a restore, or diff a backup against the
current export, before any upsert runs.

This is the operator-facing seam between the two ai-service engines that already exist:
``features/export`` (serialize / validate / read) and ``features/import_plan`` (the
idempotent write plan). It adds no new semantics; it makes the existing pair usable from
a shell and testable end-to-end with a temp file.

Exit codes: ``0`` a plan was produced; ``2`` the file is missing, is not JSON, or fails
the bundle contract (the message says which).
"""

from __future__ import annotations

import argparse
import json
import sys

from app.features import export, import_plan


def plan_for_bundle(bundle: dict, existing: dict | None = None) -> dict:
    """Validate ``bundle`` then produce its import plan (pure).

    Raises ``ValueError`` when the bundle fails ``export.validate_bundle`` -- a
    malformed or tampered backup must be rejected *before* any write is planned.
    """
    errors = export.validate_bundle(bundle)
    if errors:
        raise ValueError("invalid bundle: " + "; ".join(errors))
    return import_plan.plan_import(bundle, existing)


def plan_from_files(bundle_path: str, existing_path: str | None = None) -> dict:
    """Read the bundle (and optional current export) from disk, then plan."""
    bundle = export.read_bundle(bundle_path)
    existing = export.read_bundle(existing_path) if existing_path else None
    return plan_for_bundle(bundle, existing)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="app.ops.restore_plan",
        description="Print the idempotent import plan for an export bundle (dry run).")
    p.add_argument("bundle", help="path to the export bundle JSON")
    p.add_argument("--existing", default=None,
                   help="optional current export to diff against (marks updates/deletes)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        plan = plan_from_files(args.bundle, args.existing)
    except (OSError, ValueError) as e:
        print(f"restore-plan: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    c = plan.get("op_counts", {})
    print(f"restore-plan: {c.get('total', 0)} ops "
          f"(create {c.get('create', 0)}, update {c.get('update', 0)}, "
          f"delete {c.get('delete', 0)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
