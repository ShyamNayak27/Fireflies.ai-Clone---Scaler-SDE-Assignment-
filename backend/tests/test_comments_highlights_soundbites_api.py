"""Comments, highlights, and soundbites (Milestone 12) — all thin CRUD over
existing schema tables (app/models/meeting.py), exercised the same way the
already-shipped action-items CRUD is."""
from __future__ import annotations

from httpx import AsyncClient


async def _first_segment_id(client: AsyncClient, meeting_id: int) -> int:
    transcript = (await client.get(f"/api/meetings/{meeting_id}/transcript")).json()
    return transcript["items"][0]["id"]


async def test_comment_lifecycle(client: AsyncClient, seeded_meeting_id: int) -> None:
    segment_id = await _first_segment_id(client, seeded_meeting_id)

    created = await client.post(f"/api/segments/{segment_id}/comments", json={"body": "Nice catch."})
    assert created.status_code == 201
    comment = created.json()

    listed = (await client.get(f"/api/meetings/{seeded_meeting_id}/comments")).json()
    assert any(c["id"] == comment["id"] for c in listed)

    deleted = await client.delete(f"/api/comments/{comment['id']}")
    assert deleted.status_code == 204

    listed_after = (await client.get(f"/api/meetings/{seeded_meeting_id}/comments")).json()
    assert all(c["id"] != comment["id"] for c in listed_after)


async def test_comment_on_missing_segment_is_404(client: AsyncClient) -> None:
    resp = await client.post("/api/segments/999999/comments", json={"body": "x"})
    assert resp.status_code == 404


async def test_highlight_offset_is_clamped_to_segment_length(
    client: AsyncClient, seeded_meeting_id: int
) -> None:
    segment_id = await _first_segment_id(client, seeded_meeting_id)
    resp = await client.post(
        f"/api/segments/{segment_id}/highlights",
        json={"color": "yellow", "start_offset": 0, "end_offset": 999999},
    )
    assert resp.status_code == 201
    highlight = resp.json()

    segment = (await client.get(f"/api/meetings/{seeded_meeting_id}/transcript")).json()["items"][0]
    assert highlight["end_offset"] == len(segment["text"])  # clamped, not rejected


async def test_highlight_lifecycle(client: AsyncClient, seeded_meeting_id: int) -> None:
    segment_id = await _first_segment_id(client, seeded_meeting_id)
    created = (
        await client.post(
            f"/api/segments/{segment_id}/highlights",
            json={"color": "green", "start_offset": 0, "end_offset": 5},
        )
    ).json()

    listed = (await client.get(f"/api/meetings/{seeded_meeting_id}/highlights")).json()
    assert any(h["id"] == created["id"] for h in listed)

    deleted = await client.delete(f"/api/highlights/{created['id']}")
    assert deleted.status_code == 204


async def test_soundbite_lifecycle(client: AsyncClient, meeting_id: int) -> None:
    created = await client.post(
        f"/api/meetings/{meeting_id}/soundbites",
        json={"title": "Great quote", "start_ms": 0, "end_ms": 5000},
    )
    assert created.status_code == 201
    soundbite = created.json()

    listed = (await client.get(f"/api/meetings/{meeting_id}/soundbites")).json()
    assert any(s["id"] == soundbite["id"] for s in listed)

    deleted = await client.delete(f"/api/soundbites/{soundbite['id']}")
    assert deleted.status_code == 204

    listed_after = (await client.get(f"/api/meetings/{meeting_id}/soundbites")).json()
    assert listed_after == []


async def test_soundbite_on_missing_meeting_is_404(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/meetings/999999/soundbites", json={"title": "x", "start_ms": 0, "end_ms": 1000}
    )
    assert resp.status_code == 404
