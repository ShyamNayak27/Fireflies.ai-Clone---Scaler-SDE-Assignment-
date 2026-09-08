"""Turns a plain (speaker, text) dialogue script into timestamped segments.

Real ASR exports either carry timestamps already or don't — when they don't, the
ingest normaliser (docs/ARCHITECTURE.md §5.3) synthesises them from word count at an
assumed speaking rate. This is the same estimator, reused here so hand-written seed
dialogue gets realistic, internally-consistent timing instead of hand-typed numbers
that would drift the moment a line changes.
"""

from __future__ import annotations

WORDS_PER_MINUTE = 152
GAP_PATTERN_MS = [350, 600, 450, 900, 300, 750]  # deterministic turn-gap cycle, not random


def estimate_segments(dialogue: list[tuple[str, str]]) -> list[dict]:
    """dialogue: [(speaker_name, text), ...] in order. Returns segment dicts with
    idx/speaker/start_ms/end_ms/text, ready to attach to a meeting fixture."""
    segments: list[dict] = []
    cursor_ms = 0
    for i, (speaker, text) in enumerate(dialogue):
        word_count = max(1, len(text.split()))
        duration_ms = max(900, round(word_count / WORDS_PER_MINUTE * 60_000))
        segments.append(
            {
                "idx": i,
                "speaker": speaker,
                "start_ms": cursor_ms,
                "end_ms": cursor_ms + duration_ms,
                "text": text,
            }
        )
        gap = GAP_PATTERN_MS[i % len(GAP_PATTERN_MS)]
        cursor_ms += duration_ms + gap
    return segments


def total_duration_ms(segments: list[dict]) -> int:
    return segments[-1]["end_ms"] if segments else 0
