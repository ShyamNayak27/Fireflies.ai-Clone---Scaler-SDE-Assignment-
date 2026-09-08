"""SQL only. No HTTP concepts here — see the layering rule in docs/ARCHITECTURE.md §6.1."""
from __future__ import annotations

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Meeting, MeetingTag, Tag, TranscriptSegment
from app.repositories.cursor import decode_cursor, encode_cursor

DEFAULT_PAGE_SIZE = 20


async def list_meetings(
    session: AsyncSession,
    *,
    owner_id: int,
    cursor: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    tag: str | None = None,
) -> tuple[list[Meeting], str | None]:
    """Keyset pagination on (started_at, id) — see docs/ARCHITECTURE.md §6.3.
    Verified against ix_meetings_recency via EXPLAIN QUERY PLAN during design."""
    stmt = (
        select(Meeting)
        .where(Meeting.owner_id == owner_id)
        .options(selectinload(Meeting.participants))
        .order_by(Meeting.started_at.desc(), Meeting.id.desc())
        .limit(limit + 1)
    )
    if tag:
        # A join rather than a subquery — meetings with more than one matching
        # tag can't happen here since a meeting has at most one link row per
        # tag, so this can't fan out duplicate rows.
        stmt = stmt.join(MeetingTag, MeetingTag.meeting_id == Meeting.id).join(
            Tag, Tag.id == MeetingTag.tag_id
        ).where(Tag.name == tag)
    if cursor:
        cursor_started_at, cursor_id = decode_cursor(cursor)
        # A plain Python tuple `<` here (as this once read) silently degrades to
        # comparing only the first element — SQLAlchemy's ColumnElement.__eq__
        # returns a truthy BinaryExpression rather than a real bool, so CPython's
        # tuple comparison never gets to the id tiebreaker. `tuple_()` builds an
        # actual SQL row-value comparison, which is what keyset pagination needs
        # to stay stable across rows sharing the same `started_at`.
        stmt = stmt.where(
            tuple_(Meeting.started_at, Meeting.id) < (cursor_started_at, cursor_id)
        )

    rows = list((await session.execute(stmt)).scalars().all())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(last.started_at, last.id)
    return rows, next_cursor


async def get_meeting(session: AsyncSession, meeting_id: int) -> Meeting | None:
    stmt = (
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .options(selectinload(Meeting.participants))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_transcript(
    session: AsyncSession,
    *,
    meeting_id: int,
    cursor: str | None = None,
    limit: int = 200,
) -> tuple[list[TranscriptSegment], str | None]:
    """Segments are paginated by idx, not offset — a 3-hour meeting's transcript
    is not fetched in one round trip (docs/ARCHITECTURE.md §8, virtualization note)."""
    stmt = (
        select(TranscriptSegment)
        .where(TranscriptSegment.meeting_id == meeting_id)
        .options(selectinload(TranscriptSegment.speaker))
        .order_by(TranscriptSegment.idx)
        .limit(limit + 1)
    )
    if cursor:
        (after_idx,) = decode_cursor(cursor)
        stmt = stmt.where(TranscriptSegment.idx > after_idx)

    rows = list((await session.execute(stmt)).scalars().all())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = encode_cursor(rows[-1].idx)
    return rows, next_cursor


async def get_segment(session: AsyncSession, *, segment_id: int) -> TranscriptSegment | None:
    """Looked up on its own id — comments and highlights (§Milestone 12) attach
    to a segment directly rather than being nested under a meeting in the URL."""
    return await session.get(TranscriptSegment, segment_id)


async def get_all_segments(session: AsyncSession, *, meeting_id: int) -> list[TranscriptSegment]:
    """Unpaginated — for the summarizer (app/ai/summarizer.py) and RAG retrieval
    (app/services/ask.py), both of which need the whole transcript at once, unlike
    the UI's page-at-a-time `list_transcript` above."""
    stmt = (
        select(TranscriptSegment)
        .where(TranscriptSegment.meeting_id == meeting_id)
        .options(selectinload(TranscriptSegment.speaker))
        .order_by(TranscriptSegment.idx)
    )
    return list((await session.execute(stmt)).scalars().all())
