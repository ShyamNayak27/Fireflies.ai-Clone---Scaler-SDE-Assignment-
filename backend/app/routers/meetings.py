"""HTTP only. Routers never touch a Session's SQL surface directly, and never
raise a raw HTTPException for domain errors — those are handled centrally via
core/errors.py so every error response has the same problem+json shape.

Caching lives at this layer, not in services/ — the cache stores the finished
Pydantic response, never an ORM object (an ORM instance is tied to the session
that loaded it and is unsafe to hand back once that session closes). See
docs/ARCHITECTURE.md §13.3 for the CacheBackend seam this reads and writes through.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache, invalidate_meeting_caches
from app.core.config import get_settings
from app.core.db import SessionLocal, get_session
from app.core.limiter import limiter
from app.models import Job
from app.schemas.job import JobOut
from app.schemas.meeting import (
    ActionItemCreate,
    ActionItemOut,
    AskCitationOut,
    AskRequest,
    AskResponse,
    MeetingDetail,
    MeetingListItem,
    MeetingListResponse,
    MeetingUpdate,
    ParticipantOut,
    SegmentOut,
    SummaryOut,
    TagOut,
    TranscriptResponse,
)
from app.services import action_items as action_items_service
from app.services import ask as ask_service
from app.services import meetings as meetings_service
from app.services import summarize as summarize_service
from app.services import summary as summary_service
from app.services import tags as tags_service

router = APIRouter(prefix="/api/meetings", tags=["meetings"])
settings = get_settings()

# Single-seeded-user demo (see docs/ARCHITECTURE.md §1 non-goals — real auth is
# explicitly out of scope). Swapping this for a real `current_user` dependency
# does not touch anything below it, because owner_id is already threaded through
# every repository call.
DEMO_OWNER_ID = 1


@router.get("", response_model=MeetingListResponse)
@limiter.limit(settings.rate_limit_default)
async def list_meetings(
    request: Request,
    cursor: str | None = None,
    limit: int = Query(default=20, le=100),
    tag: str | None = None,
    q: str | None = None,
    participant: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: str = Query(default="recent", pattern="^(recent|oldest)$"),
    session: AsyncSession = Depends(get_session),
) -> MeetingListResponse:
    cache_key = (
        f"meetings:list:{DEMO_OWNER_ID}:{cursor}:{limit}:{tag}:{q}:{participant}:"
        f"{date_from}:{date_to}:{sort}"
    )
    if (hit := cache.get(cache_key)) is not None:
        return hit  # type: ignore[return-value]

    items, next_cursor = await meetings_service.list_meetings_page(
        session,
        owner_id=DEMO_OWNER_ID,
        cursor=cursor,
        limit=limit,
        tag=tag,
        q=q,
        participant=participant,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )
    tags_by_meeting = await meetings_service.tags_for_meetings(session, meetings=items)
    response = MeetingListResponse(
        items=[
            MeetingListItem(
                id=m.id,
                title=m.title,
                started_at=m.started_at,
                duration_ms=m.duration_ms,
                status=m.status,
                participants=[ParticipantOut.model_validate(p) for p in m.participants],
                tags=[TagOut.model_validate(t) for t in tags_by_meeting.get(m.id, [])],
            )
            for m in items
        ],
        next_cursor=next_cursor,
    )
    cache.set(cache_key, response, settings.cache_ttl_seconds)
    return response


@router.get("/{meeting_id}", response_model=MeetingDetail)
@limiter.limit(settings.rate_limit_default)
async def get_meeting(
    request: Request, meeting_id: int, session: AsyncSession = Depends(get_session)
) -> MeetingDetail:
    cache_key = f"meetings:detail:{meeting_id}"
    if (hit := cache.get(cache_key)) is not None:
        return hit  # type: ignore[return-value]

    meeting = await meetings_service.get_meeting_or_404(session, meeting_id)
    meeting_tags = await tags_service.list_tags_for_meeting(session, meeting_id=meeting_id)
    response = MeetingDetail(
        id=meeting.id,
        title=meeting.title,
        started_at=meeting.started_at,
        duration_ms=meeting.duration_ms,
        status=meeting.status,
        participants=[ParticipantOut.model_validate(p) for p in meeting.participants],
        tags=[TagOut.model_validate(t) for t in meeting_tags],
        description=meeting.description,
        media_url=meeting.media_url,
        media_type=meeting.media_type,
        timestamps_estimated=meeting.timestamps_estimated,
    )
    cache.set(cache_key, response, settings.cache_ttl_seconds)
    return response


@router.patch("/{meeting_id}", response_model=MeetingDetail)
@limiter.limit(settings.rate_limit_write)
async def update_meeting(
    request: Request, meeting_id: int, body: MeetingUpdate, session: AsyncSession = Depends(get_session)
) -> MeetingDetail:
    meeting = await meetings_service.update_meeting(
        session, meeting_id=meeting_id, title=body.title, description=body.description
    )
    meeting_tags = await tags_service.list_tags_for_meeting(session, meeting_id=meeting_id)
    invalidate_meeting_caches(meeting_id)
    return MeetingDetail(
        id=meeting.id,
        title=meeting.title,
        started_at=meeting.started_at,
        duration_ms=meeting.duration_ms,
        status=meeting.status,
        participants=[ParticipantOut.model_validate(p) for p in meeting.participants],
        tags=[TagOut.model_validate(t) for t in meeting_tags],
        description=meeting.description,
        media_url=meeting.media_url,
        media_type=meeting.media_type,
        timestamps_estimated=meeting.timestamps_estimated,
    )


@router.delete("/{meeting_id}", status_code=204)
@limiter.limit(settings.rate_limit_write)
async def delete_meeting(
    request: Request, meeting_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    await meetings_service.delete_meeting(session, meeting_id=meeting_id)
    invalidate_meeting_caches(meeting_id)
    return Response(status_code=204)


@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse)
@limiter.limit(settings.rate_limit_default)
async def get_transcript(
    request: Request,
    meeting_id: int,
    cursor: str | None = None,
    limit: int = Query(default=200, le=500),
    session: AsyncSession = Depends(get_session),
) -> TranscriptResponse:
    cache_key = f"meetings:transcript:{meeting_id}:{cursor}:{limit}"
    if (hit := cache.get(cache_key)) is not None:
        return hit  # type: ignore[return-value]

    items, next_cursor = await meetings_service.get_transcript_page(
        session, meeting_id=meeting_id, cursor=cursor, limit=limit
    )
    response = TranscriptResponse(
        items=[SegmentOut.model_validate(s) for s in items], next_cursor=next_cursor
    )
    cache.set(cache_key, response, settings.cache_ttl_seconds)
    return response


@router.get("/{meeting_id}/summary", response_model=SummaryOut)
@limiter.limit(settings.rate_limit_default)
async def get_summary(
    request: Request, meeting_id: int, session: AsyncSession = Depends(get_session)
) -> SummaryOut:
    cache_key = f"meetings:summary:{meeting_id}"
    if (hit := cache.get(cache_key)) is not None:
        return hit  # type: ignore[return-value]

    response = await summary_service.get_summary_or_404(session, meeting_id=meeting_id)
    cache.set(cache_key, response, settings.cache_ttl_seconds)
    return response


@router.get("/{meeting_id}/action-items", response_model=list[ActionItemOut])
@limiter.limit(settings.rate_limit_default)
async def list_action_items(
    request: Request, meeting_id: int, session: AsyncSession = Depends(get_session)
) -> list[ActionItemOut]:
    cache_key = f"meetings:action_items:{meeting_id}"
    if (hit := cache.get(cache_key)) is not None:
        return hit  # type: ignore[return-value]

    items = await action_items_service.list_action_items(session, meeting_id=meeting_id)
    response = [ActionItemOut.model_validate(item) for item in items]
    cache.set(cache_key, response, settings.cache_ttl_seconds)
    return response


async def _run_summarize_job_in_background(job_id: str, meeting_id: int) -> None:
    # Fresh session — the request's session is closed by the time a
    # BackgroundTask runs, same boundary as recordings/ingest.
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is not None:
            await summarize_service.process_summarize_job(session, job=job)
    # The summary/action-items caches (§13.3) would otherwise stay stale for up
    # to cache_ttl_seconds after a background job finishes — unlike a
    # synchronous write, nothing else touches the cache on this path.
    invalidate_meeting_caches(meeting_id)


@router.post("/{meeting_id}/summarize", response_model=JobOut, status_code=202)
@limiter.limit(settings.rate_limit_ai)
async def summarize_meeting(
    request: Request,
    meeting_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> JobOut:
    await meetings_service.get_meeting_or_404(session, meeting_id)
    job = await summarize_service.create_summarize_job(session, meeting_id=meeting_id)
    background_tasks.add_task(_run_summarize_job_in_background, job.id, meeting_id)
    return JobOut.model_validate(job)


@router.post("/{meeting_id}/ask", response_model=AskResponse)
@limiter.limit(settings.rate_limit_ai)
async def ask_meeting(
    request: Request,
    meeting_id: int,
    body: AskRequest,
    session: AsyncSession = Depends(get_session),
) -> AskResponse:
    result = await ask_service.ask_meeting(session, meeting_id=meeting_id, question=body.question)
    return AskResponse(
        answer=result.answer,
        citations=[
            AskCitationOut(number=c.number, segment_id=c.segment_id, start_ms=c.start_ms)
            for c in result.citations
        ],
        model=result.model,
    )


@router.post("/{meeting_id}/action-items", response_model=ActionItemOut, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def create_action_item(
    request: Request,
    meeting_id: int,
    body: ActionItemCreate,
    session: AsyncSession = Depends(get_session),
) -> ActionItemOut:
    item = await action_items_service.create_action_item(
        session,
        meeting_id=meeting_id,
        text=body.text,
        assignee_id=body.assignee_id,
        due_date=body.due_date,
        source_segment_id=body.source_segment_id,
    )
    invalidate_meeting_caches(meeting_id)
    return ActionItemOut.model_validate(item)
