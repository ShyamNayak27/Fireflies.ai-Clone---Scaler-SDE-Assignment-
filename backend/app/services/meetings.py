"""Business logic layer. No SQL (that's repositories/), no HTTP (that's routers/)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Meeting
from app.repositories import meetings as meetings_repo
from app.repositories import tags as tags_repo


async def list_meetings_page(
    session: AsyncSession, *, owner_id: int, cursor: str | None, limit: int, tag: str | None = None
) -> tuple[list[Meeting], str | None]:
    return await meetings_repo.list_meetings(
        session, owner_id=owner_id, cursor=cursor, limit=limit, tag=tag
    )


async def tags_for_meetings(session: AsyncSession, *, meetings: list[Meeting]) -> dict[int, list]:
    return await tags_repo.tags_by_meeting_ids(session, meeting_ids=[m.id for m in meetings])


async def get_meeting_or_404(session: AsyncSession, meeting_id: int) -> Meeting:
    meeting = await meetings_repo.get_meeting(session, meeting_id)
    if meeting is None:
        raise NotFoundError("meeting", meeting_id)
    return meeting


async def get_transcript_page(
    session: AsyncSession, *, meeting_id: int, cursor: str | None, limit: int
):
    # Confirms the meeting exists (and belongs to this owner, once auth is real)
    # before paginating its transcript, so a bad id fails with 404 not an empty page.
    await get_meeting_or_404(session, meeting_id)
    return await meetings_repo.list_transcript(
        session, meeting_id=meeting_id, cursor=cursor, limit=limit
    )
