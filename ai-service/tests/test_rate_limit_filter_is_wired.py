"""Rate limiting must remain wired: filter exists, returns 429, and is registered.

Source-level gate for the backend rate-limit subsystem (Epic 77 coverage review):
- `RateLimitFilter` is a `OncePerRequestFilter`, maps auth/ai/mail/mfa/inbound buckets,
  and over-limit requests get HTTP 429 with code `RATE_LIMITED`.
- `SecurityConfig` registers the filter after JWT auth.
- `RateLimitMetrics` exists (decisions are instrumented).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RATE_DIR = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "ratelimit"
FILTER = RATE_DIR / "RateLimitFilter.java"
METRICS = RATE_DIR / "RateLimitMetrics.java"
CONFIG = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "config" / "SecurityConfig.java"


def test_rate_limit_filter_maps_buckets_and_returns_429() -> None:
    text = FILTER.read_text(encoding="utf-8")
    assert "OncePerRequestFilter" in text
    assert "RATE_LIMITED" in text and "429" in text
    for bucket in ('"auth"', '"ai"', '"mail"', '"mfa"', '"inbound"'):
        assert bucket in text, f"RateLimitFilter must define bucket {bucket}"
    assert "ruleFor" in text


def test_security_config_registers_rate_limit_filter_and_metrics_exist() -> None:
    cfg = CONFIG.read_text(encoding="utf-8")
    assert "rateLimitFilter" in cfg or "RateLimitFilter" in cfg
    assert "addFilterAfter(rateLimitFilter, JwtAuthFilter.class)" in cfg
    assert METRICS.is_file()
