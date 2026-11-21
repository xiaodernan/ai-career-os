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


def test_portfolio_sync_regenerates_the_fact_pack_before_publishing() -> None:
    """The 'latest results' sync must measure the head it actually checked out.

    The workflow once copied a checked-in snapshot verbatim; the site then said
    Epic 353 while the repo was two epics later. It also used `pwsh`, which is
    absent on this Windows runner, so neither failure was visible in the UI.
    """
    workflow = (
        ROOT / ".github" / "workflows" / "sync-career-os.yml"
    ).read_text(encoding="utf-8")
    generator = (ROOT / "scripts" / "showcase-sync.py").read_text(encoding="utf-8")

    assert "shell: pwsh" not in workflow
    assert "scripts/showcase-sync.py" in workflow
    assert "regenerate" in workflow.lower()
    # The regeneration has to happen before the pack is read and pushed.
    regen_at = workflow.index("Regenerate the fact pack")
    facts_at = workflow.index("Read the source head and validate the fact pack")
    copy_at = workflow.index("Copy the fact pack and push only if it moved")
    assert regen_at < facts_at < copy_at
    # Refuse a pack that does not describe this checkout, and write outputs
    # without the UTF-8 BOM that PowerShell 5.1's Out-File would add.
    assert "git rev-parse --short=7 HEAD" in workflow
    assert "does not match checkout" in workflow
    assert "[IO.File]::AppendAllText" in workflow

    # The generator itself derives the head from git, not from a hand-edited
    # constant, so a fresh checkout cannot publish somebody else's snapshot.
    assert 'git", "rev-parse", "--short=7", "HEAD"' in generator
    assert '"head": head' in generator
