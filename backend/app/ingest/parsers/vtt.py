"""WebVTT parser. This is also the format Zoom's own "Audio Transcript"
export uses (a WEBVTT file with `<v Speaker Name>` voice tags inside each cue),
so one parser genuinely covers both entries on the original aspirational list —
documented explicitly in docs/ARCHITECTURE.md rather than pretending Zoom got a
dedicated parser it doesn't need.

Cue timestamp line: `00:00:01.500 --> 00:00:04.200` (hours segment optional).
Speaker: either a `<v Name>text</v>` voice tag, or a `Name: text` prefix on the
cue text (Zoom sometimes emits the latter instead of a voice tag).
"""
from __future__ import annotations

import re

from app.ingest.parsers.base import IngestParseError
from app.ingest.types import RawTranscript, RawUtterance

_TIMESTAMP_RE = re.compile(
    r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})"
)
_VOICE_TAG_RE = re.compile(r"^<v\s+([^>]+)>(.*?)(?:</v>)?$", re.DOTALL)
_SPEAKER_PREFIX_RE = re.compile(r"^([A-Za-z][\w .'-]{0,60}):\s+(.+)$", re.DOTALL)
_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")


def _ts_to_ms(h: str | None, m: str, s: str, ms: str) -> int:
    return (int(h or 0) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)


class VttParser:
    name = "vtt"

    def sniff(self, raw: str, filename: str) -> float:
        head = raw.lstrip()[:20].upper()
        score = 0.0
        if head.startswith("WEBVTT"):
            score = 0.95
        elif filename.lower().endswith(".vtt"):
            score = 0.6
        if score and _TIMESTAMP_RE.search(raw) is None:
            score *= 0.3  # says VTT but has no cue timing at all — probably not
        return score

    def parse(self, raw: str) -> RawTranscript:
        blocks = re.split(r"\r?\n\r?\n+", raw.strip())
        utterances: list[RawUtterance] = []

        for block in blocks:
            lines = [ln for ln in block.splitlines() if ln.strip()]
            if not lines or lines[0].strip().upper().startswith("WEBVTT"):
                continue

            ts_line_idx = None
            for i, ln in enumerate(lines[:2]):
                if _TIMESTAMP_RE.search(ln):
                    ts_line_idx = i
                    break
            if ts_line_idx is None:
                continue  # a NOTE/STYLE block or stray cue identifier — skip

            m = _TIMESTAMP_RE.search(lines[ts_line_idx])
            assert m is not None
            start_ms = _ts_to_ms(m.group(1), m.group(2), m.group(3), m.group(4))
            end_ms = _ts_to_ms(m.group(5), m.group(6), m.group(7), m.group(8))

            text_lines = lines[ts_line_idx + 1 :]
            if not text_lines:
                continue
            text = " ".join(text_lines).strip()

            speaker_label: str | None = None
            voice_match = _VOICE_TAG_RE.match(text)
            if voice_match:
                speaker_label = voice_match.group(1).strip()
                text = voice_match.group(2).strip()
            else:
                prefix_match = _SPEAKER_PREFIX_RE.match(text)
                if prefix_match:
                    speaker_label = prefix_match.group(1).strip()
                    text = prefix_match.group(2).strip()

            text = _TAG_RE.sub("", text).strip()
            if not text:
                continue

            utterances.append(
                RawUtterance(
                    speaker_label=speaker_label, text=text, start_ms=start_ms, end_ms=end_ms
                )
            )

        if not utterances:
            raise IngestParseError("WEBVTT header found but no valid cues could be parsed")
        return RawTranscript(utterances=utterances)
