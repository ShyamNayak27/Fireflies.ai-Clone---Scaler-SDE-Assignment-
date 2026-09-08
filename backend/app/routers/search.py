from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.limiter import limiter
from app.routers.meetings import DEMO_OWNER_ID
from app.schemas.meeting import SearchResponse
from app.services import search as search_service

router = APIRouter(prefix="/api/search", tags=["search"])
settings = get_settings()


@router.get("", response_model=SearchResponse)
@limiter.limit(settings.rate_limit_default)
async def search(
    request: Request,
    q: str = Query(min_length=1),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    hits = await search_service.global_search(session, owner_id=DEMO_OWNER_ID, query=q)
    return SearchResponse(items=hits)
