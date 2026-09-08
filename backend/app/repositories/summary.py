"""SQL only — see the layering rule in docs/ARCHITECTURE.md §6.1.

Summary and chapters are sibling relationships on Meeting (see
app/models/meeting.py), not nested under Summary itself — the API shape
(SummaryOut carrying `chapters`) is assembled one level up, in
app/services/summary.py, from the two pieces this module loads together.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Chapter, Meeting


async def get_meeting_with_summary(session: AsyncSession, *, meeting_id: int) -> Meeting | None:
    stmt = (
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .options(
            selectinload(Meeting.summary),
            selectinload(Meeting.chapters).selectinload(Chapter.notes),
        )
    )
    return (await session.execute(stmt)).scalar_one_or_none()
