"""Turns an uploaded audio recording into a meeting. Live recording is treated as
just another ingest source (docs/ARCHITECTURE.md §5, §14) — it produces the exact
same Meeting/Participant/TranscriptSegment rows a pasted transcript would, so
every downstream feature (search, summary, transcript UI) needs no special case
for "a meeting that came from a live recording".
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.transcriber import Transcriber, TranscriptionUnavailable, get_transcriber
from app.models import Job, Meeting, Participant, TranscriptSegment
from app.seed.seed import avatar_color_for


async def create_recording_job(
    session: AsyncSession, *, owner_id: int, audio_path: str, title: str
) -> Job:
    job = Job(id=str(uuid.uuid4()), type="ingest", status="queued", payload=json.dumps(
        {"audio_path": audio_path, "title": title, "owner_id": owner_id}
    ))
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def process_recording_job(
    session: AsyncSession, *, job: Job, transcriber: Transcriber | None = None
) -> None:
    """Runs the transcription and, on success, materializes the meeting. Designed
    to run inline via BackgroundTasks today; the job row is what makes moving this
    to a real worker process later a change of caller, not of this function."""
    transcriber = transcriber or get_transcriber()
    payload = json.loads(job.payload or "{}")

    job.status = "running"
    job.stage = "transcribing"
    await session.commit()

    try:
        result = await transcriber.transcribe(payload["audio_path"])
    except TranscriptionUnavailable as exc:
        job.status = "failed"
        job.error = str(exc)
        await session.commit()
        return
    except Exception as exc:  # noqa: BLE001 — any transcription failure surfaces as a job error
        job.status = "failed"
        job.error = f"Transcription failed: {exc}"
        await session.commit()
        return

    meeting = Meeting(
        owner_id=payload["owner_id"],
        title=payload["title"],
        started_at=datetime.now(UTC).isoformat(),
        duration_ms=result.duration_ms,
        media_url=payload["audio_path"],
        media_type="audio",
        source="upload",
        status="ready",
    )
    session.add(meeting)
    await session.flush()

    speaker = Participant(
        meeting_id=meeting.id, name="You", avatar_color=avatar_color_for("You"), is_host=True
    )
    session.add(speaker)
    await session.flush()

    for idx, utt in enumerate(result.utterances):
        session.add(
            TranscriptSegment(
                meeting_id=meeting.id,
                idx=idx,
                speaker_id=speaker.id,
                start_ms=utt.start_ms,
                end_ms=utt.end_ms,
                text=utt.text,
            )
        )

    job.status = "succeeded"
    job.stage = None
    job.meeting_id = meeting.id
    await session.commit()
