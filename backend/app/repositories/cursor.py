"""Opaque cursor encode/decode for keyset pagination.

The wire format is intentionally opaque (base64 of a small tuple) so it can change
without breaking clients — see docs/ARCHITECTURE.md §6.3.
"""

from __future__ import annotations

import base64
import json


def encode_cursor(*parts: object) -> str:
    raw = json.dumps(list(parts)).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str) -> list:
    raw = base64.urlsafe_b64decode(cursor.encode())
    return json.loads(raw)
