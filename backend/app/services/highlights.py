"""Business logic layer. No SQL (that's repositories/), no HTTP (that's routers/)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Highlight
from app.repositories import highlights as highlights_repo
from app.repositories import meetings as meetings_repo
from app.services.meetings import get_meeting_or_404


async def list_highlights(session: AsyncSession, *, meeting_id: int) -> list[Highlight]:
    await get_meeting_or_404(session, meeting_id)
    return await highlights_repo.list_highlights_for_meeting(session, meeting_id=meeting_id)


async def add_highlight(
    session: AsyncSession,
    *,
    segment_id: int,
    user_id: int,
    color: str,
    start_offset: int,
    end_offset: int,
) -> Highlight:
    segment = await meetings_repo.get_segment(session, segment_id=segment_id)
    if segment is None:
        raise NotFoundError("segment", segment_id)
    end_offset = min(end_offset, len(segment.text))  # clamp rather than 422 on a stale client-side selection
    highlight = await highlights_repo.create_highlight(
        session,
        segment_id=segment_id,
        user_id=user_id,
        color=color,
        start_offset=start_offset,
        end_offset=end_offset,
    )
    await session.commit()
    return highlight


async def delete_highlight(session: AsyncSession, *, highlight_id: int) -> int | None:
    highlight = await highlights_repo.get_highlight(session, highlight_id=highlight_id)
    if highlight is None:
        raise NotFoundError("highlight", highlight_id)
    segment = await meetings_repo.get_segment(session, segment_id=highlight.segment_id)
    meeting_id = segment.meeting_id if segment else None
    await highlights_repo.delete_highlight(session, highlight=highlight)
    await session.commit()
    return meeting_id
