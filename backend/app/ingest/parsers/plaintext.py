"""Two plain-text parsers, in increasing order of "how little structure do we
require":

`OtterTextParser` matches Otter.ai's actual copy/paste export shape — a
"Speaker Name  H:MM" or "Speaker Name  MM:SS" cue line on its own, followed by
a blank line, followed by that turn's text:

    Alex Kim  0:00
    Hey everyone, thanks for joining.

    Priya Shah  0:15
    No problem, glad to be here.

`PlainTextFallbackParser` is the last-resort registry entry (docs/ARCHITECTURE.md
§5.1): no timing, and speakers only if every non-blank line matches `Name: text`
consistently — otherwise the whole paste becomes one unattributed utterance
rather than guessing wrong. It always sniffs a small positive score so the
registry has somewhere to land rather than rejecting an upload outright.
"""
from __future__ import annotations

import re

from app.ingest.types import RawTranscript, RawUtterance

_OTTER_CUE_RE = re.compile(r"^(?P<name>[A-Za-z][\w .'-]{0,60})\s{2,}(?P<ts>\d{1,2}:\d{2}(?::\d{2})?)\s*$")
_SPEAKER_LINE_RE = re.compile(r"^([A-Za-z][\w .'-]{0,60}):\s+(.+)$")


def _mmss_to_ms(ts: str) -> int:
    parts = [int(p) for p in ts.split(":")]
    if len(parts) == 2:
        m, s = parts
        h = 0
    else:
        h, m, s = parts
    return (h * 3600 + m * 60 + s) * 1000


class OtterTextParser:
    name = "otter_text"

    def sniff(self, raw: str, filename: str) -> float:
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        if len(lines) < 2:
            return 0.0
        cue_lines = sum(1 for ln in lines if _OTTER_CUE_RE.match(ln))
        if cue_lines == 0:
            return 0.0
        # Require a meaningful fraction of non-blank lines to look like cues —
        # a transcript with one stray "Name  1:23"-shaped line isn't Otter.
        ratio = cue_lines / len(lines)
        return min(0.85, 0.3 + ratio)

    def parse(self, raw: str) -> RawTranscript:
        utterances: list[RawUtterance] = []
        current_speaker: str | None = None
        current_ms: int | None = None
        buffer: list[str] = []

        def flush() -> None:
            if buffer:
                text = " ".join(buffer).strip()
                if text:
                    utterances.append(
                        RawUtterance(
                            speaker_label=current_speaker,
                            text=text,
                            start_ms=current_ms,
                            end_ms=None,
                        )
                    )
            buffer.clear()

        for line in raw.splitlines():
            stripped = line.strip()
            cue = _OTTER_CUE_RE.match(stripped) if stripped else None
            if cue:
                flush()
                current_speaker = cue.group("name").strip()
                current_ms = _mmss_to_ms(cue.group("ts"))
            elif stripped:
                buffer.append(stripped)
        flush()

        return RawTranscript(utterances=utterances)


class PlainTextFallbackParser:
    """Registry order matters (docs/ARCHITECTURE.md §5.1): this is registered
    last and always wins by default when nothing more specific matches."""

    name = "plain_text"

    def sniff(self, raw: str, filename: str) -> float:
        return 0.1 if raw.strip() else 0.0

    def parse(self, raw: str) -> RawTranscript:
        paragraphs = [p.strip() for p in re.split(r"\r?\n\s*\r?\n", raw.strip()) if p.strip()]
        if not paragraphs:
            paragraphs = [raw.strip()]

        # Consistent "Name: text" on every paragraph's first line → attribute it.
        # Otherwise treat every paragraph as one unattributed utterance rather
        # than guessing speakers from noise.
        matches = [_SPEAKER_LINE_RE.match(p.splitlines()[0]) for p in paragraphs]
        if paragraphs and all(matches):
            utterances = [
                RawUtterance(
                    speaker_label=m.group(1).strip(),  # type: ignore[union-attr]
                    text=" ".join(
                        [m.group(2).strip()] + p.splitlines()[1:]  # type: ignore[union-attr]
                    ).strip(),
                )
                for p, m in zip(paragraphs, matches, strict=True)
            ]
        else:
            utterances = [
                RawUtterance(speaker_label=None, text=" ".join(p.splitlines()).strip())
                for p in paragraphs
            ]

        return RawTranscript(utterances=[u for u in utterances if u.text])
