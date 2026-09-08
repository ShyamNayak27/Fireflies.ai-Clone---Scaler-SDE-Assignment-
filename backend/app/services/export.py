"""Renders a meeting (summary, action items, transcript) as a standalone document —
the "download this meeting" bonus (docs/ARCHITECTURE.md §6.2 documented this as
`GET .../export?format=md|txt` from the start). No SQL of its own beyond what the
repositories it composes already expose; no HTTP (that's routers/export.py).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.repositories import action_items as action_items_repo
from app.repositories import meetings as meetings_repo
from app.repositories import summary as summary_repo
from app.services.meetings import get_meeting_or_404


def _mmss(ms: int) -> str:
    total_s = ms // 1000
    return f"{total_s // 60:02d}:{total_s % 60:02d}"


async def render_meeting_export(session: AsyncSession, *, meeting_id: int, fmt: str) -> tuple[str, str]:
    """Returns (content, filename). `fmt` is 'md' or 'txt' — markdown headings
    collapse to plain uppercase labels for the text variant rather than being a
    second, separately-maintained template."""
    if fmt not in ("md", "txt"):
        raise ValueError(f"Unsupported export format: {fmt!r}")

    meeting = await get_meeting_or_404(session, meeting_id)
    meeting_with_summary = await summary_repo.get_meeting_with_summary(session, meeting_id=meeting_id)
    if meeting_with_summary is None:
        raise NotFoundError("meeting", meeting_id)  # can't happen given the 404 above, but keeps mypy honest
    action_items = await action_items_repo.list_action_items(session, meeting_id=meeting_id)
    segments = await meetings_repo.get_all_segments(session, meeting_id=meeting_id)

    md = fmt == "md"
    lines: list[str] = []

    def h1(text: str) -> None:
        lines.append(f"# {text}" if md else text.upper())

    def h2(text: str) -> None:
        lines.append(f"## {text}" if md else text.upper())

    h1(meeting.title)
    lines.append(f"{meeting.started_at} · {meeting.duration_ms // 60000} min")
    if meeting.participants:
        lines.append("Participants: " + ", ".join(p.name for p in meeting.participants))
    lines.append("")

    if meeting_with_summary.summary is not None:
        h2("Overview")
        lines.append(meeting_with_summary.summary.overview)
        lines.append("")
        for chapter in meeting_with_summary.chapters:
            heading = f"{chapter.title} ({_mmss(chapter.start_ms)}–{_mmss(chapter.end_ms)})"
            lines.append(("### " if md else "") + heading)
            for note in chapter.notes:
                bullet = "- " if md else "  - "
                ts = f" [{_mmss(note.start_ms)}]" if note.start_ms is not None else ""
                lines.append(f"{bullet}{note.text}{ts}")
            lines.append("")

    if action_items:
        h2("Action items")
        for item in action_items:
            box = "[x]" if item.completed else "[ ]"
            checkbox = f"- {box} " if md else f"  {box} "
            assignee = f" (@{item.assignee.name})" if item.assignee else ""
            due = f" — due {item.due_date}" if item.due_date else ""
            lines.append(f"{checkbox}{item.text}{assignee}{due}")
        lines.append("")

    if segments:
        h2("Transcript")
        for seg in segments:
            speaker = seg.speaker.name if seg.speaker else "Unknown"
            lines.append(f"**[{_mmss(seg.start_ms)}] {speaker}:** {seg.text}" if md else f"[{_mmss(seg.start_ms)}] {speaker}: {seg.text}")

    content = "\n".join(lines).rstrip() + "\n"
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in meeting.title).strip() or "meeting"
    filename = f"{safe_title.replace(' ', '_')}.{fmt}"
    return content, filename
