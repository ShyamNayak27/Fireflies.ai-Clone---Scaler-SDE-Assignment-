"""Map-reduce summarization (docs/ARCHITECTURE.md §9.1). Same Protocol-seam
pattern as `app.ai.transcriber.Transcriber` and `app.ingest.parsers.base.TranscriptParser`:
a small interface, a cheap deterministic implementation that always works, and a
real LLM implementation behind it.

Two implementations, not three. The original design sketch described a third
`SeededSummarizer` for pre-generated fixtures — that's not a distinct code path
here, because the six seed meetings already get their Summary/Chapter/Note rows
written directly by `app/seed/seed.py` at boot, never through this module. A
summarizer that only knows how to reproduce six hardcoded meetings wouldn't
generalize to a freshly-ingested one anyway. So `summarizer_backend: "seeded"`
(the config default) and `"heuristic"` both resolve to `HeuristicSummarizer` —
documented honestly in `get_summarizer` below rather than pretending a third
implementation exists.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.core.config import get_settings

MAX_WINDOW_MS = 10 * 60 * 1000  # ~10-minute map chunks, per docs/ARCHITECTURE.md §9.1
MIN_WINDOW_MS = 90 * 1000  # a 3-minute demo meeting still deserves more than one chapter
STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "so",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "that",
    "this",
    "it",
    "we",
    "you",
    "i",
    "they",
    "he",
    "she",
    "at",
    "as",
    "by",
    "from",
    "about",
    "just",
    "like",
    "can",
    "will",
    "would",
    "should",
    "could",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "not",
    "if",
    "what",
    "which",
    "who",
    "when",
    "where",
    "how",
    "there",
    "here",
    "our",
    "your",
    "my",
    "us",
    "them",
    "also",
    "then",
    "than",
    "some",
    "all",
    "one",
    "get",
    "got",
    "going",
    "know",
    "think",
    "let",
    "lets",
    "yeah",
    "okay",
    "ok",
    "gonna",
    "wanna",
    "really",
    "actually",
    "right",
    "well",
    "thing",
    "things",
    "still",
    "much",
    "even",
    "way",
    "little",
    "bit",
    "sure",
    "maybe",
    "look",
    "looking",
    "make",
    "making",
    "made",
    "want",
    "wanted",
    "need",
    "needs",
    "needed",
    "come",
    "coming",
    "guys",
}
_ACTION_PATTERNS = [
    re.compile(r"\bI['’]ll\b", re.IGNORECASE),
    re.compile(r"\bI will\b", re.IGNORECASE),
    re.compile(r"\bcan you\b", re.IGNORECASE),
    re.compile(r"\bcould you\b", re.IGNORECASE),
    re.compile(r"\blet['’]s\b.*\b(by|before)\b", re.IGNORECASE),
    re.compile(r"\bneed(?:s)? to\b", re.IGNORECASE),
    re.compile(r"\baction item\b", re.IGNORECASE),
    re.compile(r"\bfollow(?:\s|-)?up\b", re.IGNORECASE),
]
_DUE_DATE_RE = re.compile(
    r"\bby (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"tomorrow|end of (?:day|week)|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2})\b",
    re.IGNORECASE,
)


@dataclass
class SegmentInput:
    """Decoupled from the ORM on purpose — the summarizer never touches a
    Session, matching the layering rule in docs/ARCHITECTURE.md §6.1."""

    id: int
    idx: int
    start_ms: int
    end_ms: int
    speaker_name: str | None
    text: str


@dataclass
class NoteDraft:
    text: str
    start_ms: int | None


@dataclass
class ChapterDraft:
    title: str
    start_ms: int
    end_ms: int
    notes: list[NoteDraft] = field(default_factory=list)


@dataclass
class ActionItemDraft:
    text: str
    due_date: str | None
    source_segment_id: int | None


@dataclass
class SummaryDraft:
    overview: str
    model: str | None  # None = heuristic (no LLM was involved), matching Summary.model
    chapters: list[ChapterDraft] = field(default_factory=list)
    action_items: list[ActionItemDraft] = field(default_factory=list)


class SummarizerUnavailable(Exception):
    pass


def _adaptive_window_ms(segments: list[SegmentInput]) -> int:
    """A fixed 10-minute window (the docs' original number, tuned for a
    real-length meeting) produces exactly one chapter for the several-minute
    demo meetings this app mostly sees — caught during live testing, where a
    3.5-minute standup came back as a single undifferentiated chapter. Aim for
    roughly 3 chapters instead, floored at 90s (so a short meeting isn't
    sliced into one-sentence "chapters") and capped at the original 10-minute
    ceiling (so a genuinely long meeting doesn't get an unreasonably wide window)."""
    total_ms = segments[-1].end_ms - segments[0].start_ms
    return max(MIN_WINDOW_MS, min(MAX_WINDOW_MS, total_ms // 3 or MIN_WINDOW_MS))


def chunk_by_time(
    segments: list[SegmentInput], window_ms: int | None = None
) -> list[list[SegmentInput]]:
    """Chunk boundaries fall on segment (i.e. speaker-turn) boundaries, never
    mid-utterance — a chunk starts fresh once the running window is exceeded."""
    if not segments:
        return []
    window_ms = window_ms if window_ms is not None else _adaptive_window_ms(segments)
    chunks: list[list[SegmentInput]] = []
    current: list[SegmentInput] = [segments[0]]
    window_start = segments[0].start_ms
    for seg in segments[1:]:
        if seg.start_ms - window_start >= window_ms:
            chunks.append(current)
            current = [seg]
            window_start = seg.start_ms
        else:
            current.append(seg)
    chunks.append(current)
    return chunks


def _mmss(ms: int) -> str:
    total_s = ms // 1000
    return f"{total_s // 60:02d}:{total_s % 60:02d}"


class HeuristicSummarizer:
    """No API key required. Deterministic and fast — the same transcript
    always produces the same summary, which also makes it trivially testable."""

    async def summarize(self, segments: list[SegmentInput], meeting_title: str) -> SummaryDraft:
        chunks = chunk_by_time(segments)
        chapters = [self._chapter_for(chunk) for chunk in chunks]
        overview = self._overview_for(meeting_title, chapters, segments)
        action_items = self._action_items_for(segments)
        return SummaryDraft(
            overview=overview, model=None, chapters=chapters, action_items=action_items
        )

    def _chapter_for(self, chunk: list[SegmentInput]) -> ChapterDraft:
        title = self._keyword_title(chunk)
        notes = self._notes_for(chunk)
        return ChapterDraft(
            title=title, start_ms=chunk[0].start_ms, end_ms=chunk[-1].end_ms, notes=notes
        )

    def _keyword_title(self, chunk: list[SegmentInput]) -> str:
        counts: dict[str, int] = {}
        for seg in chunk:
            for raw_word in re.findall(r"[A-Za-z][A-Za-z'’-]{2,}", seg.text.lower()):
                # Strip a trailing clitic ("let's" -> "let", "that's" -> "that")
                # rather than hardcoding every contraction into the stopword
                # list — a bare apostrophe form would otherwise slip through
                # stopword filtering and win a chapter title on frequency alone
                # (caught live: "Let's & Agreed" from a 3-sentence closing chunk).
                word = re.split(r"['’]", raw_word)[0]
                if len(word) < 3 or word in STOPWORDS:
                    continue
                counts[word] = counts.get(word, 0) + 1
        if not counts:
            return f"Discussion ({_mmss(chunk[0].start_ms)}–{_mmss(chunk[-1].end_ms)})"
        top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:2]
        return " & ".join(word.capitalize() for word, _ in top)

    def _notes_for(self, chunk: list[SegmentInput], max_notes: int = 3) -> list[NoteDraft]:
        # Pick the longest utterances as a cheap proxy for "most substantive" —
        # a one-word acknowledgement is rarely the point of a chapter, a
        # multi-sentence turn usually is.
        ranked = sorted(chunk, key=lambda s: -len(s.text))[:max_notes]
        ranked.sort(key=lambda s: s.start_ms)
        return [
            NoteDraft(
                text=seg.text if len(seg.text) <= 160 else seg.text[:157] + "…",
                start_ms=seg.start_ms,
            )
            for seg in ranked
        ]

    def _overview_for(
        self, meeting_title: str, chapters: list[ChapterDraft], segments: list[SegmentInput]
    ) -> str:
        speakers = sorted({s.speaker_name for s in segments if s.speaker_name})
        titles = [c.title for c in chapters]
        if len(titles) <= 1:
            topics = titles[0] if titles else ""
        elif len(titles) == 2:
            topics = f"{titles[0]} and {titles[1]}"
        else:
            topics = ", ".join(titles[:-1]) + f", and {titles[-1]}"
        who = f" with {', '.join(speakers)}" if speakers else ""
        return (
            f'"{meeting_title}"{who} covered: {topics}.'
            if topics
            else f'"{meeting_title}" — no substantive content was extracted.'
        )

    def _action_items_for(self, segments: list[SegmentInput]) -> list[ActionItemDraft]:
        items: list[ActionItemDraft] = []
        seen: set[str] = set()
        for seg in segments:
            if not any(p.search(seg.text) for p in _ACTION_PATTERNS):
                continue
            key = seg.text.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            due_match = _DUE_DATE_RE.search(seg.text)
            items.append(
                ActionItemDraft(
                    text=seg.text if len(seg.text) <= 200 else seg.text[:197] + "…",
                    due_date=due_match.group(1) if due_match else None,
                    source_segment_id=seg.id,
                )
            )
        return items


class LLMSummarizer:
    """Real map-reduce over the OpenAI chat completions API. Map: one call per
    ~10-minute chunk, asking for a chapter title, a short mini-summary, cited
    notes, and cited candidate action items — citations are numbered indices
    into that chunk's own segment list, resolved back to real start_ms/segment
    ids in Python rather than trusted from the model. Reduce: one further call
    over the concatenated mini-summaries to produce the final overview.
    Action-item de-duplication across chunks is done in Python (case-insensitive
    text match) rather than a second LLM pass — good enough for the volume of
    action items a single meeting produces, and it avoids re-resolving
    citations through yet another indirection.
    """

    def __init__(self, api_key: str, model: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def summarize(self, segments: list[SegmentInput], meeting_title: str) -> SummaryDraft:
        chunks = chunk_by_time(segments)
        chapters: list[ChapterDraft] = []
        action_items: list[ActionItemDraft] = []
        mini_summaries: list[str] = []
        seen_action_keys: set[str] = set()

        for chunk in chunks:
            mapped = await self._map_chunk(chunk)
            chapters.append(
                ChapterDraft(
                    title=mapped["chapter_title"],
                    start_ms=chunk[0].start_ms,
                    end_ms=chunk[-1].end_ms,
                    notes=[
                        NoteDraft(text=n["text"], start_ms=self._resolve_cite(chunk, n.get("cite")))
                        for n in mapped["notes"]
                    ],
                )
            )
            mini_summaries.append(mapped["mini_summary"])
            for a in mapped["action_items"]:
                key = a["text"].strip().lower()
                if key in seen_action_keys:
                    continue
                seen_action_keys.add(key)
                seg = self._segment_for_cite(chunk, a.get("cite"))
                action_items.append(
                    ActionItemDraft(
                        text=a["text"],
                        due_date=a.get("due_date"),
                        source_segment_id=seg.id if seg else None,
                    )
                )

        overview = await self._reduce_overview(meeting_title, mini_summaries)
        return SummaryDraft(
            overview=overview, model=self._model, chapters=chapters, action_items=action_items
        )

    def _resolve_cite(self, chunk: list[SegmentInput], cite: int | None) -> int | None:
        seg = self._segment_for_cite(chunk, cite)
        return seg.start_ms if seg else None

    def _segment_for_cite(self, chunk: list[SegmentInput], cite: int | None) -> SegmentInput | None:
        if cite is None or not (0 <= cite < len(chunk)):
            return None
        return chunk[cite]

    async def _map_chunk(self, chunk: list[SegmentInput]) -> dict:
        context = "\n".join(
            f"[{i}] {_mmss(seg.start_ms)} {seg.speaker_name or 'Unknown'}: {seg.text}"
            for i, seg in enumerate(chunk)
        )
        prompt = (
            "You are summarizing one segment of a meeting transcript. Numbered lines are "
            'the source; cite them by their number in the "cite" field of anything you '
            "extract, never invent a number outside the given range.\n\n"
            f"TRANSCRIPT SEGMENT:\n{context}\n\n"
            "Respond with strict JSON: "
            '{"chapter_title": "2-4 word title", "mini_summary": "1-2 sentences", '
            '"notes": [{"text": "...", "cite": <int>}], '
            '"action_items": [{"text": "...", "due_date": "<string or null>", "cite": <int>}]}'
        )
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return json.loads(resp.choices[0].message.content or "{}")

    async def _reduce_overview(self, meeting_title: str, mini_summaries: list[str]) -> str:
        joined = "\n".join(f"- {s}" for s in mini_summaries)
        prompt = (
            f'Write one short paragraph (2-4 sentences) summarizing the meeting "{meeting_title}" '
            f"given these section summaries, in chronological order:\n{joined}\n\n"
            'Respond with strict JSON: {"overview": "..."}'
        )
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        return data.get("overview") or " ".join(mini_summaries)


def get_summarizer() -> HeuristicSummarizer | LLMSummarizer:
    settings = get_settings()
    if settings.summarizer_backend == "llm" and settings.openai_api_key:
        return LLMSummarizer(settings.openai_api_key, settings.llm_model)
    return HeuristicSummarizer()
