"""Scrubbing stage (docs/ARCHITECTURE.md §5.4) — the mandatory last step before
an ingested transcript is materialized as real rows. Two separable jobs:

1. Pseudonymize speaker names: every real name becomes a different, plausible
   fake name, deterministically (same input name -> same fake, every time,
   within and across runs) via a salted hash so the mapping isn't reversible
   without the salt, but is stable enough that "Alex Kim" reads as one
   consistent person throughout a meeting.
2. Scrub contact data found *inside* utterance text — emails, phone numbers,
   URLs, and long digit runs (card/SSN-shaped numbers) — replaced with
   plausible-looking fakes of the same shape (an email that still looks like an
   email), not a `[REDACTED]` token. A `[REDACTED]` marker announces exactly
   where sensitive data used to be and still tells a reader how many characters
   it had; a same-shaped fake gives nothing away.

Both use `settings.ingest_scrub_salt` (app.core.config) so pseudonyms aren't
guessable without it, but are cheap to audit/regenerate if the salt ever needs
to rotate.
"""
from __future__ import annotations

import hashlib
import re

from app.core.config import get_settings

_FIRST_NAMES = [
    "Jordan", "Casey", "Morgan", "Taylor", "Riley", "Avery", "Quinn", "Rowan",
    "Skyler", "Reese", "Dakota", "Emerson", "Finley", "Harper", "Kendall",
    "Logan", "Parker", "Sage", "Micah", "Nico",
]
_LAST_NAMES = [
    "Reyes", "Patel", "Novak", "Alvarez", "Brennan", "Osei", "Lindqvist",
    "Farah", "Chun", "Delgado", "Whitfield", "Marsh", "Okafor", "Ibsen",
    "Castellano", "Prasad", "Duarte", "Yoon", "Bianchi", "Mercer",
]

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[a-zA-Z]{2,}")
_URL_RE = re.compile(r"https?://[^\s)>\].,;:!?]+|www\.[^\s)>\].,;:!?]+", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\-. ]{7,}\d)(?!\d)")
_LONG_DIGIT_RE = re.compile(r"(?<!\d)\d{9,}(?!\d)")


def _salted_index(value: str, salt: str, modulus: int) -> int:
    digest = hashlib.sha256(f"{salt}:{value.strip().lower()}".encode()).hexdigest()
    return int(digest, 16) % modulus


def _fake_name_for(real_name: str, salt: str) -> str:
    first = _FIRST_NAMES[_salted_index(real_name, salt, len(_FIRST_NAMES))]
    last = _LAST_NAMES[_salted_index(real_name + "|last", salt, len(_LAST_NAMES))]
    return f"{first} {last}"


def _fake_email_for(real: str, salt: str) -> str:
    idx = _salted_index(real, salt, 9000) + 1000
    return f"user{idx}@example.com"


def _fake_phone_for(real: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{real}".encode()).hexdigest()
    n = int(digest, 16)
    area = 200 + (n % 700)
    exch = 200 + ((n // 700) % 700)
    line = (n // 490000) % 10000
    return f"({area}) {exch}-{line:04d}"


def _fake_url_for(real: str, salt: str) -> str:
    idx = _salted_index(real, salt, 90000) + 1000
    return f"https://example.com/redacted/{idx}"


def _fake_digits_for(real: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{real}".encode()).hexdigest()
    n = int(digest, 16)
    return str(n)[: len(real)].ljust(len(real), "0")


class Scrubber:
    """One instance per ingest job — memoizes name pseudonyms so every mention
    of "Alex Kim" across a whole transcript maps to the same fake name."""

    def __init__(self, salt: str | None = None) -> None:
        self._salt = salt or get_settings().ingest_scrub_salt
        self._name_cache: dict[str, str] = {}

    def pseudonymize_name(self, real_name: str) -> str:
        key = real_name.strip().lower()
        if key not in self._name_cache:
            self._name_cache[key] = _fake_name_for(real_name, self._salt)
        return self._name_cache[key]

    def scrub_text(self, text: str) -> str:
        salt = self._salt
        text = _EMAIL_RE.sub(lambda m: _fake_email_for(m.group(0), salt), text)
        text = _URL_RE.sub(lambda m: _fake_url_for(m.group(0), salt), text)
        text = _PHONE_RE.sub(lambda m: _fake_phone_for(m.group(0), salt), text)
        text = _LONG_DIGIT_RE.sub(lambda m: _fake_digits_for(m.group(0), salt), text)
        # Also catch any speaker names mentioned in prose (e.g. "thanks, Alex")
        # so a pseudonymized speaker isn't un-pseudonymized by their own line.
        for real_name, fake_name in self._name_cache.items():
            pattern = re.compile(rf"\b{re.escape(real_name)}\b", re.IGNORECASE)
            text = pattern.sub(fake_name, text)
        return text
