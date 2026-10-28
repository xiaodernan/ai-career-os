"""Deterministic mock voice -- TEST INFRASTRUCTURE ONLY.

The mock hears the same sentence whatever was said, and speaks a short tone.
That is enough to prove the seam's contract (bytes in, words out; words in,
audio out) and for a browser to actually play the answer. It is refused when
APP_ENV=prod, because a product that only pretends to listen must not ship.
"""

import io
import math
import struct
import wave

MOCK_TRANSCRIPT = "This is a mock transcript of a spoken answer."
SAMPLE_RATE = 8000
TONE_HZ = 440
SECONDS = 0.25


class MockVoice:
    name = "mock"

    async def transcribe(self, audio: bytes, mime: str, locale: str | None = None) -> str:
        return MOCK_TRANSCRIPT

    async def speak(self, text: str, locale: str | None = None) -> tuple[bytes, str]:
        frames = int(SAMPLE_RATE * SECONDS)
        samples = b"".join(
            struct.pack("<h", int(12000 * math.sin(2 * math.pi * TONE_HZ * i / SAMPLE_RATE)))
            for i in range(frames)
        )
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(samples)
        return buffer.getvalue(), "audio/wav"
