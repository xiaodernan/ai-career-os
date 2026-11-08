"""frontend/package.json and package-lock.json must stay consistent.

CI uses `npm ci`, which fails when the lock file doesn't match package.json.
This gate asserts the lock's root package version/name match package.json and
that every direct dependency in package.json appears in the lock's root deps.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "frontend" / "package.json"
LOCK = ROOT / "frontend" / "package-lock.json"


def test_frontend_lock_matches_package_json_for_ci() -> None:
    pkg = json.loads(PKG.read_text(encoding="utf-8"))
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    # Lockfile v2/v3: `packages[""]` mirrors root package.json.
    packages = lock.get("packages") or {}
    root_pkg = packages.get("") or {}
    assert root_pkg.get("name") == pkg.get("name"), "lock root name != package.json name"
    assert root_pkg.get("version") == pkg.get("version"), "lock root version != package.json version"
    # Every direct dependency/devDependency version must be present in the lock root's deps maps
    # (npm lock root records resolved specs; presence check is enough for consistency).
    lock_deps = {**(root_pkg.get("dependencies") or {}), **(root_pkg.get("devDependencies") or {})}
    pkg_deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    missing = [name for name in pkg_deps if name not in lock_deps]
    assert not missing, f"package-lock.json root missing direct deps from package.json: {missing}"
