"""SubRip (.srt) parser. Structurally identical to VTT except the timestamp
separator is a comma instead of a dot and every cue is prefixed with a numeric
index line — genuinely a different format worth its own parser (not just a VTT
variant) because that index line and the comma-decimal are enough to make a
regex written for one silently mis-parse the other."""

from __future__ import annotations

import re

from app.ingest.parsers.base import IngestParseError
from app.ingest.parsers.vtt import _SPEAKER_PREFIX_RE, _TAG_RE  # shared, format-agnostic
from app.ingest.types import RawTranscript, RawUtterance

_INDEX_RE = re.compile(r"^\d+$")
_TIMESTAMP_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
)


def _ts_to_ms(h: str, m: str, s: str, ms: str) -> int:
    return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)


class SrtParser:
    name = "srt"

    def sniff(self, raw: str, filename: str) -> float:
        if _TIMESTAMP_RE.search(raw) is None:
            return 0.0
        score = 0.5
        if filename.lower().endswith(".srt"):
            score += 0.3
        if re.search(r"^\d+\s*$", raw.strip().splitlines()[0] if raw.strip() else ""):
            score += 0.15
        return min(score, 0.9)

    def parse(self, raw: str) -> RawTranscript:
        blocks = re.split(r"\r?\n\r?\n+", raw.strip())
        utterances: list[RawUtterance] = []

        for block in blocks:
            lines = [ln for ln in block.splitlines() if ln.strip()]
            if not lines:
                continue
            if _INDEX_RE.match(lines[0].strip()):
                lines = lines[1:]
            if not lines:
                continue

            m = _TIMESTAMP_RE.search(lines[0])
            if not m:
                continue
            start_ms = _ts_to_ms(m.group(1), m.group(2), m.group(3), m.group(4))
            end_ms = _ts_to_ms(m.group(5), m.group(6), m.group(7), m.group(8))

            text_lines = lines[1:]
            if not text_lines:
                continue
            text = _TAG_RE.sub("", " ".join(text_lines)).strip()
            if not text:
                continue

            speaker_label: str | None = None
            prefix_match = _SPEAKER_PREFIX_RE.match(text)
            if prefix_match:
                speaker_label = prefix_match.group(1).strip()
                text = prefix_match.group(2).strip()

            utterances.append(
                RawUtterance(
                    speaker_label=speaker_label, text=text, start_ms=start_ms, end_ms=end_ms
                )
            )

        if not utterances:
            raise IngestParseError("Timestamps looked like SRT but no valid cues were found")
        return RawTranscript(utterances=utterances)
