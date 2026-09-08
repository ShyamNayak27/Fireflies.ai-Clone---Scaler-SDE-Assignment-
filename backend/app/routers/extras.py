"""Milestone 12 bonus features — tags, comments, highlights, soundbites, and
export. Small enough as a group that a dedicated router per resource would be
more ceremony than payload; grouped here rather than bloating routers/meetings.py
further. Same layering rule as everywhere else (docs/ARCHITECTURE.md §6.1):
routers never touch a Session's SQL surface, never raise a raw HTTPException.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_meeting_caches
from app.core.config import get_settings
from app.core.db import get_session
from app.core.limiter import limiter
from app.routers.meetings import DEMO_OWNER_ID
from app.schemas.meeting import (
    CommentCreate,
    CommentOut,
    HighlightCreate,
    HighlightOut,
    SoundbiteCreate,
    SoundbiteOut,
    TagCreate,
    TagOut,
)
from app.services import comments as comments_service
from app.services import highlights as highlights_service
from app.services import soundbites as soundbites_service
from app.services import tags as tags_service
from app.services.export import render_meeting_export

router = APIRouter(prefix="/api", tags=["extras"])
settings = get_settings()


# ---------------------------------------------------------------- tags ----

@router.get("/tags", response_model=list[TagOut])
async def list_all_tags(session: AsyncSession = Depends(get_session)) -> list[TagOut]:
    return [TagOut.model_validate(t) for t in await tags_service.list_all_tags(session)]


@router.post("/meetings/{meeting_id}/tags", response_model=TagOut, status_code=201)
@limiter.limit(settings.rate_limit_default)
async def add_tag(
    request: Request, meeting_id: int, body: TagCreate, session: AsyncSession = Depends(get_session)
) -> TagOut:
    tag = await tags_service.add_tag(session, meeting_id=meeting_id, name=body.name)
    invalidate_meeting_caches(meeting_id)
    return TagOut.model_validate(tag)


@router.delete("/meetings/{meeting_id}/tags/{tag_id}", status_code=204)
async def remove_tag(meeting_id: int, tag_id: int, session: AsyncSession = Depends(get_session)) -> Response:
    await tags_service.remove_tag(session, meeting_id=meeting_id, tag_id=tag_id)
    invalidate_meeting_caches(meeting_id)
    return Response(status_code=204)


# ------------------------------------------------------------- comments ----

@router.get("/meetings/{meeting_id}/comments", response_model=list[CommentOut])
async def list_comments(meeting_id: int, session: AsyncSession = Depends(get_session)) -> list[CommentOut]:
    return [CommentOut.model_validate(c) for c in await comments_service.list_comments(session, meeting_id=meeting_id)]


@router.post("/segments/{segment_id}/comments", response_model=CommentOut, status_code=201)
@limiter.limit(settings.rate_limit_default)
async def add_comment(
    request: Request, segment_id: int, body: CommentCreate, session: AsyncSession = Depends(get_session)
) -> CommentOut:
    comment = await comments_service.add_comment(
        session, segment_id=segment_id, user_id=DEMO_OWNER_ID, body=body.body
    )
    return CommentOut.model_validate(comment)


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(comment_id: int, session: AsyncSession = Depends(get_session)) -> Response:
    meeting_id = await comments_service.delete_comment(session, comment_id=comment_id)
    invalidate_meeting_caches(meeting_id)
    return Response(status_code=204)


# ------------------------------------------------------------ highlights ----

@router.get("/meetings/{meeting_id}/highlights", response_model=list[HighlightOut])
async def list_highlights(meeting_id: int, session: AsyncSession = Depends(get_session)) -> list[HighlightOut]:
    return [
        HighlightOut.model_validate(h)
        for h in await highlights_service.list_highlights(session, meeting_id=meeting_id)
    ]


@router.post("/segments/{segment_id}/highlights", response_model=HighlightOut, status_code=201)
@limiter.limit(settings.rate_limit_default)
async def add_highlight(
    request: Request, segment_id: int, body: HighlightCreate, session: AsyncSession = Depends(get_session)
) -> HighlightOut:
    highlight = await highlights_service.add_highlight(
        session,
        segment_id=segment_id,
        user_id=DEMO_OWNER_ID,
        color=body.color,
        start_offset=body.start_offset,
        end_offset=body.end_offset,
    )
    return HighlightOut.model_validate(highlight)


@router.delete("/highlights/{highlight_id}", status_code=204)
async def delete_highlight(highlight_id: int, session: AsyncSession = Depends(get_session)) -> Response:
    meeting_id = await highlights_service.delete_highlight(session, highlight_id=highlight_id)
    invalidate_meeting_caches(meeting_id)
    return Response(status_code=204)


# ------------------------------------------------------------ soundbites ----

@router.get("/meetings/{meeting_id}/soundbites", response_model=list[SoundbiteOut])
async def list_soundbites(meeting_id: int, session: AsyncSession = Depends(get_session)) -> list[SoundbiteOut]:
    return [
        SoundbiteOut.model_validate(s)
        for s in await soundbites_service.list_soundbites(session, meeting_id=meeting_id)
    ]


@router.post("/meetings/{meeting_id}/soundbites", response_model=SoundbiteOut, status_code=201)
@limiter.limit(settings.rate_limit_default)
async def add_soundbite(
    request: Request, meeting_id: int, body: SoundbiteCreate, session: AsyncSession = Depends(get_session)
) -> SoundbiteOut:
    soundbite = await soundbites_service.add_soundbite(
        session, meeting_id=meeting_id, title=body.title, start_ms=body.start_ms, end_ms=body.end_ms
    )
    invalidate_meeting_caches(meeting_id)
    return SoundbiteOut.model_validate(soundbite)


@router.delete("/soundbites/{soundbite_id}", status_code=204)
async def delete_soundbite(soundbite_id: int, session: AsyncSession = Depends(get_session)) -> Response:
    meeting_id = await soundbites_service.delete_soundbite(session, soundbite_id=soundbite_id)
    invalidate_meeting_caches(meeting_id)
    return Response(status_code=204)


# ---------------------------------------------------------------- export ----

@router.get("/meetings/{meeting_id}/export")
@limiter.limit(settings.rate_limit_default)
async def export_meeting(
    request: Request, meeting_id: int, format: Literal["md", "txt"] = "md", session: AsyncSession = Depends(get_session)
) -> Response:
    content, filename = await render_meeting_export(session, meeting_id=meeting_id, fmt=format)
    media_type = "text/markdown" if format == "md" else "text/plain"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
