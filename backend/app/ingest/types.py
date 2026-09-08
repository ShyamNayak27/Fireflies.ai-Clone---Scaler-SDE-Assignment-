"""Shared shapes for the ingest pipeline (docs/ARCHITECTURE.md §5). A parser's
job ends at RawTranscript — everything after that (speaker resolution,
normalization, scrubbing) is format-agnostic and lives in its own module."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawUtterance:
    """One line/cue as a parser found it — before any cleanup. speaker_label
    is exactly what the source file said (or None if the format doesn't carry
    speaker info at all, e.g. a bare .txt paste); start_ms/end_ms are None
    when the source has no timestamps, which the normalizer synthesizes."""

    speaker_label: str | None
    text: str
    start_ms: int | None = None
    end_ms: int | None = None


@dataclass
class RawTranscript:
    utterances: list[RawUtterance] = field(default_factory=list)
    title_hint: str | None = None  # a few formats carry a title/subject line
