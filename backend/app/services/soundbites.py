"""Business logic layer. No SQL (that's repositories/), no HTTP (that's routers/)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Soundbite
from app.repositories import soundbites as soundbites_repo
from app.services.meetings import get_meeting_or_404


async def list_soundbites(session: AsyncSession, *, meeting_id: int) -> list[Soundbite]:
    await get_meeting_or_404(session, meeting_id)
    return await soundbites_repo.list_soundbites(session, meeting_id=meeting_id)


async def add_soundbite(
    session: AsyncSession, *, meeting_id: int, title: str, start_ms: int, end_ms: int
) -> Soundbite:
    await get_meeting_or_404(session, meeting_id)
    soundbite = await soundbites_repo.create_soundbite(
        session, meeting_id=meeting_id, title=title, start_ms=start_ms, end_ms=end_ms
    )
    await session.commit()
    return soundbite


async def delete_soundbite(session: AsyncSession, *, soundbite_id: int) -> int:
    soundbite = await soundbites_repo.get_soundbite(session, soundbite_id=soundbite_id)
    if soundbite is None:
        raise NotFoundError("soundbite", soundbite_id)
    meeting_id = soundbite.meeting_id
    await soundbites_repo.delete_soundbite(session, soundbite=soundbite)
    await session.commit()
    return meeting_id
