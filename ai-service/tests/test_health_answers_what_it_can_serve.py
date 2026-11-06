"""The health route says what the deployment can serve, not just what it named.

A stack that named `openai_compat` without a key answered `{"status": "ok",
"llm_provider": "openai_compat"}` while every AI call inside it 500ed on
``ConfigError: LLM_PROVIDER=openai_compat requires LLM_API_KEY`` — the probe
the compose healthcheck and the backend's dependency report read was green on
a deployment that could not serve its one job. The readiness fields close
that gap, and they are measured, not restated: ``llm_ready`` /
``embedding_ready`` build the provider through the same factories the AI
calls go through, so what health reports and what the first call raises can
never drift apart. ``status`` stays ``ok`` — the compose healthcheck and the
backend's startup gate read it as "can serve", and the readiness halves are
what a monitor reads to tell a misconfigured provider from a dead process.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.providers import registry

client = TestClient(app)


def settings(**over) -> Settings:
    """A variant with the provider knobs stated explicitly: the repo's own
    .env must not decide what a readiness case tests."""
    base = {
        "app_env": "dev",
        "llm_provider": "mock",
        "embedding_provider": "hash",
        "embedding_api_key": "",
        "llm_api_key": "",
    }
    return Settings(**{**base, **over})


def test_the_offline_pair_is_ready():
    s = settings()
    assert registry.llm_ready(s) is True
    assert registry.embeddings_ready(s) is True


def test_a_keyless_openai_compat_is_not_ready():
    # The deployment this file exists for: every AI call raised ConfigError
    # while /health said ok. Ready must follow the factory, which refuses.
    assert registry.llm_ready(settings(llm_provider="openai_compat", llm_api_key="")) is False


def test_a_keyed_openai_compat_is_ready():
    assert registry.llm_ready(settings(llm_provider="openai_compat", llm_api_key="k")) is True


def test_embedding_openai_falls_back_to_the_llm_key():
    # get_embeddings reads embedding_key -> EMBEDDING_API_KEY or LLM_API_KEY, so
    # readiness must read the same fallback, not only the embedding key's own field.
    both_empty = settings(embedding_provider="openai")
    assert registry.embeddings_ready(both_empty) is False
    llm_only = settings(embedding_provider="openai", llm_api_key="k")
    assert registry.embeddings_ready(llm_only) is True


def test_unknown_providers_are_not_ready():
    assert registry.llm_ready(settings(llm_provider="carrier_pigeon")) is False
    assert registry.embeddings_ready(settings(embedding_provider="smoke_signals")) is False


def test_mock_in_prod_is_not_ready():
    # The lifespan refuses to boot this pairing; a monitor must see the same
    # verdict from the health route rather than an ok with an unusable provider.
    s = settings(app_env="prod")
    assert registry.llm_ready(s) is False
    # hash embeddings stay legal in prod: readiness is per provider, not per env.
    assert registry.embeddings_ready(s) is True


@pytest.mark.parametrize("field", ["llm_ready", "embedding_ready"])
def test_the_health_route_carries_the_readiness_halves(monkeypatch, field):
    async def _row(_query):
        return {"ok": 1}

    monkeypatch.setattr("app.core.db.fetchrow", _row)
    monkeypatch.setattr(
        "app.main.get_settings",
        lambda: settings(llm_provider="openai_compat", llm_api_key=""),
    )
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["llm_provider"] == "openai_compat"
    assert body["llm_ready"] is False
    assert body["embedding_provider"] == "hash"
    assert body["embedding_ready"] is True
    assert field in body  # and the walk above read every field by name


def test_the_offline_stack_healths_ready(monkeypatch):
    async def _row(_query):
        return {"ok": 1}

    monkeypatch.setattr("app.core.db.fetchrow", _row)
    monkeypatch.setattr("app.main.get_settings", lambda: settings())
    body = client.get("/health").json()
    assert body["llm_ready"] is True and body["embedding_ready"] is True
