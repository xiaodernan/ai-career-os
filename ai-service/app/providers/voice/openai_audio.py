"""Speech over an OpenAI-compatible audio API.

Two calls, each the provider's own shape: multipart to /audio/transcriptions
(the browser's webm/opus blob goes in as a file) and JSON to /audio/speech,
which answers the audio bytes directly. Nothing in the interview's scoring
path reads either answer -- the transcript is the answer box's text, and the
audio is what the browser plays.
"""

import httpx


class OpenAIAudioProvider:
    name = "openai_compat"

    def __init__(self, client: httpx.AsyncClient, base_url: str, api_key: str,
                 stt_model: str, tts_model: str, tts_voice: str):
        self.client = client
        self.base = base_url.rstrip("/")
        self.key = api_key
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.tts_voice = tts_voice

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.key}"}

    async def transcribe(self, audio: bytes, mime: str, locale: str | None = None) -> str:
        extension = "webm" if "webm" in (mime or "") else "wav" if "wav" in (mime or "") else "mp3"
        data = {"model": self.stt_model}
        # The transcription API takes ISO-639-1; the page speaks `en` / `zh`.
        language = (locale or "")[:2]
        if language in ("en", "zh"):
            data["language"] = language
        response = await self.client.post(
            f"{self.base}/audio/transcriptions",
            headers=self._headers(),
            files={"file": (f"answer.{extension}", audio, mime or "audio/webm")},
            data=data,
            timeout=120,
        )
        response.raise_for_status()
        return str(response.json().get("text") or "").strip()

    async def speak(self, text: str, locale: str | None = None) -> tuple[bytes, str]:
        response = await self.client.post(
            f"{self.base}/audio/speech",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={
                "model": self.tts_model,
                "voice": self.tts_voice,
                "input": text,
                "response_format": "wav",
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.content, "audio/wav"
