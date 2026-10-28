"""The voice routes (19.6): one answer in, one question out.

The seam is server-side so a deployment can choose a speech provider, but the
browser keeps its own speech APIs as the fallback -- voice is an enhancement
to the interview, never a precondition for answering one. Audio crosses the
backend's JSON bridge, so both directions travel as base64, the same shape the
render routes use for documents.

The transcript is *not* scored differently: it fills the answer box, and the
text interview's own submit path evaluates it. Recording, transcribing and
speaking change the transport, not the interview.
"""

import base64
import binascii

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.deps import Ctx, require_internal
from app.core.errors import (
    VOICE_AUDIO_INVALID,
    VOICE_AUDIO_TOO_LARGE,
    VOICE_NOT_CONFIGURED,
    VOICE_UPSTREAM_FAILED,
    RefusalError,
)
from app.providers.registry import ConfigError, get_voice, voice_configured

router = APIRouter(prefix="/internal/voice", tags=["voice"])

# A minute of speech at the browser's usual bitrate is well under a megabyte;
# ten is room for a slow, quiet answer without making the bridge a file host.
MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_SPOKEN_CHARS = 4000


class TranscribeReq(BaseModel):
    audio: str = Field(min_length=1)
    mime: str = "audio/webm"
    locale: str | None = None


class SpeakReq(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_SPOKEN_CHARS)
    locale: str | None = None


@router.get("/status")
async def status(ctx: Ctx = Depends(require_internal)):
    s = get_settings()
    configured = voice_configured(s)
    return {
        "provider": s.voice_provider if configured else "",
        "stt": configured,
        "tts": configured,
    }


def _voice():
    try:
        return get_voice()
    except ConfigError as exc:
        raise RefusalError(VOICE_NOT_CONFIGURED.with_detail({"reason": str(exc)})) from exc


@router.post("/transcribe")
async def transcribe(req: TranscribeReq, ctx: Ctx = Depends(require_internal)):
    try:
        audio = base64.b64decode(req.audio, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RefusalError(VOICE_AUDIO_INVALID) from exc
    if len(audio) > MAX_AUDIO_BYTES:
        raise RefusalError(VOICE_AUDIO_TOO_LARGE)
    provider = _voice()
    try:
        text = await provider.transcribe(audio, req.mime, req.locale)
    except Exception as exc:  # noqa: BLE001 -- a provider's failure is one answer to the caller
        raise RefusalError(VOICE_UPSTREAM_FAILED) from exc
    return {"text": text, "provider": provider.name}


@router.post("/speak")
async def speak(req: SpeakReq, ctx: Ctx = Depends(require_internal)):
    provider = _voice()
    try:
        audio, mime = await provider.speak(req.text, req.locale)
    except Exception as exc:  # noqa: BLE001
        raise RefusalError(VOICE_UPSTREAM_FAILED) from exc
    return {
        "audio": base64.b64encode(audio).decode("ascii"),
        "mime": mime,
        "provider": provider.name,
    }
