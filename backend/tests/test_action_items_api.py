"""Action item CRUD (Milestone 9) — kept covered here since it was the app's
first client-authored mutation and the pattern every later write (tags,
comments, highlights, soundbites) followed."""
from __future__ import annotations

from httpx import AsyncClient


async def test_create_complete_and_delete_action_item(client: AsyncClient, meeting_id: int) -> None:
    created = await client.post(f"/api/meetings/{meeting_id}/action-items", json={"text": "Follow up"})
    assert created.status_code == 201
    item = created.json()
    assert item["completed"] is False

    completed = await client.patch(f"/api/action-items/{item['id']}", json={"completed": True})
    assert completed.status_code == 200
    assert completed.json()["completed"] is True

    deleted = await client.delete(f"/api/action-items/{item['id']}")
    assert deleted.status_code == 204

    items = (await client.get(f"/api/meetings/{meeting_id}/action-items")).json()
    assert all(i["id"] != item["id"] for i in items)


async def test_completed_items_sort_after_open_ones(client: AsyncClient, meeting_id: int) -> None:
    a = (await client.post(f"/api/meetings/{meeting_id}/action-items", json={"text": "A"})).json()
    b = (await client.post(f"/api/meetings/{meeting_id}/action-items", json={"text": "B"})).json()
    await client.patch(f"/api/action-items/{a['id']}", json={"completed": True})

    items = (await client.get(f"/api/meetings/{meeting_id}/action-items")).json()
    ids_in_order = [i["id"] for i in items]
    assert ids_in_order.index(b["id"]) < ids_in_order.index(a["id"])


async def test_action_item_on_missing_meeting_is_404(client: AsyncClient) -> None:
    resp = await client.get("/api/meetings/999999/action-items")
    assert resp.status_code == 404


async def test_update_missing_action_item_is_404(client: AsyncClient) -> None:
    resp = await client.patch("/api/action-items/999999", json={"completed": True})
    assert resp.status_code == 404
