"""Orchestrates the full ingest pipeline (docs/ARCHITECTURE.md §5): parse ->
resolve speakers -> normalize timing/merge -> scrub. Kept as one small pure
function (no DB access) so `app/services/ingest.py` only has to worry about the
Job lifecycle and persistence around it — exactly the same split
`app/ai/transcriber.py` vs `app/services/recordings.py` already established.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ingest.normalizer import NormalizedSegment, normalize
from app.ingest.parsers import parse_transcript
from app.ingest.scrub import Scrubber
from app.ingest.speakers import resolve_speakers


@dataclass
class IngestResult:
    segments: list[NormalizedSegment]
    parser_used: str
    timestamps_estimated: bool
    speaker_count: int


def run_ingest_pipeline(raw: str, filename: str) -> IngestResult:
    raw_transcript, parser_name = parse_transcript(raw, filename)
    if not raw_transcript.utterances:
        return IngestResult(
            segments=[], parser_used=parser_name, timestamps_estimated=False, speaker_count=0
        )

    speaker_map = resolve_speakers(raw_transcript.utterances)
    normalized = normalize(raw_transcript.utterances, speaker_map)

    scrubber = Scrubber()
    canonical_labels = {s.label for s in speaker_map.values()}
    for label in canonical_labels:
        scrubber.pseudonymize_name(label)

    scrubbed_segments = [
        NormalizedSegment(
            speaker_label=scrubber.pseudonymize_name(seg.speaker_label),
            avatar_color=seg.avatar_color,
            text=scrubber.scrub_text(seg.text),
            start_ms=seg.start_ms,
            end_ms=seg.end_ms,
        )
        for seg in normalized.segments
    ]

    return IngestResult(
        segments=scrubbed_segments,
        parser_used=parser_name,
        timestamps_estimated=normalized.timestamps_estimated,
        speaker_count=len({s.speaker_label for s in scrubbed_segments}),
    )
