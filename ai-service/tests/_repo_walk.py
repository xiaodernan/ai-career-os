"""A pruning repo walk for the census tests.

`Path.rglob("*")` cannot prune. It descends into every directory and yields every entry,
so a census that discards `node_modules` *by name* still pays to walk it — and pays again
on every call, because these tests call their `census()` helper once per pattern.

Measured on this repo (2026-10-07), `ROOT.rglob("*")` traverses **107,781** entries, of
which **81,687 are files under `frontend/node_modules`**. Through this sandbox's
filesystem shim that made one census test take **907 seconds** — 63% of the whole
ai-service suite, which went from ~85s to ~24 minutes. `os.walk` lets the walk prune a
directory before descending into it, which is the same fix `test_response_shape_contract.py`
already applies in its `python_files()`.

The filters each census applies afterwards are unchanged: this only stops the walk from
entering directories the caller was going to discard anyway.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Directory names no census wants to read, and no walk should descend into.
SKIP_DIRS = frozenset({"node_modules", "__pycache__", "dist", "build", "target",
                       ".git", ".next", ".venv", "venv", ".mypy_cache", ".pytest_cache",
                       ".ruff_cache", "coverage", "playwright-report", "test-results"})


def walk_files(root: Path, skip_dirs: frozenset[str] | set[str] = SKIP_DIRS) -> Iterator[Path]:
    """Yield every *file* under `root`, never descending into a skipped directory.

    Dot-directories are pruned too, matching the `any(part.startswith(".") ...)` guard the
    callers already apply to the relative path — pruning here just avoids walking them.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in skip_dirs and not d.startswith("."))
        for name in sorted(filenames):
            yield Path(dirpath) / name
