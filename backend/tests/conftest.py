"""Shared pytest fixtures. The app's `engine`/`SessionLocal` are created at
*import* time from `settings.database_url` (app/core/db.py), so the test
DATABASE_URL has to be set before that module — or anything importing it — is
first touched anywhere in the process. That's why this file sets the env var
at collection time, before any `app.*` import below.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator

_tmp_dir = tempfile.mkdtemp(prefix="fireflies-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp_dir}/test.db"
os.environ["INGEST_SCRUB_SALT"] = "test-salt"
os.environ["RATE_LIMIT_DEFAULT"] = (
    "10000/minute"  # tests fire many requests fast; hardening's own limits are covered separately
)
os.environ["RATE_LIMIT_AI"] = "10000/minute"

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.db import Base, engine
from app.main import app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _prepare_database() -> AsyncIterator[None]:
    """Creates every ORM table plus the hand-written FTS5 virtual table and its
    sync triggers (docs/ARCHITECTURE.md §4.4) — the one piece of schema that
    isn't part of `Base.metadata` because it isn't a mapped model. One schema
    for the whole test session; individual tests avoid colliding by creating
    their own meeting rather than sharing fixture data.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE segments_fts USING fts5(
                    text, content='transcript_segments', content_rowid='id',
                    tokenize='porter unicode61'
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TRIGGER segments_ai AFTER INSERT ON transcript_segments BEGIN
                    INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
                END
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TRIGGER segments_ad AFTER DELETE ON transcript_segments BEGIN
                    INSERT INTO segments_fts(segments_fts, rowid, text) VALUES('delete', old.id, old.text);
                END
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TRIGGER segments_au AFTER UPDATE ON transcript_segments BEGIN
                    INSERT INTO segments_fts(segments_fts, rowid, text) VALUES('delete', old.id, old.text);
                    INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
                END
                """
            )
        )
        await conn.execute(
            text(
                "INSERT INTO users (id, name, email, created_at) "
                "VALUES (1, 'Demo User', 'demo@test.dev', datetime('now'))"
            )
        )
    yield


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def meeting_id(client: AsyncClient) -> int:
    """A fresh, empty-transcript meeting for tests that just need *a* meeting
    to hang a resource off of. Created via the real ingest endpoint (paste
    mode) rather than inserted directly, so these tests also incidentally
    exercise ingest — but any test needing actual transcript segments creates
    its own via `seeded_meeting_id` below instead."""
    resp = await client.post(
        "/api/meetings/ingest",
        data={
            "title": "API test meeting",
            "text": "Speaker One  0:00\nHello there, this is a test line.",
        },
    )
    assert resp.status_code == 202
    job_id = resp.json()["id"]
    return await _await_job_meeting_id(client, job_id)


@pytest_asyncio.fixture
async def seeded_meeting_id(client: AsyncClient) -> int:
    """A meeting with a few real transcript segments — for search/export tests
    that need actual content, not just a title."""
    text_ = (
        "Alex Kim  0:00\n"
        "Let's talk about the crack detection model precision this week.\n\n"
        "Priya Shah  0:10\n"
        "Precision is up to ninety one percent on the validation set.\n\n"
        "Alex Kim  0:20\n"
        "Great, I'll follow up with the dashboard cold start issue by Friday.\n"
    )
    resp = await client.post(
        "/api/meetings/ingest", data={"title": "Search fixture meeting", "text": text_}
    )
    assert resp.status_code == 202
    job_id = resp.json()["id"]
    return await _await_job_meeting_id(client, job_id)


async def _await_job_meeting_id(client: AsyncClient, job_id: str) -> int:
    import asyncio

    for _ in range(50):
        job = (await client.get(f"/api/jobs/{job_id}")).json()
        if job["status"] == "succeeded":
            assert job["meeting_id"] is not None
            return job["meeting_id"]
        if job["status"] == "failed":
            raise AssertionError(f"ingest job failed: {job['error']}")
        await asyncio.sleep(0.02)
    raise AssertionError("ingest job never completed")
