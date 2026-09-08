# Meeting Notes & Transcription Platform (Fireflies.ai Clone)

Scaler SDE Fullstack Assignment — Shyam Narayan Nayak. Full design rationale, schema,
and scaling path live in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); this file is
the practical setup guide plus a summary of what's actually built and verified.

## Stack

- **Frontend** — Next.js 16 (App Router, TypeScript, Tailwind v4)
- **Backend** — FastAPI, SQLAlchemy 2.0 (async), Alembic
- **Database** — SQLite (WAL mode) locally, Postgres (Supabase) in the deployed
  environment — the same code runs against either; see ADR-006 in `docs/ARCHITECTURE.md`
- **Search** — SQLite FTS5 locally, Postgres `tsvector`/GIN in production, behind one
  `SearchBackend` seam
- **Testing** — pytest (backend) + Playwright (e2e), `ruff` + `mypy` + `import-linter`
- **CI/CD** — GitHub Actions (`.github/workflows/ci.yml`); Vercel (frontend) + Render
  (backend)

## What's built

Everything below has been exercised over real HTTP against real running servers, not
just written and assumed correct — see `docs/ARCHITECTURE.md` §6.2 and §10 for exactly
what was verified and how.

- Meetings list + detail, cursor pagination, tag filtering
- Ingest: file upload and pasted transcript text, both async via a job/poll pipeline
- Live recording: browser mic capture (`MediaRecorder`) → upload → the same job pipeline
- Transcript view with click-to-seek, virtual playback clock when there's no real media
- Summary, chapters, notes (seeded; not yet LLM-generated on ingest — see Assumptions)
- Action items: full CRUD, complete-and-sort-to-bottom
- Global full-text search (⌘K command palette wired to it) and per-transcript search
- Tags, comments, highlights, soundbites — get-or-create tags, clamped highlight ranges
- Export a meeting to Markdown or plain text
- Dark / light / system theme toggle, persisted per-browser, no flash of the wrong theme
- RAG "ask this meeting" chat with citations (§9.2)

Not built (see `docs/ARCHITECTURE.md` §6.2, §13 for the full list): `PATCH`/`DELETE` on
a meeting, `ETag`/`304` revalidation, and automatic summarization on ingest — summary
and chapters are currently seed-time content only.

## Seed data

All seeded meetings are **fictional** — an invented company ("Solstice Analytics"),
invented people, and invented figures. They're written to match the cadence of real
startup standups and pitch calls without containing any real one. See
`docs/ARCHITECTURE.md` §1 for why.

## Running locally

### Backend

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m app.seed.seed   # idempotent — safe to re-run
uvicorn app.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`. Health check at `/healthz`.

### Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

App at `http://localhost:3000`.

## Testing

```bash
# Backend — from backend/
ruff check .
mypy app
lint-imports          # layering rule: routers -> services -> repositories
pytest -v             # 45 tests

# Frontend — from frontend/
npx tsc --noEmit
npm run lint
npm run build

# End-to-end (needs both servers already running, per "Running locally" above)
npm run test:e2e
```

CI runs all of the above on every push/PR — see `.github/workflows/ci.yml`.

## Deployment

The backend targets **Render** (`render.yaml` in the repo root) against a **Supabase
Postgres** project; the frontend targets **Vercel** (`frontend/vercel.json`). See
`docs/ARCHITECTURE.md` §11 for the full plan — connection string format, environment
variables, health checks, and why Postgres was chosen for the deployed environment over
SQLite-on-a-disk.

Practical steps:

1. **Database** — provision (or reuse) a Supabase project; grab its Postgres connection
   string and prefix the driver: `postgresql+asyncpg://...`.
2. **Backend (Render)** — new Web Service from this repo, root directory `backend`;
   Render picks up `render.yaml`. Set `DATABASE_URL` to the string from step 1,
   `OPENAI_API_KEY` if the LLM summarizer/RAG chat should be live, and once the frontend
   is deployed, `CORS_ORIGINS` to `["https://<your-app>.vercel.app"]`.
3. **Frontend (Vercel)** — import this repo, root directory `frontend`; Vercel picks up
   `vercel.json`. Set `NEXT_PUBLIC_API_URL` to the Render service's URL from step 2.
4. Redeploy the backend once the Vercel URL is known, so `CORS_ORIGINS` is correct.

The Render free tier cold-starts in ~50s after idling — expected, not a broken link.

## Assumptions and known limitations

- **Auth is mocked.** Every request acts as a single demo owner (`DEMO_OWNER_ID`); the
  schema is already multi-tenant-shaped (`owner_id` on every root table, leading every
  index) so real auth is additive, not a rewrite — see `docs/ARCHITECTURE.md` §12.
- **Summaries and chapters are seed-time content**, not generated automatically when a
  meeting is ingested. The summarizer itself is built and swappable
  (`summarizer_backend: "seeded" | "heuristic" | "llm"`) but isn't yet wired to fire on
  ingest completion.
- **Real transcript source files were not available during development**; the parser
  registry, normaliser, and scrubber were built and tested against representative
  formats and fixtures rather than the assignment's own reference files.
- **Live transcription (`transcriber_backend: "openai"`) requires an `OPENAI_API_KEY`**;
  without one, live recording still captures and uploads audio, but the job fails
  loudly with a clear error rather than silently producing no transcript.
- **Export supports Markdown and plain text**, not PDF — PDF generation is a real
  library dependency, not a from-scratch feature, and wasn't prioritized within the
  assignment's time budget.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for: the full data model and why
each table is shaped the way it is, the ingest pipeline design, the complete API
surface with what's built vs. not, the transcript↔player sync algorithm, the AI/RAG
layer, the testing strategy (including a real bug this pass's test suite caught and
fixed — see §10), the deployment plan, and the scaling path.
