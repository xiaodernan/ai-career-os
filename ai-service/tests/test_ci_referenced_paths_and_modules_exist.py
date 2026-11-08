"""Key paths and modules referenced by CI workflows must exist.

The nightly/full-stack CI job invokes specific migration globs, ops modules, and
SQL files. A rename or deletion that leaves CI pointing at a missing target only
fails when the (expensive) nightly runs. This gate asserts the referenced targets
exist in the repo.

It is a static existence check (no imports of ops modules that may require heavy
deps/services beyond what's installed) — we verify the files are present.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ci_nightly_referenced_paths_exist() -> None:
    required = [
        ROOT / "backend" / "src" / "main" / "resources" / "db" / "migration",
        ROOT / "ai-service" / "ops" / "vector_index.sql",
        ROOT / "ai-service" / "app" / "ops" / "embed_jobs.py",
        ROOT / "ai-service" / "app" / "ops" / "seed_eval_corpus.py",
        ROOT / "ai-service" / "app" / "ops" / "check_export.py",
        ROOT / "ai-service" / "app" / "ops" / "nightly_report.py",
        ROOT / "scripts" / "eval-corpus.json",
        ROOT / ".github" / "workflows" / "ci.yml",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    assert not missing, f"CI-referenced paths missing: {missing}"
    # Sanity: migrations dir has at least one V*.sql (nightly globs V*.sql).
    mig = ROOT / "backend" / "src" / "main" / "resources" / "db" / "migration"
    assert list(mig.glob("V*.sql")), "no V*.sql migrations found (CI nightly expects them)"
