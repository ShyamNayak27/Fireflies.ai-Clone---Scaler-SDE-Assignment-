"""Turns a meeting's transcript into a Summary + Chapters + Notes + suggested
ActionItems — the on-demand sibling of the six seed meetings' pre-written
summaries. Same Job lifecycle as `app/services/recordings.py` and
`app/services/ingest.py`: request handler creates the row, a BackgroundTask
runs this against a fresh session.
"""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.summarizer import SegmentInput, SummaryDraft, get_summarizer
from app.models import Chapter, Job, Meeting, Note, Participant, Summary
from app.repositories import meetings as meetings_repo
from app.repositories.action_items import create_action_item, list_existing_texts

logger = logging.getLogger(__name__)


async def create_summarize_job(session: AsyncSession, *, meeting_id: int) -> Job:
    job = Job(
        id=str(uuid.uuid4()),
        type="summarize",
        meeting_id=meeting_id,
        status="queued",
        payload=json.dumps({"meeting_id": meeting_id}),
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def _replace_summary(session: AsyncSession, *, meeting_id: int, draft: SummaryDraft) -> None:
    # Regenerating replaces whatever's there — Chapter's cascade deletes its
    # Notes for free (app/models/meeting.py), so only Chapter and Summary need
    # an explicit delete.
    await session.execute(delete(Chapter).where(Chapter.meeting_id == meeting_id))
    await session.execute(delete(Summary).where(Summary.meeting_id == meeting_id))

    session.add(
        Summary(
            meeting_id=meeting_id, overview=draft.overview, model=draft.model, prompt_version="v1"
        )
    )
    for position, chapter_draft in enumerate(draft.chapters):
        chapter = Chapter(
            meeting_id=meeting_id,
            title=chapter_draft.title,
            start_ms=chapter_draft.start_ms,
            end_ms=chapter_draft.end_ms,
            position=position,
        )
        session.add(chapter)
        await session.flush()
        for note_position, note_draft in enumerate(chapter_draft.notes):
            session.add(
                Note(
                    chapter_id=chapter.id,
                    text=note_draft.text,
                    start_ms=note_draft.start_ms,
                    position=note_position,
                )
            )


async def _resolve_assignee_id(
    session: AsyncSession, *, meeting_id: int, speaker_name: str | None
) -> int | None:
    if not speaker_name:
        return None
    stmt = select(Participant.id).where(
        Participant.meeting_id == meeting_id, Participant.name == speaker_name
    )
    return await session.scalar(stmt)


async def process_summarize_job(session: AsyncSession, *, job: Job) -> None:
    payload = json.loads(job.payload or "{}")
    meeting_id = payload["meeting_id"]

    job.status = "running"
    job.stage = "summarizing"
    await session.commit()

    segments = await meetings_repo.get_all_segments(session, meeting_id=meeting_id)
    if not segments:
        job.status = "failed"
        job.error = "This meeting has no transcript to summarize."
        await session.commit()
        return

    meeting = await session.get(Meeting, meeting_id)
    title = meeting.title if meeting else "Untitled meeting"

    inputs = [
        SegmentInput(
            id=s.id,
            idx=s.idx,
            start_ms=s.start_ms,
            end_ms=s.end_ms,
            speaker_name=s.speaker.name if s.speaker else None,
            text=s.text,
        )
        for s in segments
    ]

    summarizer = get_summarizer()
    try:
        draft = await summarizer.summarize(inputs, title)
    except Exception as exc:  # noqa: BLE001 — LLM failure falls back rather than failing the job
        logger.warning("LLM summarizer failed (%s); falling back to heuristic", exc)
        from app.ai.summarizer import HeuristicSummarizer

        draft = await HeuristicSummarizer().summarize(inputs, title)

    job.stage = "materializing"
    await session.commit()

    await _replace_summary(session, meeting_id=meeting_id, draft=draft)

    existing_texts = await list_existing_texts(session, meeting_id=meeting_id)
    for item_draft in draft.action_items:
        if item_draft.text.strip().lower() in existing_texts:
            continue  # already there — a repeated regenerate-summary call is idempotent, not additive
        source_segment = next((s for s in segments if s.id == item_draft.source_segment_id), None)
        assignee_id = await _resolve_assignee_id(
            session,
            meeting_id=meeting_id,
            speaker_name=source_segment.speaker.name
            if source_segment and source_segment.speaker
            else None,
        )
        await create_action_item(
            session,
            meeting_id=meeting_id,
            text=item_draft.text,
            assignee_id=assignee_id,
            due_date=item_draft.due_date,
            source_segment_id=item_draft.source_segment_id,
        )

    job.status = "succeeded"
    job.stage = None
    await session.commit()
