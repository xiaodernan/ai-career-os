"""The voice seam: one interface for hearing an answer and speaking a question.

The interview's scoring, difficulty ladder and depth trajectory are the text
interview's -- only the transport changes. A deployment that configures a
provider gets server-side speech; one that does not leaves the browser its
own speech APIs, which is why every call here is an enhancement and never a
precondition for answering.
"""

from typing import Protocol


class Transcriber(Protocol):
    name: str

    async def transcribe(self, audio: bytes, mime: str, locale: str | None = None) -> str:
        """The words in one recorded answer, in whatever language was spoken."""
        ...


class Synthesizer(Protocol):
    name: str

    async def speak(self, text: str, locale: str | None = None) -> tuple[bytes, str]:
        """One question as audio, plus the mime type the browser should play it as."""
        ...


class Voice(Transcriber, Synthesizer, Protocol):
    """One provider for both directions, which is what the registry hands out."""
