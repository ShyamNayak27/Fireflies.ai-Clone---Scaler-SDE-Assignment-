"""Business logic layer. No SQL (that's repositories/), no HTTP (that's routers/)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Comment
from app.repositories import comments as comments_repo
from app.repositories import meetings as meetings_repo
from app.services.meetings import get_meeting_or_404


async def list_comments(session: AsyncSession, *, meeting_id: int) -> list[Comment]:
    await get_meeting_or_404(session, meeting_id)
    return await comments_repo.list_comments_for_meeting(session, meeting_id=meeting_id)


async def add_comment(
    session: AsyncSession, *, segment_id: int, user_id: int, body: str
) -> Comment:
    segment = await meetings_repo.get_segment(session, segment_id=segment_id)
    if segment is None:
        raise NotFoundError("segment", segment_id)
    comment = await comments_repo.create_comment(
        session, segment_id=segment_id, user_id=user_id, body=body
    )
    await session.commit()
    return comment


async def delete_comment(session: AsyncSession, *, comment_id: int) -> int | None:
    """Returns the deleted comment's meeting_id for cache invalidation."""
    comment = await comments_repo.get_comment(session, comment_id=comment_id)
    if comment is None:
        raise NotFoundError("comment", comment_id)
    segment = await meetings_repo.get_segment(session, segment_id=comment.segment_id)
    meeting_id = segment.meeting_id if segment else None
    await comments_repo.delete_comment(session, comment=comment)
    await session.commit()
    return meeting_id
