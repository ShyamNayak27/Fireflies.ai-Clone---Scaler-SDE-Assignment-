"""Application settings, loaded from environment variables / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database — SQLite locally (matches the assignment brief exactly), Postgres in
    # the deployed environment for real concurrent-write capacity. See
    # docs/ARCHITECTURE.md ADR-006. The dialect is read off this URL everywhere
    # rather than hardcoded, so the same code runs against either.
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # AI (docs/ARCHITECTURE.md §9)
    openai_api_key: str | None = None
    summarizer_backend: str = "seeded"  # "llm" | "heuristic" | "seeded" — see get_summarizer()
    llm_model: str = "gpt-4o-mini"  # used by both the map-reduce summarizer and RAG chat

    # Speech-to-text (live recording — docs/ARCHITECTURE.md §14)
    transcriber_backend: str = "unavailable"  # "openai" | "unavailable"
    media_storage_dir: str = "./data/media"

    # Jobs
    job_poll_interval_ms: int = 1000

    # Ingest scrubbing (docs/ARCHITECTURE.md §5.4) — salts the pseudonymization
    # hash. Fixed default is fine for this assignment's single-tenant demo
    # deployment; a real multi-tenant deployment would set this per-environment
    # so pseudonyms aren't guessable/reversible across installs.
    ingest_scrub_salt: str = "fireflies-clone-dev-salt"

    # Rate limiting (docs/ARCHITECTURE.md §13.2) — per-client-IP, sliding window.
    rate_limit_default: str = "120/minute"
    rate_limit_write: str = "30/minute"
    rate_limit_ai: str = "10/minute"

    # Cache (docs/ARCHITECTURE.md §13.3)
    cache_ttl_seconds: int = 30

    # Error tracking — optional, no-op unless set (docs/ARCHITECTURE.md §13.4)
    sentry_dsn: str | None = None

    environment: str = "development"

    @property
    def sqlite_path(self) -> Path | None:
        if not self.is_sqlite:
            return None
        # sqlite+aiosqlite:///./data/app.db -> ./data/app.db
        raw = self.database_url.split(":///")[-1]
        return Path(raw)

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url

    @property
    def is_postgres(self) -> bool:
        return "postgres" in self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
