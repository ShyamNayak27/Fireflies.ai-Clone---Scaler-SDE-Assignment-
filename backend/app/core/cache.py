"""CacheBackend seam (docs/ARCHITECTURE.md §13.3). An in-process TTL cache today —
correct for a single web process, and exactly the shape that swaps for Redis behind
the same three methods once there's more than one process to keep in sync.

Invalidation is by prefix, not by individual key: a write to a meeting clears every
cached page that could contain it (list pages, the detail, its transcript) rather
than trying to enumerate exactly which cache entries a given write could affect,
which is the class of bug that produces stale reads after a mutation.
"""

from __future__ import annotations

import time
from typing import Protocol


class CacheBackend(Protocol):
    def get(self, key: str) -> object | None: ...
    def set(self, key: str, value: object, ttl_seconds: int) -> None: ...
    def invalidate_prefix(self, prefix: str) -> None: ...


class InMemoryTTLCache:
    """Not thread-safe across multiple processes — that's precisely the limit
    that makes swapping to Redis the right call once the app scales past one
    process (docs/ARCHITECTURE.md §13.3)."""

    def __init__(self, max_entries: int = 2000) -> None:
        self._store: dict[str, tuple[float, object]] = {}
        self._max_entries = max_entries

    def get(self, key: str) -> object | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: object, ttl_seconds: int) -> None:
        if len(self._store) >= self._max_entries:
            # Cheap eviction: drop the oldest-inserted entry rather than maintaining
            # a real LRU — acceptable because this cache only ever holds cheaply
            # recomputed read results, never anything authoritative.
            oldest_key = next(iter(self._store), None)
            if oldest_key is not None:
                self._store.pop(oldest_key, None)
        self._store[key] = (time.monotonic() + ttl_seconds, value)

    def invalidate_prefix(self, prefix: str) -> None:
        for key in [k for k in self._store if k.startswith(prefix)]:
            self._store.pop(key, None)


# Process-wide singleton. Fine for a single-process deployment; the seam above is
# what makes it not fine forever.
cache = InMemoryTTLCache()


def invalidate_meeting_caches(meeting_id: int | None = None) -> None:
    """Called by every write path touching a meeting or anything under it
    (action items, summary regeneration) so a mutation is never masked by a
    stale cached read. Shared across routers rather than duplicated per file —
    see app/routers/meetings.py and app/routers/action_items.py."""
    cache.invalidate_prefix("meetings:list:")
    if meeting_id is not None:
        cache.invalidate_prefix(f"meetings:detail:{meeting_id}")
        cache.invalidate_prefix(f"meetings:transcript:{meeting_id}")
        cache.invalidate_prefix(f"meetings:summary:{meeting_id}")
        cache.invalidate_prefix(f"meetings:action_items:{meeting_id}")
