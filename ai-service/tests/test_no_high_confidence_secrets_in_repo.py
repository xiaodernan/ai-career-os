"""Tracked files must not contain high-confidence secrets.

Epic 77 secret-scanning gate. Patterns are deliberately high-signal (private key
blocks and provider token formats) to avoid false-positive noise on legitimate
dev defaults (`dev-only-*`, `*_dev_password`, `CHANGE_ME`, example domains, which
the production guard already refuses to boot on).

Scope: all git-tracked files (source, config, docs, scripts, CI).
Reads via `git ls-files`; scans text files only.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{36,}"),
    re.compile(r"ghs_[A-Za-z0-9]{36,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),  # Slack tokens
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style secret keys
]

SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".woff", ".woff2", ".jar", ".class"}
SKIP_DIRS = {"node_modules", ".venv", ".git", "target", "backups"}


def _tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / line for line in out.splitlines() if line.strip()]


def test_no_high_confidence_secrets_in_tracked_files() -> None:
    hits = []
    for path in _tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_EXT:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat in PATTERNS:
            if pat.search(text):
                hits.append(f"{rel}: {pat.pattern}")
    assert not hits, "high-confidence secrets found in tracked files:\n" + "\n".join(hits)
