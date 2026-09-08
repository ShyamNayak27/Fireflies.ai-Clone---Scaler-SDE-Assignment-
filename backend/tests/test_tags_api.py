"""Tags CRUD + list-filter (Milestone 12)."""
from __future__ import annotations

from httpx import AsyncClient


async def test_add_tag_creates_and_attaches(client: AsyncClient, meeting_id: int) -> None:
    resp = await client.post(f"/api/meetings/{meeting_id}/tags", json={"name": "Standup"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Standup"

    detail = (await client.get(f"/api/meetings/{meeting_id}")).json()
    assert {"name": "Standup"}.items() <= detail["tags"][0].items()


async def test_adding_the_same_tag_name_twice_reuses_it_not_duplicates(
    client: AsyncClient, meeting_id: int
) -> None:
    first = await client.post(f"/api/meetings/{meeting_id}/tags", json={"name": "Reused"})
    second = await client.post(f"/api/meetings/{meeting_id}/tags", json={"name": "Reused"})
    assert first.json()["id"] == second.json()["id"]

    all_tags = (await client.get("/api/tags")).json()
    assert sum(1 for t in all_tags if t["name"] == "Reused") == 1


async def test_meetings_list_filters_by_tag(client: AsyncClient, meeting_id: int) -> None:
    await client.post(f"/api/meetings/{meeting_id}/tags", json={"name": "FilterMe"})

    filtered = (await client.get("/api/meetings", params={"tag": "FilterMe"})).json()
    assert any(m["id"] == meeting_id for m in filtered["items"])

    unfiltered_by_missing_tag = (await client.get("/api/meetings", params={"tag": "NoSuchTag"})).json()
    assert unfiltered_by_missing_tag["items"] == []


async def test_remove_tag(client: AsyncClient, meeting_id: int) -> None:
    tag = (await client.post(f"/api/meetings/{meeting_id}/tags", json={"name": "Temp"})).json()
    resp = await client.delete(f"/api/meetings/{meeting_id}/tags/{tag['id']}")
    assert resp.status_code == 204

    detail = (await client.get(f"/api/meetings/{meeting_id}")).json()
    assert all(t["name"] != "Temp" for t in detail["tags"])


async def test_remove_tag_not_on_meeting_is_404(client: AsyncClient, meeting_id: int) -> None:
    resp = await client.delete(f"/api/meetings/{meeting_id}/tags/999999")
    assert resp.status_code == 404
    assert resp.json()["type"] == "/problems/not-found"


async def test_add_tag_to_missing_meeting_is_404(client: AsyncClient) -> None:
    resp = await client.post("/api/meetings/999999/tags", json={"name": "X"})
    assert resp.status_code == 404


async def test_add_tag_rejects_empty_name(client: AsyncClient, meeting_id: int) -> None:
    resp = await client.post(f"/api/meetings/{meeting_id}/tags", json={"name": ""})
    assert resp.status_code == 422
