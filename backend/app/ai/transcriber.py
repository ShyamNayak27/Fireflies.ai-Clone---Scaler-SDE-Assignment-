"""Speech-to-text seam for live recording (docs/ARCHITECTURE.md §14). Turning on
real recording means real audio of real people goes through a third-party API —
that consent decision belongs to whoever presses record, not to this code; this
module's job is only to make the capability real and swappable.

`UnavailableTranscriber` is the default specifically so an unconfigured deployment
fails loudly and immediately (a clear job error) rather than silently accepting an
upload it can never process.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class TranscriptionUnavailable(Exception):
    pass


@dataclass
class TranscribedUtterance:
    start_ms: int
    end_ms: int
    text: str


@dataclass
class TranscriptionResult:
    utterances: list[TranscribedUtterance]
    duration_ms: int


class Transcriber(Protocol):
    async def transcribe(self, audio_path: str) -> TranscriptionResult: ...


class UnavailableTranscriber:
    async def transcribe(self, audio_path: str) -> TranscriptionResult:
        raise TranscriptionUnavailable(
            "Speech-to-text is not configured. Set TRANSCRIBER_BACKEND=openai and "
            "OPENAI_API_KEY to enable live recording transcription."
        )


class OpenAIWhisperTranscriber:
    """Uses OpenAI's transcription API with word-level timestamps
    (response_format='verbose_json', timestamp_granularities=['word']), then groups
    words back into utterances using the same merge logic the ingest normalizer uses
    for any other source (docs/ARCHITECTURE.md §5.3) — live recording is just
    another ingest source, not a special case."""

    def __init__(self, api_key: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)

    async def transcribe(self, audio_path: str) -> TranscriptionResult:
        # Recorded clips are a few minutes of compressed audio at most, but a
        # blocking `open()`/`read()` still stalls the single event loop for
        # every other in-flight request while it runs — push it to a thread.
        audio_bytes = await asyncio.to_thread(Path(audio_path).read_bytes)
        resp = await self._client.audio.transcriptions.create(
            model="whisper-1",
            file=(Path(audio_path).name, audio_bytes),
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )

        words = getattr(resp, "words", None) or []
        if not words:
            # Fall back to one utterance spanning the whole clip if the API didn't
            # return word timestamps for this model/response combination.
            text = getattr(resp, "text", "") or ""
            duration_ms = round(getattr(resp, "duration", 0.0) * 1000)
            return TranscriptionResult(
                utterances=[TranscribedUtterance(0, duration_ms, text)] if text else [],
                duration_ms=duration_ms,
            )

        utterances: list[TranscribedUtterance] = []
        buffer: list[str] = []
        buf_start = words[0].start
        prev_end = words[0].start
        gap_threshold_s = 2.0

        for w in words:
            if w.start - prev_end > gap_threshold_s and buffer:
                utterances.append(
                    TranscribedUtterance(
                        round(buf_start * 1000), round(prev_end * 1000), " ".join(buffer)
                    )
                )
                buffer = []
                buf_start = w.start
            buffer.append(w.word)
            prev_end = w.end

        if buffer:
            utterances.append(
                TranscribedUtterance(
                    round(buf_start * 1000), round(prev_end * 1000), " ".join(buffer)
                )
            )

        duration_ms = round(words[-1].end * 1000)
        return TranscriptionResult(utterances=utterances, duration_ms=duration_ms)


def get_transcriber() -> Transcriber:
    settings = get_settings()
    if settings.transcriber_backend == "openai" and settings.openai_api_key:
        return OpenAIWhisperTranscriber(settings.openai_api_key)
    return UnavailableTranscriber()
