"""The SearchBackend seam (docs/ARCHITECTURE.md §7.3). Two real implementations exist
today — search_sqlite.py (FTS5, local dev) and search_postgres.py (tsvector, the
deployed environment) — selected at call time by dialect, never by a hardcoded
import, so the same service code runs against either (docs/ARCHITECTURE.md ADR-006).
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class SearchBackend(Protocol):
    async def search_global(
        self, session: AsyncSession, *, owner_id: int, query: str, limit: int = 20
    ) -> list[dict]: ...

    async def search_within_meeting(
        self, session: AsyncSession, *, meeting_id: int, query: str
    ) -> list[dict]: ...

    async def search_within_meeting_any(
        self, session: AsyncSession, *, meeting_id: int, keywords: list[str], limit: int = 20
    ) -> list[dict]: ...
