"""Flyway SQL migrations must follow the versioned naming convention.

The nightly CI applies migrations in version order by globbing `V*.sql` and
sorting (`-V`). A file that breaks the `V<digits>__<description>.sql` pattern
(or uses a non-monotonic/duplicate version) can be skipped, misordered, or cause
Flyway/runtime surprises. This gate enforces the naming pattern and unique,
strictly increasing version numbers.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "backend" / "src" / "main" / "resources" / "db" / "migration"

PATTERN = re.compile(r"^V(\d+)__([A-Za-z0-9][A-Za-z0-9_]*)\.sql$")


def test_flyway_migrations_are_named_and_versioned_monotonically() -> None:
    assert MIGRATIONS.is_dir(), f"missing migrations dir: {MIGRATIONS}"
    names = [p.name for p in MIGRATIONS.glob("*.sql")]
    assert names, "no migration files found"
    bad_names = [f for f in names if not PATTERN.match(f)]
    assert not bad_names, f"migrations with invalid Flyway names: {bad_names}"
    # Sort numerically by version (lexicographic sort would put V10 before V2).
    ordered = sorted(names, key=lambda f: int(PATTERN.match(f).group(1)))  # type: ignore[union-attr]
    versions = [int(PATTERN.match(f).group(1)) for f in ordered]  # type: ignore[union-attr]
    assert len(versions) == len(set(versions)), (
        f"duplicate migration versions: {sorted(v for v in versions if versions.count(v) > 1)}"
    )
    # Monotonic by construction after numeric sort; assert contiguous sanity holds and no absurd gaps.
    assert versions[0] >= 1
    gaps = [b - a for a, b in zip(versions, versions[1:]) if b - a > 20]
    assert not gaps, f"suspiciously large migration version gaps: {gaps} (versions={versions})"

