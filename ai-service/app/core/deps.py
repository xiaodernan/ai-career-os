from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.core.config import get_settings


@dataclass
class Ctx:
    user_id: str
    run_id: str | None = None


async def require_internal(
    x_internal_token: str = Header(default=""),
    x_user_id: str = Header(default="", alias="X-User-Id"),
    x_run_id: str = Header(default="", alias="X-Run-Id"),
) -> Ctx:
    s = get_settings()
    if x_internal_token != s.internal_api_token:
        raise HTTPException(status_code=401, detail="invalid internal token")
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-Id required")
    return Ctx(user_id=x_user_id, run_id=x_run_id or None)
