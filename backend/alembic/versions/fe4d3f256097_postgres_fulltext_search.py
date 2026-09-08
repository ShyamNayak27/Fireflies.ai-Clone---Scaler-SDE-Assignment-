"""postgres fulltext search (Postgres only)

The Postgres equivalent of migration 52ec82d9f148's FTS5 setup: a generated tsvector
column, a GIN index over it, and no trigger needed because a generated column stays
in sync automatically — Postgres recomputes it on every write, which is actually
simpler than SQLite's external-content trigger approach. Implements the same
SearchBackend protocol from a different repository module (see
app/repositories/search_postgres.py and docs/ARCHITECTURE.md §7.3 / ADR-006).

No-op on any other dialect.

Revision ID: fe4d3f256097
Revises: 52ec82d9f148
Create Date: 2026-09-07
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "fe4d3f256097"
down_revision: Union[str, None] = "52ec82d9f148"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        ALTER TABLE transcript_segments
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('english', text)) STORED
        """
    )
    op.execute(
        "CREATE INDEX ix_segments_search_vector "
        "ON transcript_segments USING GIN (search_vector)"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS ix_segments_search_vector")
    op.execute("ALTER TABLE transcript_segments DROP COLUMN IF EXISTS search_vector")
