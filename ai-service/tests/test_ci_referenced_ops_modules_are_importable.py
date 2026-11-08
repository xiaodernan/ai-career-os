"""Ops modules invoked by CI must be importable (no syntax/import-time breakage).

The nightly job runs `python -m app.ops.{embed_jobs,seed_eval_corpus,check_export,nightly_report}`.
A syntax error or broken import in these modules only surfaces during the
expensive nightly run. This gate imports each module in-process to catch
parse/import failures early (offline, no DB/network required at import time).

Note: we import by module name; modules that perform work only under `__main__`
or in explicit async entrypoints are safe to import.
"""

from __future__ import annotations

import importlib

MODULES = [
    "app.ops.embed_jobs",
    "app.ops.seed_eval_corpus",
    "app.ops.check_export",
    "app.ops.nightly_report",
]


def test_ci_referenced_ops_modules_import() -> None:
    failures = []
    for name in MODULES:
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 - gate reports the real import failure
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    assert not failures, "CI-referenced ops modules failed to import:\n" + "\n".join(failures)
