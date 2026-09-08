"""Idempotent seed loader.

Runs on backend boot (see docs/ARCHITECTURE.md §11): if the meetings table is
already non-empty, this is a no-op, so a Render restart never duplicates seed data.
Run standalone with `python -m app.seed.seed`.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal, engine
from app.models import (
    ActionItem,
    Chapter,
    Meeting,
    Note,
    Participant,
    Summary,
    TranscriptSegment,
    User,
)
from app.seed.fixtures import ALL_MEETINGS
from app.seed.timing import estimate_segments, total_duration_ms

logger = logging.getLogger(__name__)

AVATAR_RAMP = [
    "#584CF4",
    "#0F6E68",
    "#D9A15C",
    "#C4507A",
    "#3E7CB1",
    "#7A6FF0",
    "#4C9F70",
    "#B85C38",
]


def avatar_color_for(name: str) -> str:
    digest = hashlib.sha1(name.encode()).hexdigest()
    return AVATAR_RAMP[int(digest, 16) % len(AVATAR_RAMP)]


async def _seed_needed(session: AsyncSession) -> bool:
    count = await session.scalar(select(func.count()).select_from(Meeting))
    return (count or 0) == 0


async def seed(session: AsyncSession) -> None:
    if not await _seed_needed(session):
        logger.info("seed skipped — meetings table is not empty")
        return

    owner = User(name="Shyam Nayak", email="demo@fireflies-clone.dev")
    session.add(owner)
    await session.flush()

    for fixture in ALL_MEETINGS:
        segments_raw = estimate_segments(fixture["dialogue"])
        duration_ms = total_duration_ms(segments_raw)

        meeting = Meeting(
            owner_id=owner.id,
            title=fixture["title"],
            started_at=fixture["started_at"],
            duration_ms=duration_ms,
            media_url=None,  # virtual playback — see docs/ARCHITECTURE.md ADR-004
            source=fixture.get("source", "seed"),
            status="ready",
        )
        session.add(meeting)
        await session.flush()

        participants_by_name: dict[str, Participant] = {}
        for p in fixture["participants"]:
            participant = Participant(
                meeting_id=meeting.id,
                name=p["name"],
                email=p.get("email"),
                is_host=p.get("is_host", False),
                avatar_color=avatar_color_for(p["name"]),
            )
            session.add(participant)
            participants_by_name[p["name"]] = participant
        await session.flush()

        db_segments: list[TranscriptSegment] = []
        for seg in segments_raw:
            speaker = participants_by_name.get(seg["speaker"])
            db_seg = TranscriptSegment(
                meeting_id=meeting.id,
                idx=seg["idx"],
                speaker_id=speaker.id if speaker else None,
                start_ms=seg["start_ms"],
                end_ms=seg["end_ms"],
                text=seg["text"],
            )
            session.add(db_seg)
            db_segments.append(db_seg)
        await session.flush()

        summary = Summary(
            meeting_id=meeting.id,
            overview=fixture["summary_overview"],
            model=None,  # seeded, not LLM-generated — see docs/ARCHITECTURE.md §9.1
            prompt_version="seed-v1",
        )
        session.add(summary)

        for pos, chapter_fixture in enumerate(fixture["chapters"]):
            lo, hi = chapter_fixture["segment_range"]
            chapter = Chapter(
                meeting_id=meeting.id,
                title=chapter_fixture["title"],
                start_ms=db_segments[lo].start_ms,
                end_ms=db_segments[hi].end_ms,
                position=pos,
            )
            session.add(chapter)
            await session.flush()

            for note_pos, note_fixture in enumerate(chapter_fixture["notes"]):
                seg_idx = note_fixture.get("segment_idx")
                session.add(
                    Note(
                        chapter_id=chapter.id,
                        text=note_fixture["text"],
                        start_ms=db_segments[seg_idx].start_ms if seg_idx is not None else None,
                        position=note_pos,
                    )
                )

        for pos, item in enumerate(fixture["action_items"]):
            assignee = participants_by_name.get(item.get("assignee") or "")
            src_idx = item.get("source_segment_idx")
            session.add(
                ActionItem(
                    meeting_id=meeting.id,
                    text=item["text"],
                    assignee_id=assignee.id if assignee else None,
                    due_date=item.get("due_date"),
                    source_segment_id=db_segments[src_idx].id if src_idx is not None else None,
                    position=pos,
                )
            )

        logger.info("seeded meeting %r with %d segments", meeting.title, len(db_segments))

    await session.commit()

    # Backfill the FTS5 index for anything the AFTER INSERT trigger might have raced
    # (it shouldn't, but this makes the seed self-healing rather than trusting silently).
    await session.execute(text_insert_missing_fts())
    await session.commit()


def text_insert_missing_fts():
    from sqlalchemy import text

    return text(
        """
        INSERT INTO segments_fts(rowid, text)
        SELECT s.id, s.text FROM transcript_segments s
        WHERE s.id NOT IN (SELECT rowid FROM segments_fts)
        """
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with SessionLocal() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
