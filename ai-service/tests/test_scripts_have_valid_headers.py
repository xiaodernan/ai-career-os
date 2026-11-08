"""Operational scripts must have valid interpreter headers.

`scripts/*.sh` run in CI/Linux environments and must declare a bash/sh shebang.
`scripts/*.py` should be parseable (syntax check) so broken helpers fail early.
This is a lightweight hygiene gate (no execution).
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def test_shell_scripts_have_shebangs() -> None:
    assert SCRIPTS.is_dir()
    sh = sorted(SCRIPTS.glob("*.sh"))
    assert sh, "expected shell scripts under scripts/"
    bad = []
    for p in sh:
        first = p.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
        line = first[0] if first else ""
        if not (line.startswith("#!/usr/bin/env bash") or line.startswith("#!/bin/bash") or line.startswith("#!/usr/bin/env sh") or line.startswith("#!/bin/sh")):
            bad.append(f"{p.name}: {line!r}")
    assert not bad, f"shell scripts missing valid shebang: {bad}"


def test_python_scripts_are_syntax_valid() -> None:
    py = sorted(SCRIPTS.glob("*.py"))
    assert py, "expected python scripts under scripts/"
    bad = []
    for p in py:
        try:
            ast.parse(p.read_text(encoding="utf-8", errors="replace"), filename=str(p))
        except SyntaxError as e:
            bad.append(f"{p.name}:{e.lineno}: {e.msg}")
    assert not bad, "python scripts have syntax errors:\n" + "\n".join(bad)
