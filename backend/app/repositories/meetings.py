"""SQL only. No HTTP concepts here — see the layering rule in docs/ARCHITECTURE.md §6.1."""

from __future__ import annotations

from sqlalchemy import delete as sa_delete
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Meeting, MeetingTag, Participant, Tag, TranscriptSegment
from app.repositories.cursor import decode_cursor, encode_cursor

DEFAULT_PAGE_SIZE = 20


async def list_meetings(
    session: AsyncSession,
    *,
    owner_id: int,
    cursor: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    tag: str | None = None,
    q: str | None = None,
    participant: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: str = "recent",
) -> tuple[list[Meeting], str | None]:
    """Keyset pagination on (started_at, id) — see docs/ARCHITECTURE.md §6.3.
    Verified against ix_meetings_recency via EXPLAIN QUERY PLAN during design.

    `sort="oldest"` flips both the ORDER BY and the keyset comparison direction
    — a naive version that only flips ORDER BY would re-serve the same first
    page forever once a cursor is involved.
    """
    oldest_first = sort == "oldest"
    order_cols = (
        (Meeting.started_at.asc(), Meeting.id.asc())
        if oldest_first
        else (Meeting.started_at.desc(), Meeting.id.desc())
    )
    stmt = (
        select(Meeting)
        .where(Meeting.owner_id == owner_id)
        .options(selectinload(Meeting.participants))
        .order_by(*order_cols)
        .limit(limit + 1)
    )
    needs_distinct = False
    if tag:
        # A join rather than a subquery — meetings with more than one matching
        # tag can't happen here since a meeting has at most one link row per
        # tag, so this can't fan out duplicate rows.
        stmt = (
            stmt.join(MeetingTag, MeetingTag.meeting_id == Meeting.id)
            .join(Tag, Tag.id == MeetingTag.tag_id)
            .where(Tag.name == tag)
        )
    if participant:
        # Unlike tag, a meeting can have several participants matching the same
        # substring (rare, but possible) — this join can fan out, so it's the
        # one filter that needs `.distinct()` below.
        stmt = stmt.join(Participant, Participant.meeting_id == Meeting.id).where(
            Participant.name.ilike(f"%{participant}%")
        )
        needs_distinct = True
    if q:
        stmt = stmt.where(Meeting.title.ilike(f"%{q}%"))
    if date_from:
        stmt = stmt.where(Meeting.started_at >= date_from)
    if date_to:
        # started_at is an ISO-8601 string, not a native timestamp column, so a
        # bare date string as an upper bound would exclude that entire day —
        # widen it to the end of that day.
        stmt = stmt.where(Meeting.started_at <= f"{date_to}T23:59:59.999999")
    if needs_distinct:
        stmt = stmt.distinct()
    if cursor:
        cursor_started_at, cursor_id = decode_cursor(cursor)
        # A plain Python tuple `<` here (as this once read) silently degrades to
        # comparing only the first element — SQLAlchemy's ColumnElement.__eq__
        # returns a truthy BinaryExpression rather than a real bool, so CPython's
        # tuple comparison never gets to the id tiebreaker. `tuple_()` builds an
        # actual SQL row-value comparison, which is what keyset pagination needs
        # to stay stable across rows sharing the same `started_at`.
        op = tuple_(Meeting.started_at, Meeting.id)
        stmt = stmt.where(
            op > (cursor_started_at, cursor_id)
            if oldest_first
            else op < (cursor_started_at, cursor_id)
        )

    rows = list((await session.execute(stmt)).scalars().all())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(last.started_at, last.id)
    return rows, next_cursor


async def update_meeting(
    session: AsyncSession, *, meeting: Meeting, title: str | None, description: str | None
) -> Meeting:
    if title is not None:
        meeting.title = title
    if description is not None:
        meeting.description = description
    await session.flush()
    return meeting


async def delete_meeting(session: AsyncSession, *, meeting_id: int) -> None:
    """A raw DELETE, not `session.delete(orm_instance)` — the meeting's children
    (segments, summary, chapters, action items, tags, comments, highlights,
    soundbites) are only cascaded at the DB level (`ondelete="CASCADE"` on every
    FK — see models/meeting.py), not eagerly loaded on this instance, so an
    ORM-level delete would need every relationship loaded first to cascade in
    Python. SQLite has `PRAGMA foreign_keys = ON` (core/db.py) so this cascades
    there too, not just on Postgres."""
    await session.execute(sa_delete(Meeting).where(Meeting.id == meeting_id))


async def get_meeting(session: AsyncSession, meeting_id: int) -> Meeting | None:
    stmt = (
        select(Meeting).where(Meeting.id == meeting_id).options(selectinload(Meeting.participants))
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
