"""Live recording upload. Accepts audio captured in the browser (MediaRecorder),
stores it, and kicks off transcription as a background job — the client polls
GET /api/jobs/{id}, the exact same shape every other async ingest job uses
(docs/ARCHITECTURE.md §6.4, §14).
"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SessionLocal, get_session
from app.core.errors import NotFoundError
from app.core.limiter import limiter
from app.models import Job
from app.routers.meetings import DEMO_OWNER_ID
from app.schemas.job import JobOut
from app.services.recordings import create_recording_job, process_recording_job

router = APIRouter(prefix="/api", tags=["recordings"])
settings = get_settings()


async def _run_job_in_background(job_id: str) -> None:
    # A fresh session because the request's session is closed by the time a
    # BackgroundTask runs — exactly the boundary that makes swapping this for a
    # real worker process (Celery/RQ) later a change of caller only.
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is not None:
            await process_recording_job(session, job=job)


@router.post("/recordings", response_model=JobOut, status_code=202)
@limiter.limit(settings.rate_limit_ai)
async def upload_recording(
    request: Request,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    title: str = Form(default="Untitled recording"),
    session: AsyncSession = Depends(get_session),
) -> JobOut:
    media_dir = Path(settings.media_storage_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(audio.filename or "recording.webm").suffix or ".webm"
    audio_path = media_dir / f"{uuid.uuid4()}{ext}"
    audio_path.write_bytes(await audio.read())

    job = await create_recording_job(
        session, owner_id=DEMO_OWNER_ID, audio_path=str(audio_path), title=title
    )
    background_tasks.add_task(_run_job_in_background, job.id)
    return JobOut.model_validate(job)


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)) -> JobOut:
    job = await session.get(Job, job_id)
    if job is None:
        raise NotFoundError("job", job_id)
    return JobOut.model_validate(job)
