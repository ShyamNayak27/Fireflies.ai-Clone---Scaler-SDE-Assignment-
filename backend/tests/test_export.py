"""GET /api/meetings/{id}/export (Milestone 12)."""
from __future__ import annotations

from httpx import AsyncClient


async def test_export_markdown_contains_transcript_and_headers(
    client: AsyncClient, seeded_meeting_id: int
) -> None:
    resp = await client.get(f"/api/meetings/{seeded_meeting_id}/export", params={"format": "md"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert "attachment" in resp.headers["content-disposition"]
    body = resp.text
    assert body.startswith("# Search fixture meeting")
    assert "## Transcript" in body
    assert "crack detection model precision" in body


async def test_export_txt_has_no_markdown_syntax(client: AsyncClient, seeded_meeting_id: int) -> None:
    resp = await client.get(f"/api/meetings/{seeded_meeting_id}/export", params={"format": "txt"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    body = resp.text
    assert "SEARCH FIXTURE MEETING" in body  # uppercase heading, not "# "
    assert not body.startswith("#")


async def test_export_rejects_unknown_format(client: AsyncClient, seeded_meeting_id: int) -> None:
    resp = await client.get(f"/api/meetings/{seeded_meeting_id}/export", params={"format": "pdf"})
    assert resp.status_code == 422


async def test_export_missing_meeting_is_404(client: AsyncClient) -> None:
    resp = await client.get("/api/meetings/999999/export", params={"format": "md"})
    assert resp.status_code == 404
