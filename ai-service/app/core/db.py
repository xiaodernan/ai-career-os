import json
from collections.abc import Iterable
from typing import Any

import asyncpg

from app.core.config import get_settings

_pool: asyncpg.Pool | None = None


def vec(values: Iterable[float]) -> str:
    """Encode an embedding as a pgvector text literal."""
    return "[" + ",".join(f"{v:.7f}" for v in values) + "]"


def decode_vec(text: str | None) -> list[float]:
    if not text:
        return []
    return [float(x) for x in text.strip()[1:-1].split(",")]


async def init_db() -> asyncpg.Pool:
    global _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
    )
    return _pool


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    assert _pool is not None, "db pool not initialised"
    return _pool


async def fetch(query: str, *args: Any) -> list[asyncpg.Record]:
    async with get_pool().acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args: Any) -> asyncpg.Record | None:
    async with get_pool().acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute(query: str, *args: Any) -> str:
    async with get_pool().acquire() as conn:
        return await conn.execute(query, *args)


def jsonb(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def like_contains(term: str) -> str:
    """Encode user text as a LIKE "contains" pattern with its wildcards neutralised.

    Without this the term's own metacharacters act as operators: "%" stops the filter
    from filtering, "_" matches any character ("a_b" also hits "axb"), and a term
    containing "\\" cannot match itself because backslash is LIKE's implicit escape
    character. "!" is used as an explicit escape instead, so the result does not depend
    on standard_conforming_strings — every call site must therefore emit ESCAPE '!'.
    """
    escaped = term.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return f"%{escaped}%"