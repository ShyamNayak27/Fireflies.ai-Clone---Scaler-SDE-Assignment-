"""SQL only — see the layering rule in docs/ARCHITECTURE.md §6.1."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MeetingTag, Tag


async def list_tags(session: AsyncSession) -> list[Tag]:
    stmt = select(Tag).order_by(Tag.name)
    return list((await session.execute(stmt)).scalars().all())


async def get_tag_by_name(session: AsyncSession, *, name: str) -> Tag | None:
    stmt = select(Tag).where(Tag.name == name)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_or_create_tag(session: AsyncSession, *, name: str) -> Tag:
    # Case-preserving but not case-duplicating — "Design" and "design" resolve to
    # the same tag, matching how a person actually expects a tag list to behave.
    normalized = name.strip()
    existing = await get_tag_by_name(session, name=normalized)
    if existing is not None:
        return existing
    tag = Tag(name=normalized)
    session.add(tag)
    await session.flush()
    return tag


async def list_tags_for_meeting(session: AsyncSession, *, meeting_id: int) -> list[Tag]:
    stmt = (
        select(Tag)
        .join(MeetingTag, MeetingTag.tag_id == Tag.id)
        .where(MeetingTag.meeting_id == meeting_id)
        .order_by(Tag.name)
    )
    return list((await session.execute(stmt)).scalars().all())


async def add_tag_to_meeting(session: AsyncSession, *, meeting_id: int, tag_id: int) -> None:
    existing = await session.get(MeetingTag, {"meeting_id": meeting_id, "tag_id": tag_id})
    if existing is None:
        session.add(MeetingTag(meeting_id=meeting_id, tag_id=tag_id))
        await session.flush()


async def remove_tag_from_meeting(session: AsyncSession, *, meeting_id: int, tag_id: int) -> bool:
    link = await session.get(MeetingTag, {"meeting_id": meeting_id, "tag_id": tag_id})
    if link is None:
        return False
    await session.delete(link)
    return True


async def tags_by_meeting_ids(
    session: AsyncSession, *, meeting_ids: list[int]
) -> dict[int, list[Tag]]:
    """Batch-loads tags for a page of meetings in one query, so the meetings list
    doesn't pay an N+1 for its tag chips."""
    if not meeting_ids:
        return {}
    stmt = (
        select(MeetingTag.meeting_id, Tag)
        .join(Tag, Tag.id == MeetingTag.tag_id)
        .where(MeetingTag.meeting_id.in_(meeting_ids))
        .order_by(Tag.name)
    )
    rows = (await session.execute(stmt)).all()
    result: dict[int, list[Tag]] = {mid: [] for mid in meeting_ids}
    for meeting_id, tag in rows:
        result[meeting_id].append(tag)
    return result
