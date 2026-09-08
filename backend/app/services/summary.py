"""Business logic layer. No SQL (that's repositories/), no HTTP (that's routers/)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.repositories import summary as summary_repo
from app.schemas.meeting import ChapterOut, NoteOut, SummaryOut


async def get_summary_or_404(session: AsyncSession, *, meeting_id: int) -> SummaryOut:
    meeting = await summary_repo.get_meeting_with_summary(session, meeting_id=meeting_id)
    if meeting is None:
        raise NotFoundError("meeting", meeting_id)
    if meeting.summary is None:
        # Distinct from "meeting doesn't exist" — a real state for a meeting
        # whose summarize job hasn't run yet (see docs/ARCHITECTURE.md §9.1).
        raise NotFoundError("summary for meeting", meeting_id)

    return SummaryOut(
        overview=meeting.summary.overview,
        model=meeting.summary.model,
        generated_at=meeting.summary.generated_at,
        chapters=[
            ChapterOut(
                title=chapter.title,
                start_ms=chapter.start_ms,
                end_ms=chapter.end_ms,
                notes=[NoteOut.model_validate(note) for note in chapter.notes],
            )
            for chapter in meeting.chapters
        ],
    )
