"""Normalization stage (docs/ARCHITECTURE.md §5.3): turns (RawTranscript,
speaker resolution map) into a flat, timestamp-complete, merged list of
segments ready for scrubbing and then for materializing as TranscriptSegment
rows. Three jobs, always in this order:

1. Attribute each utterance to its resolved canonical speaker.
2. Fill in timing. If every utterance already carries a start_ms, timestamps are
   real (from VTT/SRT) and are kept as-is, only filling any missing end_ms from
   the next utterance's start (or a word-rate estimate for the last one). If
   *any* utterance is missing a start_ms (Otter/plain-text sources), the whole
   transcript's timing is synthesized from word count at the same
   WORDS_PER_MINUTE / GAP_PATTERN_MS model `app.seed.timing` uses, so a
   plain-text paste gets internally-consistent, monotonic timestamps instead of
   nulls — and the result is flagged `timestamps_estimated=True` so the UI/API
   can be honest about it rather than presenting guesses as fact.
3. Merge consecutive same-speaker segments that are close enough in time to be
   one continuous turn (gap <= GAP_MERGE_THRESHOLD_MS) — mirrors the exact
   `gap_threshold_s = 2.0` rule `app.ai.transcriber` uses for live ASR word
   grouping, so a transcript that was chopped into many small cues by its
   source format reads the same as one Whisper would have produced.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.ingest.speakers import UNKNOWN_SPEAKER_LABEL, ResolvedSpeaker
from app.ingest.types import RawUtterance
from app.seed.timing import GAP_PATTERN_MS, WORDS_PER_MINUTE

GAP_MERGE_THRESHOLD_MS = 2_000


@dataclass
class NormalizedSegment:
    speaker_label: str
    avatar_color: str
    text: str
    start_ms: int
    end_ms: int


@dataclass
class NormalizedTranscript:
    segments: list[NormalizedSegment]
    timestamps_estimated: bool


def _synthesize_timings(
    utterances: list[RawUtterance], speakers: dict[str, ResolvedSpeaker]
) -> list[NormalizedSegment]:
    segments: list[NormalizedSegment] = []
    cursor_ms = 0
    for i, u in enumerate(utterances):
        raw_label = u.speaker_label or UNKNOWN_SPEAKER_LABEL
        speaker = speakers[raw_label]
        word_count = max(1, len(u.text.split()))
        duration_ms = max(900, round(word_count / WORDS_PER_MINUTE * 60_000))
        segments.append(
            NormalizedSegment(
                speaker_label=speaker.label,
                avatar_color=speaker.avatar_color,
                text=u.text,
                start_ms=cursor_ms,
                end_ms=cursor_ms + duration_ms,
            )
        )
        cursor_ms += duration_ms + GAP_PATTERN_MS[i % len(GAP_PATTERN_MS)]
    return segments


def _use_real_timings(
    utterances: list[RawUtterance], speakers: dict[str, ResolvedSpeaker]
) -> list[NormalizedSegment]:
    segments: list[NormalizedSegment] = []
    for i, u in enumerate(utterances):
        raw_label = u.speaker_label or UNKNOWN_SPEAKER_LABEL
        speaker = speakers[raw_label]
        start_ms = u.start_ms or 0
        end_ms = u.end_ms
        if end_ms is None:
            next_start = utterances[i + 1].start_ms if i + 1 < len(utterances) else None
            word_count = max(1, len(u.text.split()))
            estimate = max(900, round(word_count / WORDS_PER_MINUTE * 60_000))
            end_ms = next_start if next_start is not None and next_start > start_ms else start_ms + estimate
        segments.append(
            NormalizedSegment(
                speaker_label=speaker.label,
                avatar_color=speaker.avatar_color,
                text=u.text,
                start_ms=start_ms,
                end_ms=end_ms,
            )
        )
    return segments


def _merge_consecutive(segments: list[NormalizedSegment]) -> list[NormalizedSegment]:
    if not segments:
        return []
    merged = [segments[0]]
    for seg in segments[1:]:
        prev = merged[-1]
        if seg.speaker_label == prev.speaker_label and seg.start_ms - prev.end_ms <= GAP_MERGE_THRESHOLD_MS:
            merged[-1] = NormalizedSegment(
                speaker_label=prev.speaker_label,
                avatar_color=prev.avatar_color,
                text=f"{prev.text} {seg.text}".strip(),
                start_ms=prev.start_ms,
                end_ms=max(prev.end_ms, seg.end_ms),
            )
        else:
            merged.append(seg)
    return merged


def normalize(
    utterances: list[RawUtterance], speakers: dict[str, ResolvedSpeaker]
) -> NormalizedTranscript:
    if not utterances:
        return NormalizedTranscript(segments=[], timestamps_estimated=False)

    timestamps_estimated = any(u.start_ms is None for u in utterances)
    segments = (
        _synthesize_timings(utterances, speakers)
        if timestamps_estimated
        else _use_real_timings(utterances, speakers)
    )
    return NormalizedTranscript(
        segments=_merge_consecutive(segments), timestamps_estimated=timestamps_estimated
    )
