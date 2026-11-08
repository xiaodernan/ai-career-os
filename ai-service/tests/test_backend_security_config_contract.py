"""Backend SecurityConfig/InternalApiFilter must preserve key auth boundary invariants.

Source-level contract gate (reads Java sources). It asserts documented public
surfaces and the internal service-to-service guard wiring remain in place:
- `/api/internal/**` is reachable past Spring Security's auth rules but guarded
  by `InternalApiFilter` (X-Internal-Token), which runs before JWT auth.
- Public routes required by SECURITY.md remain permitted (auth, health, docs,
  actuator health/prometheus, mail/calendar/inbound, CORS preflight, async/error
  dispatchers).
This catches accidental removal of a boundary without needing a running JVM.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECURITY_CONFIG = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "config" / "SecurityConfig.java"
INTERNAL_FILTER = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "auth" / "security" / "InternalApiFilter.java"


def test_internal_api_surface_is_permitted_but_guarded_by_token_filter() -> None:
    cfg = SECURITY_CONFIG.read_text(encoding="utf-8")
    flt = INTERNAL_FILTER.read_text(encoding="utf-8")
    assert 'requestMatchers("/api/internal/**").permitAll()' in cfg, (
        "SecurityConfig must permit /api/internal/** at Spring Security level (guarded by InternalApiFilter)"
    )
    assert "InternalApiFilter" in cfg and "addFilterBefore(internalApiFilter, JwtAuthFilter.class)" in cfg, (
        "SecurityConfig must register InternalApiFilter before JwtAuthFilter"
    )
    assert "/api/internal" in flt, "InternalApiFilter must scope to /api/internal paths"
    assert "X-Internal-Token" in flt, "InternalApiFilter must read X-Internal-Token"
    assert "MessageDigest.isEqual" in flt, "InternalApiFilter must compare tokens in constant time"
    assert "SC_UNAUTHORIZED" in flt or "401" in flt, "InternalApiFilter must reject invalid tokens with 401"
    assert "!expected.isBlank()" in flt or "isBlank()" in flt, (
        "InternalApiFilter must reject blank/missing configured internal token (misconfiguration defense)"
    )


def test_public_routes_documented_by_security_model_remain_permitted() -> None:
    cfg = SECURITY_CONFIG.read_text(encoding="utf-8")
    required_patterns = [
        '"/api/v1/auth/**"',
        '"/api/v1/mail/**"',
        '"/api/v1/calendar.ics"',
        '"/api/v1/inbound/mail/**"',
        '"/api/v1/health"',
        '"/actuator/health", "/actuator/prometheus"',
        'DispatcherType.ASYNC, DispatcherType.ERROR',
        'HttpMethod.OPTIONS, "/**"',
    ]
    missing = [p for p in required_patterns if p not in cfg]
    assert not missing, f"SecurityConfig missing required public-route patterns: {missing}"
    # Swagger/OpenAPI docs must remain publicly reachable.
    assert "/api-docs" in cfg and "/swagger-ui" in cfg, "SecurityConfig must permit API docs/Swagger UI"
    # Frontend mints X-Request-Id per logical request; CORS must allow it, or browser preflight blocks the trace id.
    assert "setAllowedHeaders(" in cfg and '"X-Request-Id"' in cfg, (
        "SecurityConfig CORS must allow X-Request-Id (browser → backend trace propagation)"
    )
    # Default-deny: anything not explicitly permitted must require authentication.
    assert "anyRequest().authenticated()" in cfg, (
        "SecurityConfig must require authentication by default (anyRequest().authenticated())"
    )
