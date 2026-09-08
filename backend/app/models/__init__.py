"""Import every model module so Base.metadata is fully populated for Alembic autogenerate."""
from app.models.meeting import (
    ActionItem,
    Chapter,
    Comment,
    Highlight,
    Job,
    Meeting,
    MeetingTag,
    Note,
    Participant,
    Soundbite,
    Summary,
    Tag,
    TranscriptSegment,
    User,
)

__all__ = [
    "ActionItem",
    "Chapter",
    "Comment",
    "Highlight",
    "Job",
    "Meeting",
    "MeetingTag",
    "Note",
    "Participant",
    "Soundbite",
    "Summary",
    "Tag",
    "TranscriptSegment",
    "User",
]
