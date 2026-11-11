from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"], env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "dev"
    service_name: str = "career-os-ai"
    port: int = 8000
    # The commit this image was built from: baked by the Dockerfile (Epic 78).
    app_build_sha: str = "dev"

    database_url: str = "postgresql://career_os:dev_pg_pass_9f3k@localhost:5432/career_os"
    db_pool_min: int = 2
    db_pool_max: int = 10

    internal_api_token: str = "shared-secret-between-backend-and-ai-service"
    backend_base_url: str = "http://localhost:8080"

    # LLM
    llm_provider: str = "openai_compat"  # openai_compat | anthropic | ollama | mock
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_timeout_s: float = 120.0
    llm_max_retries: int = 2

    # Embeddings
    embedding_provider: str = "openai"  # openai | ollama | hash
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    embedding_base_url: str = ""
    embedding_api_key: str = ""

    # Voice (19.6) -- the interview's microphone and speaker. Off unless a
    # deployment says otherwise: the browser's own speech APIs are the
    # fallback, and a server that cannot listen says so rather than guesses.
    voice_provider: str = "none"  # none | openai_compat | mock
    voice_base_url: str = ""
    voice_api_key: str = ""
    voice_stt_model: str = "whisper-1"
    voice_tts_model: str = "gpt-4o-mini-tts"
    voice_tts_voice: str = "alloy"

    rerank_mode: str = "llm"  # llm | bm25 | none
    rerank_model: str = ""  # empty -> reuse llm_model

    # Cache (Epic 118). `off` keeps every run identical to the pre-cache build, which
    # is why it is the default: a deployment opts in, and the tests that measure the
    # pipeline's model calls set `memory` explicitly.
    cache_backend: str = "off"  # off | memory | redis
    task_bus_backend: str = "memory"  # memory | redis (Streams; the SSE fan-out scale-out path)
    # Work queue (Epic 136). `off` keeps the single-process DB-scan embed loop exactly
    # as it was; `redis` turns job embedding into a consumer group so N replicas each
    # take a share instead of all N embedding the same NULL rows (billed N times).
    work_queue_backend: str = "off"  # off | redis (Streams consumer group; at-least-once)
    work_queue_claim_ms: int = 120_000  # visibility timeout: a job idle this long is re-claimed
    work_queue_maxlen: int = 10_000  # approximate stream cap; the DB is still the source of truth
    # Dead-letter (Epic 138). A job delivered more than `work_queue_max_deliveries`
    # times is moved to the DLQ instead of being re-claimed forever (a poison job
    # would otherwise burn a worker + a model call on every retry). 0 disables it.
    work_queue_max_deliveries: int = 5
    work_queue_dlq_stream: str = "careeros:jobs:embed:dlq"
    # Dead-letter cooldown (Epic 139). A job that reached the DLQ is cooled down by
    # job id for this many seconds so the producer stops re-injecting it every tick
    # (which would start a fresh attempts=0 lineage and burn a model call forever).
    # A *cooldown*, not a permanent tombstone: a transient provider outage heals on
    # its own when the window lapses; 0 disables suppression (pure Epic 138 behaviour).
    work_queue_dlq_cooldown_s: int = 900
    work_queue_dlq_guard_key: str = "careeros:jobs:embed:dlq:cooldown"
    # Read-only queue health (Epic 140). `stale_s`: a consumer heartbeat older
    # than this means the loop stopped (report "stalled"); keep it comfortably
    # above the loop interval or a slow-but-healthy loop looks dead. `backlog_warn`:
    # PEL depth at which a live queue reports "backlogged".
    work_queue_health_stale_s: int = 300
    work_queue_health_backlog_warn: int = 32
    cache_ttl_s: int = 300
    cache_max_entries: int = 2048
    redis_url: str = "redis://127.0.0.1:16380/0"
    redis_pool_size: int = 4
    redis_connect_timeout_s: float = 0.5
    redis_timeout_s: float = 0.5

    # chunking
    chunk_target_tokens: int = 350
    chunk_overlap_tokens: int = 50

    @property
    def embedding_base(self) -> str:
        return self.embedding_base_url or self.llm_base_url

    @property
    def embedding_key(self) -> str:
        return self.embedding_api_key or self.llm_api_key

    @property
    def voice_base(self) -> str:
        return self.voice_base_url or self.llm_base_url

    @property
    def voice_key(self) -> str:
        return self.voice_api_key or self.llm_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
