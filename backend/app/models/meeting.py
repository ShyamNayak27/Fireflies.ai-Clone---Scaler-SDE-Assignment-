"""SQLAlchemy models. One module per aggregate, mirroring docs/ARCHITECTURE.md §4."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _now() -> str:
    return datetime.now(UTC).isoformat()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    avatar_url: Mapped[str | None]
    created_at: Mapped[str] = mapped_column(default=_now)

    meetings: Mapped[list[Meeting]] = relationship(back_populates="owner")


class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (
        CheckConstraint("media_type IN ('audio','video')", name="ck_meeting_media_type"),
        CheckConstraint("source IN ('upload','paste','manual','seed')", name="ck_meeting_source"),
        CheckConstraint("status IN ('processing','ready','failed')", name="ck_meeting_status"),
        # This composite index IS the cursor-pagination key — see repositories/meetings.py
        Index("ix_meetings_recency", "owner_id", "started_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str]
    description: Mapped[str | None]
    started_at: Mapped[str]  # ISO-8601 UTC
    duration_ms: Mapped[int] = mapped_column(default=0)
    media_url: Mapped[str | None]
    media_type: Mapped[str | None]
    source: Mapped[str] = mapped_column(default="seed")
    status: Mapped[str] = mapped_column(default="ready")
    timestamps_estimated: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(default=_now)
    updated_at: Mapped[str] = mapped_column(default=_now)

    owner: Mapped[User] = relationship(back_populates="meetings")
    participants: Mapped[list[Participant]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    segments: Mapped[list[TranscriptSegment]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan", order_by="TranscriptSegment.idx"
    )
    summary: Mapped[Summary | None] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan", order_by="Chapter.position"
    )
    action_items: Mapped[list[ActionItem]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    name: Mapped[str]
    email: Mapped[str | None]
    avatar_color: Mapped[str]
    is_host: Mapped[bool] = mapped_column(default=False)
    raw_labels: Mapped[str | None]  # JSON array of source labels merged into this participant

    meeting: Mapped[Meeting] = relationship(back_populates="participants")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        UniqueConstraint("meeting_id", "idx", name="uq_segment_meeting_idx"),
        Index("ix_segments_meeting_time", "meeting_id", "start_ms"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    idx: Mapped[int]
    speaker_id: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL")
    )
    start_ms: Mapped[int]
    end_ms: Mapped[int]
    text: Mapped[str]

    meeting: Mapped[Meeting] = relationship(back_populates="segments")
    speaker: Mapped[Participant | None] = relationship()


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), unique=True
    )
    overview: Mapped[str]
    model: Mapped[str | None]
    prompt_version: Mapped[str | None]
    generated_at: Mapped[str] = mapped_column(default=_now)

    meeting: Mapped[Meeting] = relationship(back_populates="summary")


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (Index("ix_chapters_meeting", "meeting_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    title: Mapped[str]
    start_ms: Mapped[int]
    end_ms: Mapped[int]
    position: Mapped[int]

    meeting: Mapped[Meeting] = relationship(back_populates="chapters")
    notes: Mapped[list[Note]] = relationship(cascade="all, delete-orphan", order_by="Note.position")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    text: Mapped[str]
    start_ms: Mapped[int | None]
    position: Mapped[int]


class ActionItem(Base):
    __tablename__ = "action_items"
    __table_args__ = (Index("ix_action_items_meeting", "meeting_id", "completed", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    text: Mapped[str]
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL")
    )
    due_date: Mapped[str | None]
    completed: Mapped[bool] = mapped_column(default=False)
    completed_at: Mapped[str | None]
    source_segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="SET NULL")
    )
    position: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[str] = mapped_column(default=_now)

    meeting: Mapped[Meeting] = relationship(back_populates="action_items")
    assignee: Mapped[Participant | None] = relationship()


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


class MeetingTag(Base):
    __tablename__ = "meeting_tags"
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    segment_id: Mapped[int] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    body: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=_now)


class Highlight(Base):
    __tablename__ = "highlights"
    id: Mapped[int] = mapped_column(primary_key=True)
    segment_id: Mapped[int] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    color: Mapped[str] = mapped_column(default="yellow")
    start_offset: Mapped[int]
    end_offset: Mapped[int]


class Soundbite(Base):
    __tablename__ = "soundbites"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    title: Mapped[str]
    start_ms: Mapped[int]
    end_ms: Mapped[int]
    created_at: Mapped[str] = mapped_column(default=_now)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("type IN ('ingest','summarize')", name="ck_job_type"),
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed')", name="ck_job_status"
        ),
        Index("ix_jobs_status", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id: Mapped[int | None] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    type: Mapped[str]
    status: Mapped[str] = mapped_column(default="queued")
    progress: Mapped[int] = mapped_column(default=0)
    stage: Mapped[str | None]
    error: Mapped[str | None]
    payload: Mapped[str | None]  # JSON
    created_at: Mapped[str] = mapped_column(default=_now)
    updated_at: Mapped[str] = mapped_column(default=_now)
