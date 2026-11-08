"""Backend password encoder must use BCrypt $2B at strength 12.

Matches SECURITY.md's documented password hashing contract. Weakening strength or
algorithm silently degrades credential storage security.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECURITY_CONFIG = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "config" / "SecurityConfig.java"


def test_password_encoder_uses_bcrypt_2b_strength_12() -> None:
    text = SECURITY_CONFIG.read_text(encoding="utf-8")
    assert "BCryptPasswordEncoder" in text
    assert "$2B" in text or "BCryptVersion.$2B" in text, "password encoder must use BCrypt $2B"
    assert "12" in text and "BCryptPasswordEncoder" in text, "password encoder must use strength 12"
    # Stronger assertion on the actual construction shape.
    assert "BCryptPasswordEncoder(BCryptPasswordEncoder.BCryptVersion.$2B, 12)" in text or (
        "BCryptVersion.$2B" in text and ", 12" in text
    ), "expected BCrypt $2B with strength 12"
