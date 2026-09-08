"""Dispatches to the SQLite (FTS5) or Postgres (tsvector) SearchBackend implementation
based on the session's actual bound dialect — never a config flag that could drift
from the real database, and never an import a caller has to know to change. See
docs/ARCHITECTURE.md §7.3 / ADR-006.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import search_postgres, search_sqlite


def _dialect_name(session: AsyncSession) -> str:
    return session.bind.dialect.name  # type: ignore[union-attr]


async def search_global(
    session: AsyncSession, *, owner_id: int, query: str, limit: int = 20
) -> list[dict]:
    backend = search_postgres if _dialect_name(session) == "postgresql" else search_sqlite
    return await backend.search_global(session, owner_id=owner_id, query=query, limit=limit)


async def search_within_meeting(
    session: AsyncSession, *, meeting_id: int, query: str
) -> list[dict]:
    backend = search_postgres if _dialect_name(session) == "postgresql" else search_sqlite
    return await backend.search_within_meeting(session, meeting_id=meeting_id, query=query)


async def search_within_meeting_any(
    session: AsyncSession, *, meeting_id: int, keywords: list[str], limit: int = 20
) -> list[dict]:
    backend = search_postgres if _dialect_name(session) == "postgresql" else search_sqlite
    return await backend.search_within_meeting_any(
        session, meeting_id=meeting_id, keywords=keywords, limit=limit
    )
