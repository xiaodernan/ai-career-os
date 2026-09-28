import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.db import close_db, init_db
from app.core.logging import setup_logging
from app.ops.embed_jobs import embed_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging()
    if settings.llm_provider == "mock" and settings.app_env == "prod":
        raise RuntimeError("mock LLM provider forbidden in prod")
    pool = await init_db()
    app.state.pool = pool
    # Fresh vectors without an ops step: the loop sweeps jobs.embedding IS NULL, so a
    # role created mid-session becomes vector-searchable within a minute (and the first
    # pass doubles as the startup backfill). Failures inside the loop are its own.
    embed_task = asyncio.create_task(embed_loop())
    try:
        yield
    finally:
        embed_task.cancel()
        with suppress(asyncio.CancelledError):
            await embed_task
        await close_db()


app = FastAPI(title="AI Career OS — AI Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    from app.core import db

    row = await db.fetchrow("SELECT 1 AS ok")
    s = get_settings()
    return {
        "status": "ok",
        "db": bool(row),
        "llm_provider": s.llm_provider,
        "embedding_provider": s.embedding_provider,
    }


from app.api import agents, features, ingest, interview, rag, tasks  # noqa: E402

app.include_router(ingest.router)
app.include_router(rag.router)
app.include_router(agents.router)
app.include_router(interview.router)
app.include_router(tasks.router)
app.include_router(tasks.alias_router)
app.include_router(features.router)
