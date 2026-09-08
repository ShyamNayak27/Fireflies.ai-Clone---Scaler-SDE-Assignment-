"""Normalization stage (docs/ARCHITECTURE.md §5.3): timing synthesis/passthrough
and the gap-merge rule."""
from __future__ import annotations

from app.ingest.normalizer import GAP_MERGE_THRESHOLD_MS, normalize
from app.ingest.speakers import ResolvedSpeaker, resolve_speakers
from app.ingest.types import RawUtterance


def _speakers_for(utterances: list[RawUtterance]) -> dict[str, ResolvedSpeaker]:
    return resolve_speakers(utterances)


def test_real_timestamps_are_kept_verbatim() -> None:
    utterances = [
        RawUtterance(speaker_label="Alex", text="Hi", start_ms=0, end_ms=1000),
        RawUtterance(speaker_label="Priya", text="Hello", start_ms=1000, end_ms=2000),
    ]
    result = normalize(utterances, _speakers_for(utterances))
    assert result.timestamps_estimated is False
    assert [s.start_ms for s in result.segments] == [0, 1000]


def test_missing_start_ms_triggers_synthesized_timing_for_the_whole_transcript() -> None:
    utterances = [
        RawUtterance(speaker_label="Alex", text="Hi there", start_ms=0, end_ms=1000),
        RawUtterance(speaker_label="Priya", text="Hello back", start_ms=None, end_ms=None),
    ]
    result = normalize(utterances, _speakers_for(utterances))
    assert result.timestamps_estimated is True
    # Synthesized timing is monotonic and every segment gets real start/end ints.
    starts = [s.start_ms for s in result.segments]
    assert starts == sorted(starts)
    assert all(isinstance(s.start_ms, int) and isinstance(s.end_ms, int) for s in result.segments)


def test_missing_end_ms_is_filled_from_next_utterance_start() -> None:
    utterances = [
        RawUtterance(speaker_label="Alex", text="Hi", start_ms=0, end_ms=None),
        RawUtterance(speaker_label="Priya", text="Hello", start_ms=1500, end_ms=2500),
    ]
    result = normalize(utterances, _speakers_for(utterances))
    assert result.segments[0].end_ms == 1500


def test_close_same_speaker_utterances_merge() -> None:
    utterances = [
        RawUtterance(speaker_label="Alex", text="First part.", start_ms=0, end_ms=1000),
        RawUtterance(
            speaker_label="Alex", text="Second part.", start_ms=1000 + GAP_MERGE_THRESHOLD_MS - 1, end_ms=3000
        ),
    ]
    result = normalize(utterances, _speakers_for(utterances))
    assert len(result.segments) == 1
    assert result.segments[0].text == "First part. Second part."
    assert result.segments[0].end_ms == 3000


def test_far_apart_same_speaker_utterances_do_not_merge() -> None:
    utterances = [
        RawUtterance(speaker_label="Alex", text="First part.", start_ms=0, end_ms=1000),
        RawUtterance(
            speaker_label="Alex", text="Second part.", start_ms=1000 + GAP_MERGE_THRESHOLD_MS + 1, end_ms=5000
        ),
    ]
    result = normalize(utterances, _speakers_for(utterances))
    assert len(result.segments) == 2


def test_different_speakers_never_merge_even_if_adjacent() -> None:
    utterances = [
        RawUtterance(speaker_label="Alex", text="Hi", start_ms=0, end_ms=500),
        RawUtterance(speaker_label="Priya", text="Hello", start_ms=500, end_ms=1000),
    ]
    result = normalize(utterances, _speakers_for(utterances))
    assert len(result.segments) == 2


def test_empty_transcript_normalizes_to_empty_segments() -> None:
    result = normalize([], {})
    assert result.segments == []
    assert result.timestamps_estimated is False
