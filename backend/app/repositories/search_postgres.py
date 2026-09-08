"""Postgres tsvector-backed search. Implements the same SearchBackend seam as
search_sqlite.py — see docs/ARCHITECTURE.md §7.3 / ADR-006.

`websearch_to_tsquery` is used rather than `plainto_tsquery` or `to_tsquery` because
it accepts raw user input safely (quoted phrases, `-exclude`, `OR`) without ever
raising a syntax error on stray punctuation — the same safety property
_sanitize_fts_query gives the SQLite implementation, for free, from Postgres itself.
Verified against a live Supabase Postgres instance during development: the
generated `search_vector` column, the GIN index, ts_rank ordering, and ts_headline
highlighting all confirmed working on real inserted rows.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def search_global(
    session: AsyncSession, *, owner_id: int, query: str, limit: int = 20
) -> list[dict]:
    rows = (
        (
            await session.execute(
                text(
                    """
                SELECT m.id AS meeting_id, m.title AS meeting_title,
                       s.id AS segment_id, s.start_ms,
                       p.name AS speaker_name,
                       ts_headline(
                           'english', s.text, websearch_to_tsquery('english', :q),
                           'StartSel=<mark>, StopSel=</mark>, MaxFragments=1, MaxWords=20'
                       ) AS snippet,
                       ts_rank(s.search_vector, websearch_to_tsquery('english', :q)) AS rank
                FROM transcript_segments s
                JOIN meetings m ON m.id = s.meeting_id
                LEFT JOIN participants p ON p.id = s.speaker_id
                WHERE s.search_vector @@ websearch_to_tsquery('english', :q)
                  AND m.owner_id = :owner_id
                ORDER BY rank DESC
                LIMIT :limit
                """
                ),
                {"q": query, "owner_id": owner_id, "limit": limit},
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


async def search_within_meeting(
    session: AsyncSession, *, meeting_id: int, query: str
) -> list[dict]:
    rows = (
        (
            await session.execute(
                text(
                    """
                SELECT s.id AS segment_id, s.start_ms,
                       ts_headline(
                           'english', s.text, websearch_to_tsquery('english', :q),
                           'StartSel=<mark>, StopSel=</mark>, MaxFragments=1, MaxWords=20'
                       ) AS snippet
                FROM transcript_segments s
                WHERE s.search_vector @@ websearch_to_tsquery('english', :q)
                  AND s.meeting_id = :meeting_id
                ORDER BY ts_rank(s.search_vector, websearch_to_tsquery('english', :q)) DESC
                """
                ),
                {"q": query, "meeting_id": meeting_id},
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


async def search_within_meeting_any(
    session: AsyncSession, *, meeting_id: int, keywords: list[str], limit: int = 20
) -> list[dict]:
    """OR-of-keywords retrieval for RAG — see the sqlite implementation's
    docstring for why this is a separate function from `search_within_meeting`.
    `websearch_to_tsquery` treats a bare ` or ` between terms as a real OR
    operator (the same "safe against arbitrary punctuation" property that lets
    `search_global` pass raw user input straight through), and every keyword
    here is our own regex-extracted token, not raw user input."""
    if not keywords:
        return []
    match_query = " or ".join(keywords)
    rows = (
        (
            await session.execute(
                text(
                    """
                SELECT s.id AS segment_id, s.start_ms,
                       ts_headline(
                           'english', s.text, websearch_to_tsquery('english', :q),
                           'StartSel=<mark>, StopSel=</mark>, MaxFragments=1, MaxWords=20'
                       ) AS snippet,
                       ts_rank(s.search_vector, websearch_to_tsquery('english', :q)) AS rank
                FROM transcript_segments s
                WHERE s.search_vector @@ websearch_to_tsquery('english', :q)
                  AND s.meeting_id = :meeting_id
                ORDER BY rank DESC
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
