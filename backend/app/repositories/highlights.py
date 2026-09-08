"""SQL only — see the layering rule in docs/ARCHITECTURE.md §6.1."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Highlight, TranscriptSegment


async def list_highlights_for_meeting(session: AsyncSession, *, meeting_id: int) -> list[Highlight]:
    stmt = (
        select(Highlight)
        .join(TranscriptSegment, TranscriptSegment.id == Highlight.segment_id)
        .where(TranscriptSegment.meeting_id == meeting_id)
        .order_by(Highlight.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def create_highlight(
    session: AsyncSession,
    *,
    segment_id: int,
    user_id: int,
    color: str,
    start_offset: int,
    end_offset: int,
) -> Highlight:
    highlight = Highlight(
        segment_id=segment_id,
        user_id=user_id,
        color=color,
        start_offset=start_offset,
        end_offset=end_offset,
    )
    session.add(highlight)
    await session.flush()
    return highlight


async def get_highlight(session: AsyncSession, *, highlight_id: int) -> Highlight | None:
    return await session.get(Highlight, highlight_id)


async def delete_highlight(session: AsyncSession, *, highlight: Highlight) -> None:
    await session.delete(highlight)
