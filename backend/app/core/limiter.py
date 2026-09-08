"""Per-client-IP sliding-window rate limiting (docs/ARCHITECTURE.md §13.2).

A single shared `limiter` instance so every router decorates against the same
state — two separate Limiter() instances would each track their own counters and
silently double the effective limit.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
