"""Cursor pagination on meetings (docs/ARCHITECTURE.md §6.3) — specifically the
case that a plain Python-tuple comparison gets silently wrong: rows that share
an identical `started_at` and are only ordered by the `id` tiebreaker.

`(Meeting.started_at, Meeting.id) < (cursor_started_at, cursor_id)` looks like
a row-value comparison but isn't one — SQLAlchemy's `ColumnElement.__eq__`
returns a truthy `BinaryExpression` rather than a real bool, so CPython's
tuple `__lt__` never gets past the first element and the query silently
degrades to comparing only `started_at`. With several meetings sharing one
timestamp, that drops or repeats rows across pages instead of paging through
all of them exactly once. `repositories/meetings.py` fixes this with
`tuple_(...)`; this test is what would have caught it if it regressed.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio

from app.core.db import SessionLocal
from app.models import Meeting, User
from app.repositories import meetings as meetings_repo


@pytest_asyncio.fixture
async def owner_and_tied_meetings() -> AsyncIterator[tuple[int, list[int]]]:
    """One owner with five meetings that all share the exact same
    `started_at`, so the only thing that can order/paginate them is `id`."""
    async with SessionLocal() as session:
        owner = User(name="Pagination Test Owner", email="pagination-test@test.dev")
        session.add(owner)
        await session.flush()

        same_timestamp = "2026-01-01T00:00:00+00:00"
        meeting_ids: list[int] = []
        for i in range(5):
            m = Meeting(
                owner_id=owner.id,
                title=f"Tied meeting {i}",
                started_at=same_timestamp,
                source="seed",
                status="ready",
            )
            session.add(m)
            await session.flush()
            meeting_ids.append(m.id)
        await session.commit()
        yield owner.id, meeting_ids


async def test_cursor_pagination_covers_every_row_exactly_once_when_timestamps_tie(
    owner_and_tied_meetings: tuple[int, list[int]],
) -> None:
    owner_id, expected_ids = owner_and_tied_meetings

    seen: list[int] = []
    cursor: str | None = None
    async with SessionLocal() as session:
        for _ in range(len(expected_ids) + 1):  # one extra iteration is a bug, not a hang
            page, cursor = await meetings_repo.list_meetings(
                session, owner_id=owner_id, cursor=cursor, limit=2
            )
            seen.extend(m.id for m in page)
            if cursor is None:
                break

    # Same set (nothing skipped, nothing duplicated) — order is descending by
    # (started_at, id), i.e. highest id first, since all timestamps tie.
    assert seen == sorted(expected_ids, reverse=True)
