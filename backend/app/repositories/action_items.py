"""SQL only — see the layering rule in docs/ARCHITECTURE.md §6.1."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ActionItem


async def list_action_items(session: AsyncSession, *, meeting_id: int) -> list[ActionItem]:
    stmt = (
        select(ActionItem)
        .where(ActionItem.meeting_id == meeting_id)
        .options(selectinload(ActionItem.assignee))
        # Uses ix_action_items_meeting(meeting_id, completed, position) — open
        # items first, in authoring order, matching how the Fireflies panel groups them.
        .order_by(ActionItem.completed, ActionItem.position)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_action_item(session: AsyncSession, *, action_item_id: int) -> ActionItem | None:
    stmt = (
        select(ActionItem)
        .where(ActionItem.id == action_item_id)
        .options(selectinload(ActionItem.assignee))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_action_item(
    session: AsyncSession,
    *,
    meeting_id: int,
    text: str,
    assignee_id: int | None,
    due_date: str | None,
    source_segment_id: int | None,
) -> ActionItem:
    next_position = await session.scalar(
        select(func.coalesce(func.max(ActionItem.position), -1) + 1).where(
            ActionItem.meeting_id == meeting_id
        )
    )
    item = ActionItem(
        meeting_id=meeting_id,
        text=text,
        assignee_id=assignee_id,
        due_date=due_date,
        source_segment_id=source_segment_id,
        position=next_position or 0,
    )
    session.add(item)
    await session.flush()
    await session.refresh(item, attribute_names=["assignee"])
    return item


async def delete_action_item(session: AsyncSession, *, item: ActionItem) -> None:
    await session.delete(item)


async def list_existing_texts(session: AsyncSession, *, meeting_id: int) -> set[str]:
    """Case-insensitive text set, for `app/services/summarize.py` to skip
    re-creating an action item that's already there — a regenerate-summary
    run otherwise piles up duplicates every time it's clicked (caught live:
    three re-summarize calls left twenty action items on a meeting with five
    genuine ones)."""
    rows = await session.execute(
        select(func.lower(ActionItem.text)).where(ActionItem.meeting_id == meeting_id)
    )
    return {r[0] for r in rows}
