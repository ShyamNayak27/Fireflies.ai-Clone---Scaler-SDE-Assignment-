"""The parser seam (docs/ARCHITECTURE.md §5.1). Same shape as
`app.ai.transcriber.Transcriber` — a small Protocol plus a registry function —
deliberately, so both "give me structured utterances from raw bytes" seams look
and behave the same way across the codebase.

`sniff` returns a confidence score in [0, 1] rather than a bool so the registry
can pick the *best* match instead of the first format that says "maybe" — several
of these formats can produce false-positive weak matches on a generic text blob
(e.g. a plain-text transcript that happens to contain a line of digits)."""
from __future__ import annotations

from typing import Protocol

from app.ingest.types import RawTranscript


class TranscriptParser(Protocol):
    name: str

    def sniff(self, raw: str, filename: str) -> float:
        """0.0 = definitely not this format, 1.0 = definitely is. Cheap, no
        exceptions — called against every registered parser for every upload."""
        ...

    def parse(self, raw: str) -> RawTranscript:
        """Only called on the winning parser. May raise IngestParseError."""
        ...


class IngestParseError(Exception):
    """Raised by a parser's .parse() when the content matched its sniff but
    turned out to be malformed enough that no reasonable transcript can be
    extracted (e.g. a .vtt with a WEBVTT header but zero valid cue blocks)."""
