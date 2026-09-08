"""Business logic layer. No SQL (that's repositories/), no HTTP (that's routers/)."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import ActionItem, Meeting
from app.repositories import action_items as action_items_repo
from app.services.meetings import get_meeting_or_404


async def list_action_items(session: AsyncSession, *, meeting_id: int) -> list[ActionItem]:
    await get_meeting_or_404(session, meeting_id)  # 404 on a bad id, not an empty list
    return await action_items_repo.list_action_items(session, meeting_id=meeting_id)


async def create_action_item(
    session: AsyncSession,
    *,
    meeting_id: int,
    text: str,
    assignee_id: int | None,
    due_date: str | None,
    source_segment_id: int | None,
) -> ActionItem:
    meeting: Meeting = await get_meeting_or_404(session, meeting_id)
    item = await action_items_repo.create_action_item(
        session,
        meeting_id=meeting.id,
        text=text,
        assignee_id=assignee_id,
        due_date=due_date,
        source_segment_id=source_segment_id,
    )
    await session.commit()
    return item


async def _get_action_item_or_404(session: AsyncSession, *, action_item_id: int) -> ActionItem:
    item = await action_items_repo.get_action_item(session, action_item_id=action_item_id)
    if item is None:
        raise NotFoundError("action item", action_item_id)
    return item


async def update_action_item(
    session: AsyncSession,
    *,
    action_item_id: int,
    text: str | None,
    completed: bool | None,
    due_date: str | None,
    assignee_id: int | None,
) -> ActionItem:
    item = await _get_action_item_or_404(session, action_item_id=action_item_id)
    if text is not None:
        item.text = text
    if due_date is not None:
        item.due_date = due_date
    if assignee_id is not None:
        item.assignee_id = assignee_id
    if completed is not None and completed != item.completed:
        item.completed = completed
        item.completed_at = datetime.now(UTC).isoformat() if completed else None
    await session.commit()
    await session.refresh(item, attribute_names=["assignee"])
    return item


async def delete_action_item(session: AsyncSession, *, action_item_id: int) -> int:
    """Returns the deleted item's meeting_id, so the caller can invalidate that
    meeting's caches without a second query for a row that no longer exists."""
    item = await _get_action_item_or_404(session, action_item_id=action_item_id)
    meeting_id = item.meeting_id
    await action_items_repo.delete_action_item(session, item=item)
    await session.commit()
    return meeting_id
