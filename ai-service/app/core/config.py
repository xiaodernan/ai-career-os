from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"], env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "dev"
    service_name: str = "career-os-ai"
    port: int = 8000

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

    rerank_mode: str = "llm"  # llm | none
    rerank_model: str = ""  # empty -> reuse llm_model

    # chunking
    chunk_target_tokens: int = 350
    chunk_overlap_tokens: int = 50

    @property
    def embedding_base(self) -> str:
        return self.embedding_base_url or self.llm_base_url

    @property
    def embedding_key(self) -> str:
        return self.embedding_api_key or self.llm_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
