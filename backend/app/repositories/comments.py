"""SQL only — see the layering rule in docs/ARCHITECTURE.md §6.1."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comment, TranscriptSegment


async def list_comments_for_meeting(session: AsyncSession, *, meeting_id: int) -> list[Comment]:
    stmt = (
        select(Comment)
        .join(TranscriptSegment, TranscriptSegment.id == Comment.segment_id)
        .where(TranscriptSegment.meeting_id == meeting_id)
        .order_by(Comment.created_at)
    )
    return list((await session.execute(stmt)).scalars().all())


async def create_comment(
    session: AsyncSession, *, segment_id: int, user_id: int, body: str
) -> Comment:
    comment = Comment(segment_id=segment_id, user_id=user_id, body=body)
    session.add(comment)
    await session.flush()
    return comment


async def get_comment(session: AsyncSession, *, comment_id: int) -> Comment | None:
    return await session.get(Comment, comment_id)


async def delete_comment(session: AsyncSession, *, comment: Comment) -> None:
    await session.delete(comment)
