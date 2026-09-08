"""SQL only — see the layering rule in docs/ARCHITECTURE.md §6.1."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Soundbite


async def list_soundbites(session: AsyncSession, *, meeting_id: int) -> list[Soundbite]:
    stmt = select(Soundbite).where(Soundbite.meeting_id == meeting_id).order_by(Soundbite.start_ms)
    return list((await session.execute(stmt)).scalars().all())


async def create_soundbite(
    session: AsyncSession, *, meeting_id: int, title: str, start_ms: int, end_ms: int
) -> Soundbite:
    soundbite = Soundbite(meeting_id=meeting_id, title=title, start_ms=start_ms, end_ms=end_ms)
    session.add(soundbite)
    await session.flush()
    return soundbite


async def get_soundbite(session: AsyncSession, *, soundbite_id: int) -> Soundbite | None:
    return await session.get(Soundbite, soundbite_id)


async def delete_soundbite(session: AsyncSession, *, soundbite: Soundbite) -> None:
    await session.delete(soundbite)
