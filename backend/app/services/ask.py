"""Retrieval for "ask this meeting" (docs/ARCHITECTURE.md §9.2). All the
SQL/session-touching work lives here; `app/ai/rag.py` only ever sees a plain
list of `ContextSegment`s and never a Session, per the layering rule in §6.1.

Retrieval reuses the FTS5/tsvector index search was already built on
(docs/ARCHITECTURE.md §7.3) — the same index doubles as the retriever, so this
feature costs almost nothing beyond what already existed. It goes through
`search_within_meeting_any` (keyword-OR), not `search_within_meeting`
(exact-phrase) — verified live that the latter matches nothing for a natural
question, since it phrase-wraps the whole input; see `app.ai.rag.extract_keywords`.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag import AskResult, ContextSegment, extract_keywords, get_answerer
from app.repositories import meetings as meetings_repo
from app.repositories import search as search_repo
from app.services.meetings import get_meeting_or_404

NEIGHBOR_WINDOW = 2  # ± segments around each hit, per docs/ARCHITECTURE.md §9.2
TOP_K = 6


async def ask_meeting(session: AsyncSession, *, meeting_id: int, question: str) -> AskResult:
    # Router enforces min_length=1 on `question`, so an empty string never
    # reaches here — no separate validation needed on this side.
    await get_meeting_or_404(session, meeting_id)

    keywords = extract_keywords(question)
    hits = (
        await search_repo.search_within_meeting_any(
            session, meeting_id=meeting_id, keywords=keywords, limit=TOP_K
        )
        if keywords
        else []
    )
    if not hits:
        return await get_answerer().answer(question, [])

    all_segments = await meetings_repo.get_all_segments(session, meeting_id=meeting_id)
    by_id = {s.id: i for i, s in enumerate(all_segments)}  # segment id -> position in idx order

    # Expand each hit ±NEIGHBOR_WINDOW and merge overlapping windows, so a quote
    # isn't decapitated and two nearby hits don't duplicate their shared context.
    top_hit_positions = [by_id[h["segment_id"]] for h in hits[:TOP_K] if h["segment_id"] in by_id]
    covered: set[int] = set()
    for pos in top_hit_positions:
        lo, hi = max(0, pos - NEIGHBOR_WINDOW), min(len(all_segments) - 1, pos + NEIGHBOR_WINDOW)
        covered.update(range(lo, hi + 1))

    ordered_positions = sorted(covered)
    context = [
        ContextSegment(
            number=i + 1,
            segment_id=(seg := all_segments[pos]).id,
            start_ms=seg.start_ms,
            speaker_name=seg.speaker.name if seg.speaker else None,
            text=seg.text,
        )
        for i, pos in enumerate(ordered_positions)
    ]

    return await get_answerer().answer(question, context)
