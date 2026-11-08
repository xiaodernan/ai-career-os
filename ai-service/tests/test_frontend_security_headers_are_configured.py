"""Frontend next.config must keep the baseline browser security headers.

`frontend/next.config.ts` applies headers to every route in dev and in direct
`next start` runs (not only behind a reverse proxy). Dropping a header silently
weakens the shell. This gate reads the config source and asserts the baseline set
and key values remain present.

It is a source-level contract (not a runtime header probe) so it runs without a
Node/Next runtime and stays fast/deterministic.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEXT_CONFIG = ROOT / "frontend" / "next.config.ts"


def test_frontend_security_headers_baseline_present() -> None:
    text = NEXT_CONFIG.read_text(encoding="utf-8")
    required = [
        ('X-Frame-Options', 'DENY'),
        ('X-Content-Type-Options', 'nosniff'),
        ('Referrer-Policy', 'strict-origin-when-cross-origin'),
        ('Permissions-Policy', 'camera=(), geolocation=(), microphone=(self)'),
        ('Cross-Origin-Opener-Policy', 'same-origin'),
        ('Cross-Origin-Resource-Policy', 'same-origin'),
        ('Strict-Transport-Security', 'max-age=31536000'),
    ]
    for key, value in required:
        assert key in text, f"next.config.ts missing security header {key}"
        assert value in text, f"next.config.ts missing expected value for {key}: {value}"
    assert "poweredByHeader: false" in text, "next.config.ts must disable X-Powered-By"
    assert 'source: "/:path*"' in text or "source: '/:path*'" in text, (
        "security headers must apply to all routes"
    )
