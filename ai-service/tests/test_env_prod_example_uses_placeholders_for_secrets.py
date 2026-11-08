""".env.prod.example must not ship real secrets — only placeholders.

The production example is committed to the repo. Sensitive values must be obvious
placeholders (CHANGE_ME/GENERATE/REPLACE/YOUR_/TODO) or intentionally empty for
operator-generated material, never real credentials. This gate checks a curated set
of high-impact keys.

It is a guardrail against accidental secret commits in the template, not a secret
scanner for the whole repo.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / ".env.prod.example"

# Keys whose values must never look like real committed secrets in the example.
SENSITIVE_KEYS = (
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "MINIO_ROOT_PASSWORD",
    "JWT_SECRET",
    "INTERNAL_API_TOKEN",
    "APP_MAIL_LINK_SECRET",
    "APP_MFA_SECRET",
    "APP_PUSH_VAPID_PRIVATE_KEY",
)

PLACEHOLDER_MARKERS = ("CHANGE_ME", "GENERATE", "REPLACE", "YOUR_", "TODO", "CHANGEME", "EXAMPLE")


def _values_for(text: str, key: str) -> list[str]:
    vals = []
    for line in text.splitlines():
        m = re.match(rf"^{re.escape(key)}=(.*)$", line)
        if m:
            vals.append(m.group(1).strip())
    return vals


def _is_placeholder(value: str) -> bool:
    if value == "":
        return True  # intentionally blank (operator generates)
    upper = value.upper()
    return any(marker in upper for marker in PLACEHOLDER_MARKERS)


def test_env_prod_example_sensitive_values_are_placeholders() -> None:
    text = EXAMPLE.read_text(encoding="utf-8")
    problems = []
    for key in SENSITIVE_KEYS:
        vals = _values_for(text, key)
        assert vals, f"{key} missing from .env.prod.example (coverage gate owns presence; this checks safety)"
        for v in vals:
            if not _is_placeholder(v):
                problems.append((key, "<non-placeholder value>"))
            # Extra guard: even with a marker, reject obviously dev-default leaks.
            if "dev_password" in v or "password123" in v.lower():
                problems.append((key, "<contains dev/default password pattern>"))
    assert not problems, f".env.prod.example contains non-placeholder sensitive values: {problems}"
