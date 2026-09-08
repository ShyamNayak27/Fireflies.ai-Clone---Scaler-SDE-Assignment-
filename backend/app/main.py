from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.errors import register_exception_handlers
from app.core.limiter import limiter
from app.core.logging import RequestIdMiddleware, configure_logging
from app.routers import action_items, extras, ingest, meetings, recordings, search
from app.seed.seed import seed

settings = get_settings()

# Sentry is entirely optional: with no DSN configured this block never runs, so
# the app behaves identically whether or not error tracking is wired up — see
# docs/ARCHITECTURE.md §13.4.
if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.1)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    # Idempotent: only inserts if the meetings table is empty. Safe to run on
    # every boot, which is what makes a Render restart never duplicate data —
    # see docs/ARCHITECTURE.md §11.
    async with SessionLocal() as session:
        await seed(session)
    yield


app = FastAPI(title="Meeting Notes & Transcription Platform API", lifespan=lifespan)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(_req: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        media_type="application/problem+json",
        content={
            "type": "/problems/rate-limited",
            "title": "Too Many Requests",
            "status": 429,
            "detail": f"Rate limit exceeded: {exc.detail}",
        },
    )


app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(meetings.router)
app.include_router(action_items.router)
app.include_router(search.router)
app.include_router(recordings.router)
app.include_router(ingest.router)
app.include_router(extras.router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
