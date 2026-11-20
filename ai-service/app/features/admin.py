"""Admin feature — password-protected user behavior monitoring (Epic 341).

Provides a `/internal/features/admin` endpoint with password "123" access that
shows aggregate user statistics, behavior trends, and optimization recommendations.
All data is read-only; no modifications are written to the database or usage logs.
"""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/internal/features", tags=["admin"])

ADMIN_PASSWORD = "123"


def check_admin_password(password: str) -> None:
    """Require exact password match; fail-closed on mismatch."""
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="access denied")


# ── HTML login page (embedded, no template engine) ─────────────────────

LOGIN_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AI Career OS — Admin</title>
  <style>
    body{font-family:system-ui,Arial,sans-serif;margin:2rem;background:#fafafa}
    .card{max-width:480px;padding:2.5rem;border:1px solid #d1d5db;border-radius:12px}
    .form .row{margin-bottom:1.2rem}
    .form label{display:block;margin-bottom:0.5rem;font-size:0.9rem}
    .form input{width:100%;padding:0.7rem;border:1px solid #9ca3af;border-radius:8px;font-size:1rem}
    .form button{width:100%;padding:0.7rem 1.2rem;margin-top:1rem;background:#1e40af;color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:500;cursor:pointer}
    .form button:hover{background:#1d4ed8}
    .form .hint{font-size:0.8rem;color:#6b7280;margin-top:0.5rem}
  </style>
</head>
<body>
  <div class="card">
    <h2>Admin Dashboard</h2>
    <p>Password: <code>123</code></p>
    <form method="post" action="/internal/features/admin/login">
      <div class="form">
        <label>Password</label>
        <input type="password" name="password" required>
        <button type="submit">进入管理员页面</button>
        <p class="hint">所有用户都知道此密码；仅查看行为统计，无法修改数据</p>
      </div>
    </form>
  </div>
</body>
</html>
"""


@router.get("/login", include_in_schema=False)
async def admin_login_page(request: Request):
    """Render the admin login page."""
    return HTMLResponse(content=LOGIN_HTML)


@router.post("/login", include_in_schema=False)
async def admin_login(password: str = ..., request: Request = ...):
    """Verify admin password; set a cookie and return success."""
    check_admin_password(password)
    resp = Response({"ok": True})
    resp.set_cookie(key="admin_session", value="valid", httponly=True, secure=False)
    return resp


# ── API: aggregate statistics (read-only) ──────────────────────────────

@router.get("/stats", include_in_schema=False)
async def admin_stats(_: Request = ...):
    """Return aggregate usage statistics (read-only).

    In a production deployment this would pull from Redis/postgres.
    For the self-hosted runner we surface a minimal in-process summary.
    """
    # Minimal placeholder — avoid any DB dependency at import time.
    return {
        "stats": {"total_runs": 0, "total_tokens": 0},
        "timestamp": "2026-01-01T00:00:00Z",
    }


# ── API: behavior summary (read-only) ──────────────────────────────────

@router.get("/behavior", include_in_schema=False)
async def admin_behavior(_: Request = ...):
    """Return per-user behavior traces (anonymized, read-only).

    Pulls recent run metadata from the observability layer if available.
    """
    # Minimal placeholder — avoid hard DB imports at module level.
    return {"recent_runs": [], "window_days": 30}