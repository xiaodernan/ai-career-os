"""Tests for the Epic 18.1 deployment preflight (offline, deterministic)."""

from app.core.config import Settings
from app.ops import preflight as P

PROD_GOOD = {
    "app_env": "prod",
    "llm_provider": "openai_compat",
    "embedding_provider": "openai",
    "internal_api_token": "a-real-random-token-not-the-default",
    "database_url": "postgresql://career:secret@db.internal:5432/career_os",
    "backend_base_url": "https://api.career-os.example",
    "llm_api_key": "sk-live",
    "embedding_api_key": "sk-emb",
    "db_pool_min": 2,
    "db_pool_max": 10,
}


def _failed_names(report):
    return {f["name"] for f in report["failures"]}


# ---------------- blocking failures ----------------


def test_prod_with_mock_llm_fails():
    s = {**PROD_GOOD, "llm_provider": "mock"}
    assert "llm_provider_not_mock" in _failed_names(P.run_preflight(s))


def test_prod_with_hash_embedding_fails():
    s = {**PROD_GOOD, "embedding_provider": "hash"}
    assert "embedding_provider_not_hash" in _failed_names(P.run_preflight(s))


def test_prod_with_default_token_fails():
    s = {**PROD_GOOD, "internal_api_token": P.DEFAULT_INTERNAL_TOKEN}
    assert "internal_token_overridden" in _failed_names(P.run_preflight(s))


def test_prod_with_default_database_fails():
    s = {**PROD_GOOD, "database_url": P.DEFAULT_DATABASE_URL}
    assert "database_url_not_default" in _failed_names(P.run_preflight(s))


def test_prod_missing_llm_key_fails():
    s = {**PROD_GOOD, "llm_api_key": ""}
    assert "llm_api_key_present" in _failed_names(P.run_preflight(s))


def test_prod_missing_embedding_key_fails():
    # ollama needs no key, so only the embedding key is missing
    s = {**PROD_GOOD, "llm_provider": "ollama", "embedding_provider": "openai",
         "llm_api_key": "", "embedding_api_key": ""}
    assert "embedding_api_key_present" in _failed_names(P.run_preflight(s))


def test_insane_pool_fails():
    s = {**PROD_GOOD, "db_pool_min": 20, "db_pool_max": 5}
    assert "db_pool_sane" in _failed_names(P.run_preflight(s))


# ---------------- allowed / warnings ----------------


def test_prod_good_config_passes():
    report = P.run_preflight(PROD_GOOD)
    assert report["ok"] is True
    assert report["failures"] == []


def test_dev_allows_offline_providers():
    s = {"app_env": "dev", "llm_provider": "mock", "embedding_provider": "hash"}
    report = P.run_preflight(s)
    assert report["ok"] is True
    # not-prod is a warning, not a blocker
    assert any(w["name"] == "app_env_is_prod" for w in report["warnings"])


def test_prod_localhost_backend_is_a_warning_not_a_failure():
    s = {**PROD_GOOD, "backend_base_url": "http://localhost:8080"}
    report = P.run_preflight(s)
    assert report["ok"] is True
    assert any(w["name"] == "backend_url_not_localhost" for w in report["warnings"])


def test_report_shape():
    report = P.run_preflight(PROD_GOOD)
    assert set(report) == {"ok", "checks", "failures", "warnings"}
    assert set(report["checks"][0]) == {"name", "ok", "severity", "detail"}


# ---------------- the defaults cannot silently drift ----------------

def test_default_constants_track_settings_defaults():
    """If config.py's published defaults change, the preflight must be re-pinned."""
    assert P.DEFAULT_INTERNAL_TOKEN == Settings().internal_api_token
    assert P.DEFAULT_DATABASE_URL == Settings().database_url


# ---------------- CLI exit code ----------------

def test_main_returns_one_on_failures(monkeypatch, capsys):
    monkeypatch.setattr("app.core.config.get_settings",
                        lambda: {**PROD_GOOD, "llm_provider": "mock"})
    assert P.main([]) == 1
    assert "blocking failure" in capsys.readouterr().out


def test_main_returns_zero_when_ok(monkeypatch, capsys):
    monkeypatch.setattr("app.core.config.get_settings", lambda: PROD_GOOD)
    assert P.main([]) == 0
    assert "preflight: OK" in capsys.readouterr().out
