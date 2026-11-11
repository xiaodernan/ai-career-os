import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.core.cache import close_cache, init_cache
from app.core.config import get_settings
from app.core.db import close_db, init_db
from app.core.logging import setup_logging
from app.ops.embed_jobs import embed_loop


_PUBLISHED_INTERNAL_TOKENS = {
    "shared-secret-between-backend-and-ai-service",
    "change-me",
    "CHANGE_ME",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging()
    if settings.llm_provider == "mock" and settings.app_env == "prod":
        raise RuntimeError("mock LLM provider forbidden in prod")
    if settings.voice_provider == "mock" and settings.app_env == "prod":
        raise RuntimeError("mock voice provider forbidden in prod")
    if settings.app_env == "prod":
        token = (settings.internal_api_token or "").strip()
        if not token or token in _PUBLISHED_INTERNAL_TOKENS or "CHANGE_ME" in token.upper():
            raise RuntimeError("published or empty internal API token forbidden in prod")
    pool = await init_db()
    app.state.pool = pool
    # The cache is built after the pool so a failure to reach Redis is a logged
    # degradation inside `build_cache`, never a boot failure: a cache that can stop
    # the engine from starting would be a dependency, not a cache.
    await init_cache(settings)
    # Fresh vectors without an ops step: a role created mid-session becomes
    # vector-searchable within a minute (the first pass doubles as the backfill).
    # Off (default) runs the original single-process DB scan. `redis` turns job
    # embedding into a work-queue consumer group so N replicas share the work
    # instead of each embedding the same NULL rows; it fails open to the same
    # single-process scan when Redis is down. Failures stay inside the loop.
    embed_loop_fn = embed_loop
    if getattr(settings, "work_queue_backend", "off").strip().lower() == "redis":
        from app.ops.embed_workers import embed_loop_distributed

        embed_loop_fn = embed_loop_distributed
    embed_task = asyncio.create_task(embed_loop_fn())
    try:
        yield
    finally:
        embed_task.cancel()
        with suppress(asyncio.CancelledError):
            await embed_task
        await close_cache()
        await close_db()


app = FastAPI(title="AI Career OS — AI Service", version="0.1.0", lifespan=lifespan)

from app.core.request_id import RequestIdMiddleware  # noqa: E402
app.add_middleware(RequestIdMiddleware)

from app.core.errors import register_refusal_handlers  # noqa: E402
register_refusal_handlers(app)


@app.get("/health")
async def health():
    from app.core import db
    from app.providers.registry import embeddings_ready, llm_ready

    row = await db.fetchrow("SELECT 1 AS ok")
    s = get_settings()
    return {
        "status": "ok",
        "db": bool(row),
        "llm_provider": s.llm_provider,
        "llm_ready": llm_ready(s),
        "embedding_provider": s.embedding_provider,
        "embedding_ready": embeddings_ready(s),
        "build_sha": s.app_build_sha,
    }


from app.api import agents, features, ingest, interview, memory, rag, tasks, voice  # noqa: E402

app.include_router(ingest.router)
app.include_router(rag.router)
app.include_router(agents.router)
app.include_router(interview.router)
app.include_router(memory.router)
app.include_router(tasks.router)
app.include_router(tasks.alias_router)
app.include_router(features.router)
app.include_router(voice.router)
