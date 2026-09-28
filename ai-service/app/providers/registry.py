from functools import lru_cache

import httpx

from app.core.config import Settings, get_settings
from app.providers.base import EmbeddingProvider, LLMProvider
from app.providers.embeddings.hash_embed import HashEmbeddingProvider
from app.providers.llm.anthropic import AnthropicProvider
from app.providers.llm.mock import MockProvider
from app.providers.llm.ollama import OllamaProvider
from app.providers.llm.openai_compat import OpenAICompatProvider


class ConfigError(Exception):
    pass


@lru_cache
def _http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient()


def get_llm(settings: Settings | None = None) -> LLMProvider:
    s = settings or get_settings()
    if s.llm_provider == "mock":
        if s.app_env == "prod":
            raise ConfigError("mock LLM provider is not allowed in prod")
        return MockProvider()
    if not s.llm_api_key and s.llm_provider != "ollama":
        raise ConfigError(
            f"LLM_PROVIDER={s.llm_provider} requires LLM_API_KEY (see .env.example)")
    if s.llm_provider == "openai_compat":
        return OpenAICompatProvider(_http_client(), s.llm_base_url, s.llm_api_key, s.llm_model,
                                    s.llm_max_retries)
    if s.llm_provider == "anthropic":
        return AnthropicProvider(_http_client(), s.llm_base_url or "https://api.anthropic.com",
                                 s.llm_api_key, s.llm_model)
    if s.llm_provider == "ollama":
        return OllamaProvider(_http_client(), s.llm_base_url or "http://localhost:11434",
                              s.llm_model)
    raise ConfigError(f"unknown LLM_PROVIDER {s.llm_provider}")


class _BoundEmbeddings:
    """Binds model/dim so callers only pass texts (protocol EmbeddingProvider)."""

    def __init__(self, backend, model: str, dim: int, name: str):
        self._backend = backend
        self.model = model
        self.dim = dim
        self.name = name

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self._backend.embed(texts, self.model, self.dim)


def get_embeddings(settings: Settings | None = None) -> EmbeddingProvider:
    s = settings or get_settings()
    if s.embedding_provider == "hash":
        return HashEmbeddingProvider(s.embedding_dim)
    if s.embedding_provider == "ollama":
        return _BoundEmbeddings(
            OllamaProvider(_http_client(), s.embedding_base or "http://localhost:11434",
                           s.embedding_model), s.embedding_model, s.embedding_dim, "ollama")
    if s.embedding_provider == "openai":
        base = s.embedding_base or s.llm_base_url or "https://api.openai.com/v1"
        key = s.embedding_key or s.llm_api_key
        if not key:
            raise ConfigError("EMBEDDING_PROVIDER=openai requires EMBEDDING_API_KEY/LLM_API_KEY")
        return _BoundEmbeddings(
            OpenAICompatProvider(_http_client(), base, key, s.embedding_model),
            s.embedding_model, s.embedding_dim, "openai")
    raise ConfigError(f"unknown EMBEDDING_PROVIDER {s.embedding_provider}")


async def embed_text(text: str) -> list[float] | None:
    """Embed one text with the configured provider, or None when that is impossible.

    Semantic recall is an enhancement, never a precondition: no provider configured,
    a provider that errors, or one that answers with nothing must leave the caller
    with keyword-only results instead of an exception.
    """
    try:
        vectors = await get_embeddings(get_settings()).embed([text])
    except Exception:  # noqa: BLE001 -- degrade to keyword-only, never break the caller
        return None
    return vectors[0] if vectors else None
