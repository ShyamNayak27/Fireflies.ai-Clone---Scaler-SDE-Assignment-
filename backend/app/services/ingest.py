"""Turns an uploaded/pasted transcript into a meeting — the text-based sibling
of `app/services/recordings.py`'s audio path (docs/ARCHITECTURE.md §5). Same
Job lifecycle, same "materialize Meeting/Participant/TranscriptSegment on
success" shape, so every downstream feature still needs no special case for
"a meeting that came from ingest" vs. "a meeting that came from a recording".
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.parsers import IngestParseError, NoParserMatchedError
from app.ingest.pipeline import run_ingest_pipeline
from app.models import Job, Meeting, Participant, TranscriptSegment


async def create_ingest_job(
    session: AsyncSession, *, owner_id: int, raw_text: str, filename: str, title: str, source: str
) -> Job:
    job = Job(
        id=str(uuid.uuid4()),
        type="ingest",
        status="queued",
        payload=json.dumps(
            {
                "raw_text": raw_text,
                "filename": filename,
                "title": title,
                "owner_id": owner_id,
                "source": source,
            }
        ),
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def process_ingest_job(session: AsyncSession, *, job: Job) -> None:
    """Runs the parse/normalize/scrub pipeline and, on success, materializes
    the meeting. Same BackgroundTasks-today / real-worker-later boundary as
    `process_recording_job`."""
    payload = json.loads(job.payload or "{}")

    job.status = "running"
    job.stage = "parsing"
    await session.commit()

    try:
        result = run_ingest_pipeline(payload["raw_text"], payload["filename"])
    except (IngestParseError, NoParserMatchedError) as exc:
        job.status = "failed"
        job.error = str(exc)
        await session.commit()
        return
    except Exception as exc:  # noqa: BLE001 — any pipeline failure surfaces as a job error
        job.status = "failed"
        job.error = f"Ingest failed: {exc}"
        await session.commit()
        return

    if not result.segments:
        job.status = "failed"
        job.error = "No speech could be extracted from this transcript."
        await session.commit()
        return

    job.stage = "materializing"
    await session.commit()

    meeting = Meeting(
        owner_id=payload["owner_id"],
        title=payload["title"],
        started_at=datetime.now(UTC).isoformat(),
        duration_ms=result.segments[-1].end_ms,
        media_url=None,
        media_type=None,
        source=payload["source"],
        status="ready",
        timestamps_estimated=result.timestamps_estimated,
    )
    session.add(meeting)
    await session.flush()

    participants_by_label: dict[str, Participant] = {}
    for seg in result.segments:
        if seg.speaker_label not in participants_by_label:
            participant = Participant(
                meeting_id=meeting.id,
                name=seg.speaker_label,
                avatar_color=seg.avatar_color,
                is_host=False,
            )
            session.add(participant)
            participants_by_label[seg.speaker_label] = participant
    await session.flush()

    for idx, seg in enumerate(result.segments):
        session.add(
            TranscriptSegment(
                meeting_id=meeting.id,
                idx=idx,
                speaker_id=participants_by_label[seg.speaker_label].id,
                start_ms=seg.start_ms,
                end_ms=seg.end_ms,
                text=seg.text,
            )
        )

    job.status = "succeeded"
    job.stage = None
    job.meeting_id = meeting.id
    await session.commit()
