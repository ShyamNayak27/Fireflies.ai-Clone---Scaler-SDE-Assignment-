"""Transcript ingest upload (docs/ARCHITECTURE.md §5, §6.4). Accepts either an
uploaded file (.vtt/.srt/.txt) or pasted text, auto-detects the format, and
kicks off parsing/normalization/scrubbing as a background job — the client
polls the exact same `GET /api/jobs/{id}` every other async ingest job uses
(recordings included). Exactly one of `file` / `text` must be given.
"""
from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SessionLocal, get_session
from app.core.limiter import limiter
from app.models import Job
from app.routers.meetings import DEMO_OWNER_ID
from app.schemas.job import JobOut
from app.services.ingest import create_ingest_job, process_ingest_job

router = APIRouter(prefix="/api", tags=["ingest"])
settings = get_settings()


async def _run_job_in_background(job_id: str) -> None:
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is not None:
            await process_ingest_job(session, job=job)


@router.post("/meetings/ingest", response_model=JobOut, status_code=202)
@limiter.limit(settings.rate_limit_ai)
async def ingest_transcript(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    title: str = Form(default="Untitled meeting"),
    session: AsyncSession = Depends(get_session),
) -> JobOut:
    if file is None and not text:
        raise HTTPException(422, "Provide either a file upload or pasted text.")
    if file is not None and text:
        raise HTTPException(422, "Provide only one of file upload or pasted text, not both.")

    if file is not None:
        raw_bytes = await file.read()
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        filename = file.filename or "upload.txt"
        source = "upload"
    else:
        raw_text = text or ""
        filename = "pasted-transcript.txt"
        source = "paste"

    if not raw_text.strip():
        raise HTTPException(422, "The transcript is empty.")

    job = await create_ingest_job(
        session, owner_id=DEMO_OWNER_ID, raw_text=raw_text, filename=filename, title=title, source=source
    )
    background_tasks.add_task(_run_job_in_background, job.id)
    return JobOut.model_validate(job)
