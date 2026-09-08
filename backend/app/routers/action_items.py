"""HTTP only — see the layering rule in docs/ARCHITECTURE.md §6.1.

Keyed by action-item id rather than nested under /meetings/{id}, matching the
API surface documented in docs/ARCHITECTURE.md §6.2 — an action item's id is
already globally unique, and the client editing/completing/deleting one from
the summary panel doesn't need to carry the meeting id around to do it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_meeting_caches
from app.core.config import get_settings
from app.core.db import get_session
from app.core.limiter import limiter
from app.schemas.meeting import ActionItemOut, ActionItemUpdate
from app.services import action_items as action_items_service

router = APIRouter(prefix="/api/action-items", tags=["action-items"])
settings = get_settings()


@router.patch("/{action_item_id}", response_model=ActionItemOut)
@limiter.limit(settings.rate_limit_write)
async def update_action_item(
    request: Request,
    action_item_id: int,
    body: ActionItemUpdate,
    session: AsyncSession = Depends(get_session),
) -> ActionItemOut:
    item = await action_items_service.update_action_item(
        session,
        action_item_id=action_item_id,
        text=body.text,
        completed=body.completed,
        due_date=body.due_date,
        assignee_id=body.assignee_id,
    )
    # The item's own meeting_id is on the row already loaded — no extra query.
    invalidate_meeting_caches(item.meeting_id)
    return ActionItemOut.model_validate(item)


@router.delete("/{action_item_id}", status_code=204)
@limiter.limit(settings.rate_limit_write)
async def delete_action_item(
    request: Request, action_item_id: int, session: AsyncSession = Depends(get_session)
) -> None:
    meeting_id = await action_items_service.delete_action_item(
        session, action_item_id=action_item_id
    )
    invalidate_meeting_caches(meeting_id)
