"""Parser registry (docs/ARCHITECTURE.md §5.1). Every upload is sniffed against
every registered parser; the highest-confidence match parses it. Order in
`_PARSERS` is the tiebreak when two parsers report the same score, and
`PlainTextFallbackParser` is last on purpose so it only wins when nothing more
specific claimed a higher score.

Genuinely supported formats: VTT (also covers Zoom's .vtt export), SRT, an
Otter.ai-style plain-text paste, and a generic plain-text fallback. The original
architecture sketch also listed Teams and Minutes-PDF exports and a raw-JSON
format; those are NOT implemented — there was no real per-vendor sample to
build and verify a parser against, and a parser nobody has tested against a
real export is worse than an honest "not supported yet". See ARCHITECTURE.md §5.1.
"""

from __future__ import annotations

from app.ingest.parsers.base import IngestParseError, TranscriptParser
from app.ingest.parsers.plaintext import OtterTextParser, PlainTextFallbackParser
from app.ingest.parsers.srt import SrtParser
from app.ingest.parsers.vtt import VttParser
from app.ingest.types import RawTranscript

_PARSERS: list[TranscriptParser] = [
    VttParser(),
    SrtParser(),
    OtterTextParser(),
    PlainTextFallbackParser(),
]

SNIFF_THRESHOLD = 0.05


class NoParserMatchedError(Exception):
    pass


def detect_parser(raw: str, filename: str) -> TranscriptParser:
    scored = [(p.sniff(raw, filename), p) for p in _PARSERS]
    best_score, best_parser = max(scored, key=lambda pair: pair[0])
    if best_score < SNIFF_THRESHOLD:
        raise NoParserMatchedError(
            "Could not detect a supported transcript format (VTT, SRT, or plain text)."
        )
    return best_parser


def parse_transcript(raw: str, filename: str) -> tuple[RawTranscript, str]:
    """Returns (parsed transcript, name of the parser that was used) — the name
    is threaded through to the Job payload/error so a failed ingest tells the
    user which format detection picked, not just that parsing failed."""
    parser = detect_parser(raw, filename)
    return parser.parse(raw), parser.name


__all__ = ["IngestParseError", "NoParserMatchedError", "detect_parser", "parse_transcript"]
