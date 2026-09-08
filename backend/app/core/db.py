"""Async SQLAlchemy engine/session setup, with SQLite pragmas applied per-connection.

See docs/ARCHITECTURE.md §4 for why WAL mode and foreign keys matter here: WAL lets
readers proceed while a write is in flight (SQLite's actual concurrency story), and
foreign_keys must be turned on per-connection — SQLite ignores FK constraints by
default unless this pragma is set on every new connection.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
    if "sqlite" not in settings.database_url:
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA busy_timeout = 5000")
    cursor.close()


class Base(DeclarativeBase):
    pass


SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency. Routers depend on this, never on the engine directly."""
    async with SessionLocal() as session:
        yield session
