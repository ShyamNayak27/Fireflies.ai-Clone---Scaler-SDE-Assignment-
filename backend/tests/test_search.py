"""Global FTS search (docs/ARCHITECTURE.md §7.2) — stemming, ranking, and safe
handling of hostile query input."""
from __future__ import annotations

from httpx import AsyncClient


async def test_search_finds_seeded_content(client: AsyncClient, seeded_meeting_id: int) -> None:
    resp = await client.get("/api/search", params={"q": "precision"})
    assert resp.status_code == 200
    hits = resp.json()["items"]
    assert any(h["meeting_id"] == seeded_meeting_id for h in hits)


async def test_search_stemming_matches_related_word_forms(
    client: AsyncClient, seeded_meeting_id: int
) -> None:
    # porter-stemmed FTS5 index: "detection" should match a query for "detect".
    resp = await client.get("/api/search", params={"q": "detect"})
    hits = resp.json()["items"]
    assert any(h["meeting_id"] == seeded_meeting_id for h in hits)


async def test_search_snippet_highlights_the_match(client: AsyncClient, seeded_meeting_id: int) -> None:
    resp = await client.get("/api/search", params={"q": "precision"})
    hits = [h for h in resp.json()["items"] if h["meeting_id"] == seeded_meeting_id]
    assert hits
    assert "<mark>" in hits[0]["snippet"]


async def test_search_with_hostile_characters_does_not_error(client: AsyncClient) -> None:
    for q in ['"unterminated', "*", "()", "OR AND NOT", "a\"b'c"]:
        resp = await client.get("/api/search", params={"q": q})
        assert resp.status_code == 200


async def test_search_requires_a_query(client: AsyncClient) -> None:
    resp = await client.get("/api/search", params={"q": ""})
    assert resp.status_code == 422


async def test_search_with_no_matches_returns_empty_list(client: AsyncClient) -> None:
    resp = await client.get("/api/search", params={"q": "zzzznonexistenttermzzzz"})
    assert resp.status_code == 200
    assert resp.json()["items"] == []
