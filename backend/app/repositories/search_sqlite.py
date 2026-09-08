"""FTS5-backed search (SQLite). Implements the SearchBackend seam from
docs/ARCHITECTURE.md §7.3 — swap this module for a Postgres/OpenSearch
implementation behind the same function signatures if SQLite is ever outgrown."""

from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_FTS_SPECIAL = re.compile(r'["*^:()]')


def _sanitize_fts_query(raw: str) -> str:
    """Escape user input into a safe FTS5 MATCH query. Wrapping the whole term in
    double quotes with internal quotes escaped turns it into a phrase query, so a
    stray `*` or `:` from user input can never produce an FTS5 syntax error."""
    cleaned = raw.strip().replace('"', '""')
    if not cleaned:
        return '""'
    return f'"{cleaned}"'


async def search_global(
    session: AsyncSession, *, owner_id: int, query: str, limit: int = 20
) -> list[dict]:
    safe_query = _sanitize_fts_query(query)
    rows = (
        (
            await session.execute(
                text(
                    """
                SELECT m.id AS meeting_id, m.title AS meeting_title,
                       s.id AS segment_id, s.start_ms,
                       p.name AS speaker_name,
                       snippet(segments_fts, 0, '<mark>', '</mark>', '…', 12) AS snippet,
                       bm25(segments_fts) AS rank
                FROM segments_fts
                JOIN transcript_segments s ON s.id = segments_fts.rowid
                JOIN meetings m ON m.id = s.meeting_id
                LEFT JOIN participants p ON p.id = s.speaker_id
                WHERE segments_fts MATCH :q AND m.owner_id = :owner_id
                ORDER BY rank
                LIMIT :limit
                """
                ),
                {"q": safe_query, "owner_id": owner_id, "limit": limit},
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


async def search_within_meeting(
    session: AsyncSession, *, meeting_id: int, query: str
) -> list[dict]:
    safe_query = _sanitize_fts_query(query)
    rows = (
        (
            await session.execute(
                text(
                    """
                SELECT s.id AS segment_id, s.start_ms,
                       snippet(segments_fts, 0, '<mark>', '</mark>', '…', 12) AS snippet
                FROM segments_fts
                JOIN transcript_segments s ON s.id = segments_fts.rowid
                WHERE segments_fts MATCH :q AND s.meeting_id = :meeting_id
                ORDER BY bm25(segments_fts)
                """
                ),
                {"q": safe_query, "meeting_id": meeting_id},
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


async def search_within_meeting_any(
    session: AsyncSession, *, meeting_id: int, keywords: list[str], limit: int = 20
) -> list[dict]:
    """OR-of-keywords retrieval for RAG (docs/ARCHITECTURE.md §9.2) — deliberately
    NOT `search_within_meeting`, which wraps its whole input as one exact phrase
    (right for a search box matching literal text, wrong for "does any of these
    question-derived keywords appear anywhere" — caught live: a natural-language
    question phrase-wrapped like that matches nothing). Bare, uppercase-`OR`-joined
    FTS5 terms are still safe here because every keyword comes from
    `app.ai.rag.extract_keywords`'s own regex extraction, never from raw user
    input passed straight through."""
    if not keywords:
        return []
    match_query = " OR ".join(keywords)
    rows = (
        (
            await session.execute(
                text(
                    """
                SELECT s.id AS segment_id, s.start_ms,
                       snippet(segments_fts, 0, '<mark>', '</mark>', '…', 12) AS snippet,
                       bm25(segments_fts) AS rank
                FROM segments_fts
                JOIN transcript_segments s ON s.id = segments_fts.rowid
                WHERE segments_fts MATCH :q AND s.meeting_id = :meeting_id
                ORDER BY rank
                LIMIT :limit
                """
                ),
                {"q": match_query, "meeting_id": meeting_id, "limit": limit},
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]
