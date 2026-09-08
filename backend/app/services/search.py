from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import search as search_repo
from app.schemas.meeting import SearchHit


async def global_search(session: AsyncSession, *, owner_id: int, query: str) -> list[SearchHit]:
    if not query.strip():
        return []
    rows = await search_repo.search_global(session, owner_id=owner_id, query=query)
    return [
        SearchHit(
            meeting_id=r["meeting_id"],
            meeting_title=r["meeting_title"],
            segment_id=r["segment_id"],
            start_ms=r["start_ms"],
            speaker_name=r["speaker_name"],
            snippet=r["snippet"],
        )
        for r in rows
    ]
