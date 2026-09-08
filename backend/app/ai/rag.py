"""RAG "ask this meeting" chat (docs/ARCHITECTURE.md §9.2). Pure answer-generation
logic only — no Session, no SQL, matching the layering rule in §6.1. Retrieval
(the FTS5/tsvector query, neighbor expansion, window merging) lives in
`app/services/ask.py`, which hands this module the already-retrieved context.

Two implementations, same Protocol-seam pattern as `app.ai.transcriber` and
`app.ai.summarizer`:
`ExtractiveAnswerer` (always available — no synthesis, just the retrieved
excerpts themselves, clearly labeled as such) and `LLMAnswerer` (a real
synthesized, cited answer). Unlike the summarizer, there is no "heuristic
synthesis" middle ground worth building — meaningfully answering a question
from scattered excerpts requires an LLM; anything else is honestly just search
results, so that's what the fallback presents itself as.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.ai.summarizer import STOPWORDS
from app.core.config import get_settings

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")


def extract_keywords(question: str, max_keywords: int = 6) -> list[str]:
    """Turns a natural-language question into bare content words for
    OR-based FTS retrieval (`search_within_meeting_any`). Feeding the whole
    question through the existing phrase-search seam was the first thing
    tried here — it matched nothing, because that seam wraps its entire input
    as one exact phrase (right for a literal search box, wrong for "does any
    of these words appear anywhere"). Caught live, fixed by extracting
    keywords instead of changing what the search box itself does."""
    seen: list[str] = []
    for raw in _WORD_RE.findall(question.lower()):
        word = re.split(r"['’]", raw)[0]
        if len(word) < 3 or word in STOPWORDS or word in seen:
            continue
        seen.append(word)
        if len(seen) >= max_keywords:
            break
    return seen


@dataclass
class ContextSegment:
    """One retrieved-and-expanded transcript segment, numbered for citation —
    the same numbered-context pattern `app.ai.summarizer.LLMSummarizer` uses."""

    number: int
    segment_id: int
    start_ms: int
    speaker_name: str | None
    text: str


@dataclass
class Citation:
    number: int
    segment_id: int
    start_ms: int


@dataclass
class AskResult:
    answer: str
    citations: list[Citation]
    model: str | None  # None = extractive fallback, no LLM involved


class Answerer(Protocol):
    async def answer(self, question: str, context: list[ContextSegment]) -> AskResult: ...


def _mmss(ms: int) -> str:
    total_s = ms // 1000
    return f"{total_s // 60:02d}:{total_s % 60:02d}"


class ExtractiveAnswerer:
    """No API key required. Returns the retrieved excerpts themselves rather
    than a synthesized answer — honest about not having actually answered the
    question, since that's a real distinction a user should be able to see."""

    async def answer(self, question: str, context: list[ContextSegment]) -> AskResult:
        if not context:
            return AskResult(
                answer="Nothing in this meeting's transcript matches that question.",
                citations=[],
                model=None,
            )
        lines = [
            f"[{c.number}] {_mmss(c.start_ms)} {c.speaker_name or 'Unknown'}: {c.text}"
            for c in context
        ]
        answer = (
            "No LLM is configured, so here are the most relevant excerpts instead of a "
            "synthesized answer:\n" + "\n".join(lines)
        )
        citations = [Citation(c.number, c.segment_id, c.start_ms) for c in context]
        return AskResult(answer=answer, citations=citations, model=None)


class LLMAnswerer:
    """Requires the numbered excerpts to already be assembled by the caller —
    this class only prompts, parses, and resolves citation numbers back to the
    segments the caller gave it."""

    def __init__(self, api_key: str, model: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def answer(self, question: str, context: list[ContextSegment]) -> AskResult:
        if not context:
            return AskResult(
                answer="Nothing in this meeting's transcript matches that question.",
                citations=[],
                model=None,
            )
        context_text = "\n".join(
            f"[{c.number}] {_mmss(c.start_ms)} {c.speaker_name or 'Unknown'}: {c.text}"
            for c in context
        )
        prompt = (
            "Answer the question using ONLY the numbered transcript excerpts below. "
            "Cite every claim with the excerpt number(s) it came from, inline like [2]. "
            "If the excerpts don't contain the answer, say so plainly rather than guessing.\n\n"
            f"EXCERPTS:\n{context_text}\n\nQUESTION: {question}"
        )
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        answer_text = resp.choices[0].message.content or ""
        cited_numbers = {c.number for c in context if f"[{c.number}]" in answer_text}
        citations = [
            Citation(c.number, c.segment_id, c.start_ms) for c in context if c.number in cited_numbers
        ] or [Citation(c.number, c.segment_id, c.start_ms) for c in context]
        return AskResult(answer=answer_text, citations=citations, model=self._model)


def get_answerer() -> ExtractiveAnswerer | LLMAnswerer:
    settings = get_settings()
    if settings.summarizer_backend == "llm" and settings.openai_api_key:
        return LLMAnswerer(settings.openai_api_key, settings.llm_model)
    return ExtractiveAnswerer()
