"""Business logic layer. No SQL (that's repositories/), no HTTP (that's routers/)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Tag
from app.repositories import tags as tags_repo
from app.services.meetings import get_meeting_or_404


async def list_all_tags(session: AsyncSession) -> list[Tag]:
    return await tags_repo.list_tags(session)


async def list_tags_for_meeting(session: AsyncSession, *, meeting_id: int) -> list[Tag]:
    await get_meeting_or_404(session, meeting_id)
    return await tags_repo.list_tags_for_meeting(session, meeting_id=meeting_id)


async def add_tag(session: AsyncSession, *, meeting_id: int, name: str) -> Tag:
    await get_meeting_or_404(session, meeting_id)
    tag = await tags_repo.get_or_create_tag(session, name=name)
    await tags_repo.add_tag_to_meeting(session, meeting_id=meeting_id, tag_id=tag.id)
    await session.commit()
    return tag


async def remove_tag(session: AsyncSession, *, meeting_id: int, tag_id: int) -> None:
    await get_meeting_or_404(session, meeting_id)
    removed = await tags_repo.remove_tag_from_meeting(session, meeting_id=meeting_id, tag_id=tag_id)
    if not removed:
        raise NotFoundError("tag on meeting", tag_id)
    await session.commit()
