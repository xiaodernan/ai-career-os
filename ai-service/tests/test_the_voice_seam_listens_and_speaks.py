"""The voice seam (19.6): one answer in, one question out.

The interview's scoring, difficulty ladder and depth trajectory are the text
interview's; only the transport changes. Recording an answer, turning it into
words and speaking a question are therefore **enhancements**: a deployment
with no speech provider must still be able to run an interview, and it says
so -- a typed 503 -- rather than failing halfway through the reader's answer.

What this gate holds, each case born from a way the seam could lie:

* no provider means "not configured", not a crash and not an empty transcript;
* the status route reports what is configured, so the page can choose between
  the service and the browser's own speech APIs before it records anything;
* a recorded answer crosses as bytes in, words out, and a spoken question
  crosses as words in, playable audio out;
* audio that is not base64 and audio over the cap are the caller's mistakes
  and answer 400 with a code, not 500;
* the mock is test infrastructure: refused in prod, like the LLM mock.
"""

import base64
import io
import wave

import pytest
from fastapi.testclient import TestClient

from app.api import voice as voice_mod
from app.core.config import Settings, get_settings
from app.main import app
from app.providers.registry import ConfigError, get_voice, voice_configured
from app.providers.voice.mock import MOCK_TRANSCRIPT

TOKEN = get_settings().internal_api_token
USER = "00000000-0000-0000-0000-0000000000aa"
AUTH = {"X-Internal-Token": TOKEN, "X-User-Id": USER}

client = TestClient(app)


@pytest.fixture
def no_voice(monkeypatch):
    """The default deployment: no speech provider named."""
    monkeypatch.setenv("VOICE_PROVIDER", "none")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_voice(monkeypatch):
    monkeypatch.setenv("VOICE_PROVIDER", "mock")
    monkeypatch.setenv("APP_ENV", "dev")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _post(path: str, body: dict, headers: dict | None = None):
    return client.post(f"/internal/voice/{path}", json=body,
                       headers=AUTH if headers is None else headers)


def test_a_deployment_without_voice_answers_the_status_honestly(no_voice):
    response = client.get("/internal/voice/status", headers=AUTH)
    assert response.status_code == 200, response.text
    assert response.json() == {"provider": "", "stt": False, "tts": False}


def test_the_status_names_the_configured_provider(mock_voice):
    response = client.get("/internal/voice/status", headers=AUTH)
    assert response.status_code == 200, response.text
    assert response.json() == {"provider": "mock", "stt": True, "tts": True}


def test_transcribing_without_a_provider_is_a_typed_refusal(no_voice):
    response = _post("transcribe", {"audio": base64.b64encode(b"hello").decode(),
                                    "mime": "audio/webm"})
    assert response.status_code == 503, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "VOICE_NOT_CONFIGURED"
    assert "not configured" in detail["message"]
    # the reason names the setting, which is what an operator reads first
    assert "VOICE_PROVIDER" in detail["reason"] or "not configured" in detail["reason"]


def test_a_recorded_answer_comes_back_as_words(mock_voice):
    response = _post("transcribe", {"audio": base64.b64encode(b"fake-webm-bytes").decode(),
                                    "mime": "audio/webm", "locale": "zh"})
    assert response.status_code == 200, response.text
    assert response.json() == {"text": MOCK_TRANSCRIPT, "provider": "mock"}


def test_speaking_answers_playable_audio(mock_voice):
    response = _post("speak", {"text": "Tell me about a hard migration.", "locale": "en"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mime"] == "audio/wav"
    assert body["provider"] == "mock"
    audio = base64.b64decode(body["audio"])
    assert audio[:4] == b"RIFF"
    with wave.open(io.BytesIO(audio), "rb") as clip:
        assert clip.getnframes() > 0


def test_audio_that_is_not_base64_is_refused(mock_voice):
    response = _post("transcribe", {"audio": "not base64!!", "mime": "audio/webm"})
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["code"] == "VOICE_AUDIO_INVALID"


def test_audio_over_the_cap_is_refused(mock_voice, monkeypatch):
    monkeypatch.setattr(voice_mod, "MAX_AUDIO_BYTES", 4)
    response = _post("transcribe", {"audio": base64.b64encode(b"12345678").decode(),
                                    "mime": "audio/webm"})
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["code"] == "VOICE_AUDIO_TOO_LARGE"


def test_an_empty_question_is_not_spoken(mock_voice):
    response = _post("speak", {"text": ""})
    assert response.status_code == 422, response.text


def test_both_routes_require_the_internal_token(mock_voice):
    for path, body in (("transcribe", {"audio": "aGk="}), ("speak", {"text": "hi"})):
        response = _post(path, body, headers={"X-User-Id": USER})
        assert response.status_code == 401, f"{path}: {response.text}"


def test_the_mock_is_refused_in_prod():
    with pytest.raises(ConfigError):
        get_voice(Settings(voice_provider="mock", app_env="prod"))


def test_an_unknown_provider_is_a_config_error():
    with pytest.raises(ConfigError, match="unknown VOICE_PROVIDER"):
        get_voice(Settings(voice_provider="carrier-pigeon", app_env="dev"))


def test_a_provider_that_needs_a_key_says_which_variable():
    settings = Settings(voice_provider="openai_compat", app_env="dev",
                        voice_api_key="", llm_api_key="")
    with pytest.raises(ConfigError, match="VOICE_API_KEY"):
        get_voice(settings)


def test_configured_is_about_the_name_not_the_key():
    # A key-less provider is still configured: the status route is a fact
    # about the deployment's choice, and the route that uses it says why it
    # cannot reach the provider. A status that flipped to false when the key
    # was missing would also hide the setting from the operator.
    assert voice_configured(Settings(voice_provider="openai_compat"))
    assert not voice_configured(Settings(voice_provider="none"))
