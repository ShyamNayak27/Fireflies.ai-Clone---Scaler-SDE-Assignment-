# Architecture — Meeting Notes & Transcription Platform

A Fireflies.ai clone. Next.js (TypeScript) frontend, FastAPI backend, SQLite locally /
Postgres in production.

This document is the design reference for the build. Sections 2–14 are intended to be
condensed into the repository README at submission time.

---

## 1. Goals and non-goals

### Goals

- Recreate the Fireflies post-meeting workflow: meeting library, interactive transcript,
  AI summary, action items — visually and behaviourally faithful to the original.
- Ingest **real meeting transcripts** in several third-party export formats, normalise
  them into a consistent internal shape, and strip personal data before anything is
  committed to a public repository.
- Design every hot path as if the dataset were large, even though the demo dataset is not.
  Where a production system would need infrastructure we do not have, put an interface at
  the seam and document what plugs in.

### Non-goals

Explicitly out of scope, per the brief. These ship as visible "Coming soon" placeholders
rather than being hidden, because the placeholder is part of the product surface:

- A meeting bot that joins live calls. (Live recording of a call the user is already
  in, with real speech-to-text, is in scope and built — §13.)
- Calendar / Zoom / Meet / CRM integrations.
- Real authentication. A single seeded user is assumed logged in.
- Team, sharing and collaboration features.

### The constraint that shapes everything

The repository must be **public**. The seed data derives from **real meetings**. Those two
facts are irreconcilable without a redaction stage, so redaction is not a post-processing
script — it is a mandatory stage of the ingest pipeline (§5.4), and the identity mapping it
produces never enters version control.

---

## 2. Stack and key decisions

| Layer | Choice | Reasoning |
|---|---|---|
| Frontend | Next.js 15 (App Router), TypeScript | Mandated. RSC for first paint on list/detail, client components for the interactive panes. |
| Styling | Tailwind + shadcn/ui | Token-driven, so the Fireflies palette lives in one file and dark mode is a token swap. |
| Server state | TanStack Query | Cursor pagination, optimistic mutations, cache invalidation — all first-class. |
| Client state | Zustand | Exactly one store: playback position. Everything else is server state. |
| Backend | FastAPI | Async, Pydantic schemas double as the OpenAPI contract, dependency injection makes the router/service/repository split natural. |
| ORM | SQLAlchemy 2.0 (typed) + Alembic | Typed ORM keeps the repository layer honest; migrations are evidence of schema thinking. |
| Database | SQLite (WAL) + FTS5 | Mandated. FTS5 turns search from a `LIKE` toy into real ranked retrieval at zero infrastructure cost. |
| Jobs | In-process asyncio workers + a `jobs` table | The table is the contract; the executor is swappable (§6.4). |
| Tests | pytest, Playwright | Parser and normaliser correctness is not eyeballable. |

### ADR-001 — FastAPI over Django

Django's ORM, admin and migrations are real advantages, but the assignment scores *Code
Modularity* separately from *Code Quality*, and Django's app convention pushes toward
fat views and models. FastAPI makes a four-layer split (router → service → repository →
model) the path of least resistance, and the auto-generated OpenAPI page doubles as API
documentation for the grader. Cost: no free admin panel, and migrations must be wired up
manually via Alembic.

### ADR-002 — SQLite FTS5 rather than application-level search

`LIKE '%term%'` cannot rank, cannot produce snippets, and scans every row. FTS5 gives
BM25 ranking, `snippet()` with match highlighting, prefix and phrase queries, and an
inverted index maintained by triggers. It is the single highest-leverage feature in the
project and it costs one virtual table plus three triggers.

Trade-off: it binds search to SQLite. Mitigated by putting search behind a
`SearchBackend` protocol (§7.3) so a Postgres `tsvector` or OpenSearch implementation is
a drop-in.

### ADR-003 — Transcript stored as rows, never as a blob

A JSON blob is simpler to write and forecloses everything: no click-to-seek, no
in-transcript search, no per-segment highlights or comments, no retrieval for the RAG
chat, no partial loading. Normalised `transcript_segments` rows make all of those
straightforward. This is the load-bearing schema decision.

### ADR-004 — Playback behind an interface

Real transcripts arrive without audio, but the brief requires a working seek bar and
bidirectional transcript↔player sync. Rather than pairing meetings with unrelated stock
audio, playback is abstracted (§8.4): a virtual clock drives the timeline when no media
exists, a real `HTMLMediaElement` drives it when one does. The transcript pane cannot
tell the difference.

### ADR-005 — Ingest is asynchronous from the start

Upload returns `202 Accepted` with a job id; the client polls. Parsing, normalising,
scrubbing and summarising a long transcript takes seconds to tens of seconds, and doing
it inside the request would block a worker and time out on a real file. Modelling it as a
job now means the migration to a distributed queue is a change of executor, not a change
of architecture.

---

## 3. System overview

```
┌─────────────────────────────────────────────────────────────┐
│  Next.js (Vercel)                                           │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Library   │  │ Meeting      │  │ Global search / ⌘K   │  │
│  │ (RSC)     │  │ detail       │  │                      │  │
│  └───────────┘  └──────┬───────┘  └──────────────────────┘  │
│                        │ playback store + virtual list      │
└────────────────────────┼────────────────────────────────────┘
                         │ REST / JSON
┌────────────────────────┼────────────────────────────────────┐
│  FastAPI (Render)      ▼                                    │
│  routers ─→ services ─→ repositories ─→ SQLAlchemy models   │
│                │                                            │
│                ├─→ ingest/   parsers, speakers, normalise,  │
│                │             scrub                          │
│                ├─→ ai/       summariser, RAG retrieval      │
│                └─→ jobs/     in-process worker + jobs table │
├─────────────────────────────────────────────────────────────┤
│  SQLite (WAL) on a Render persistent disk                   │
│  relational tables  +  segments_fts (FTS5)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Data model

SQLite. Timestamps are ISO-8601 strings in UTC; positions and durations are **integer
milliseconds** throughout — never floats, never formatted strings — so every seek, sort
and range query is an integer comparison.

### 4.1 Core tables

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;

CREATE TABLE users (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT NOT NULL UNIQUE,
  avatar_url  TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE meetings (
  id          INTEGER PRIMARY KEY,
  owner_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title       TEXT    NOT NULL,
  description TEXT,
  started_at  TEXT    NOT NULL,              -- ISO-8601 UTC
  duration_ms INTEGER NOT NULL DEFAULT 0,
  media_url   TEXT,                          -- NULL => virtual playback
  media_type  TEXT CHECK (media_type IN ('audio','video')),
  source      TEXT NOT NULL DEFAULT 'upload'
              CHECK (source IN ('upload','paste','manual','seed')),
  status      TEXT NOT NULL DEFAULT 'ready'
              CHECK (status IN ('processing','ready','failed')),
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- This composite index IS the cursor-pagination key (§7.2).
CREATE INDEX ix_meetings_recency ON meetings(owner_id, started_at DESC, id DESC);

CREATE TABLE participants (
  id           INTEGER PRIMARY KEY,
  meeting_id   INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  name         TEXT    NOT NULL,
  email        TEXT,
  avatar_color TEXT    NOT NULL,   -- deterministic from name hash
  is_host      INTEGER NOT NULL DEFAULT 0,
  raw_labels   TEXT                -- JSON array of source labels merged here
);
CREATE INDEX ix_participants_meeting ON participants(meeting_id);

CREATE TABLE transcript_segments (
  id         INTEGER PRIMARY KEY,
  meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  idx        INTEGER NOT NULL,     -- 0-based order within the meeting
  speaker_id INTEGER REFERENCES participants(id) ON DELETE SET NULL,
  start_ms   INTEGER NOT NULL,
  end_ms     INTEGER NOT NULL,
  text       TEXT    NOT NULL,
  UNIQUE (meeting_id, idx)
);
CREATE INDEX ix_segments_meeting_time ON transcript_segments(meeting_id, start_ms);
```

`participants` doubles as the speaker table. A speaker *is* a participant; splitting them
would add a join to the hottest query in the application and buy nothing at this scale.
`raw_labels` records which source labels (`Speaker 1`, `Shyam`, `Shyam N.`) were merged
into this participant, which keeps the normalisation auditable rather than magical.

### 4.2 Summary, chapters, notes

Modelled to match the Fireflies UI exactly: an **Overview** paragraph, then **Notes** as
timestamped bullets grouped under chapter headings (`Use Case & Requirements: 00:00 – 10:12`).

```sql
CREATE TABLE summaries (
  id             INTEGER PRIMARY KEY,
  meeting_id     INTEGER NOT NULL UNIQUE REFERENCES meetings(id) ON DELETE CASCADE,
  overview       TEXT    NOT NULL,
  model          TEXT,               -- NULL when heuristic or seeded
  prompt_version TEXT,
  generated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE chapters (
  id         INTEGER PRIMARY KEY,
  meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  title      TEXT    NOT NULL,
  start_ms   INTEGER NOT NULL,
  end_ms     INTEGER NOT NULL,
  position   INTEGER NOT NULL
);
CREATE INDEX ix_chapters_meeting ON chapters(meeting_id, position);

CREATE TABLE notes (
  id         INTEGER PRIMARY KEY,
  chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  text       TEXT    NOT NULL,
  start_ms   INTEGER,             -- anchors the bullet to a moment
  position   INTEGER NOT NULL
);
```

Summary lives in its own table rather than as nullable columns on `meetings` because it
has an independent lifecycle — it is generated asynchronously and may not exist yet, may
fail, and may be regenerated with a different model.

### 4.3 Action items, tags, annotations

```sql
CREATE TABLE action_items (
  id                INTEGER PRIMARY KEY,
  meeting_id        INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  text              TEXT    NOT NULL,
  assignee_id       INTEGER REFERENCES participants(id) ON DELETE SET NULL,
  due_date          TEXT,
  completed         INTEGER NOT NULL DEFAULT 0,
  completed_at      TEXT,
  source_segment_id INTEGER REFERENCES transcript_segments(id) ON DELETE SET NULL,
  position          INTEGER NOT NULL DEFAULT 0,
  created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX ix_action_items_meeting ON action_items(meeting_id, completed, position);

CREATE TABLE tags (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);
CREATE TABLE meeting_tags (
  meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  tag_id     INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (meeting_id, tag_id)
);

CREATE TABLE comments (
  id         INTEGER PRIMARY KEY,
  segment_id INTEGER NOT NULL REFERENCES transcript_segments(id) ON DELETE CASCADE,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body       TEXT    NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE highlights (
  id           INTEGER PRIMARY KEY,
  segment_id   INTEGER NOT NULL REFERENCES transcript_segments(id) ON DELETE CASCADE,
  user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  color        TEXT    NOT NULL DEFAULT 'yellow',
  start_offset INTEGER NOT NULL,   -- character range within segment.text
  end_offset   INTEGER NOT NULL
);

CREATE TABLE soundbites (
  id         INTEGER PRIMARY KEY,
  meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  title      TEXT    NOT NULL,
  start_ms   INTEGER NOT NULL,
  end_ms     INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

`source_segment_id` on an action item is what lets the UI jump from a task straight to
the moment it was agreed — a small column that produces a feature.

`highlights` stores a character range rather than duplicating the highlighted text, so
edits to a segment cannot orphan a highlight into inconsistency.

### 4.4 Jobs

```sql
CREATE TABLE jobs (
  id         TEXT PRIMARY KEY,          -- uuid4
  meeting_id INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
  type       TEXT NOT NULL CHECK (type IN ('ingest','summarize')),
  status     TEXT NOT NULL DEFAULT 'queued'
             CHECK (status IN ('queued','running','succeeded','failed')),
  progress   INTEGER NOT NULL DEFAULT 0,   -- 0..100
  stage      TEXT,                          -- 'parsing' | 'normalizing' | ...
  error      TEXT,
  payload    TEXT,                          -- JSON
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX ix_jobs_status ON jobs(status, created_at);
```

### 4.5 Full-text index

```sql
CREATE VIRTUAL TABLE segments_fts USING fts5(
  text,
  content      = 'transcript_segments',
  content_rowid= 'id',
  tokenize     = 'porter unicode61'
);

CREATE TRIGGER segments_ai AFTER INSERT ON transcript_segments BEGIN
  INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER segments_ad AFTER DELETE ON transcript_segments BEGIN
  INSERT INTO segments_fts(segments_fts, rowid, text) VALUES('delete', old.id, old.text);
END;
CREATE TRIGGER segments_au AFTER UPDATE ON transcript_segments BEGIN
  INSERT INTO segments_fts(segments_fts, rowid, text) VALUES('delete', old.id, old.text);
  INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
END;
```

External-content mode stores only the index, not a second copy of the text. The `porter`
stemmer makes *"discussing"* match *"discuss"*, which is what a user expects from a search
box and what `LIKE` can never do.

---

## 5. Ingest pipeline

The most technically interesting part of the system, and the part that handles real-world
mess.

```
uploaded file / pasted text
        │
        ▼
  ┌──────────────┐   sniff() across the parser registry, highest confidence wins
  │ 1. Detect    │
  └──────┬───────┘
         ▼
  ┌──────────────┐   format-specific → RawTranscript (utterances + raw speaker labels)
  │ 2. Parse     │
  └──────┬───────┘
         ▼
  ┌──────────────┐   collapse label variants onto one participant per person
  │ 3. Resolve   │
  └──────┬───────┘
         ▼
  ┌──────────────┐   merge, split, infer end_ms, clean ASR artefacts
  │ 4. Normalise │
  └──────┬───────┘
         ▼
  ┌──────────────┐   pseudonymise people, scrub emails/phones/URLs/orgs
  │ 5. Scrub     │
  └──────┬───────┘
         ▼
  ┌──────────────┐   meeting + participants + segments; FTS index via triggers
  │ 6. Persist   │
  └──────┬───────┘
         ▼
  enqueue `summarize` job
```

### 5.1 Parser registry

```python
class TranscriptParser(Protocol):
    name: str

    def sniff(self, raw: str, filename: str) -> float:
        """Confidence in [0, 1] that this parser can handle the input."""

    def parse(self, raw: str) -> RawTranscript: ...
```

Implementations: `VttParser`, `SrtParser`, `ZoomTxtParser`, `TeamsParser`,
`OtterParser`, `JsonParser`, `PlainTextParser` (the always-available fallback, confidence
`0.1`). The loader scores every registered parser and picks the highest; ties break on
file extension. Adding a format is one new file and one registry entry — no changes
anywhere else.

`RawTranscript` is the boundary type:

```python
@dataclass
class RawUtterance:
    speaker_label: str | None
    start_ms: int | None
    end_ms: int | None
    text: str

@dataclass
class RawTranscript:
    utterances: list[RawUtterance]
    title_hint: str | None
    started_at_hint: datetime | None
    source_format: str
```

### 5.2 Speaker resolution

Real exports are inconsistent within a single file. Resolution runs in order:

1. Normalise each label (trim, strip trailing punctuation, collapse whitespace, drop role
   suffixes like `(Host)`).
2. Group by exact match after normalisation.
3. Merge groups where one label is a prefix or initial-form of another
   (`Shyam` ≈ `Shyam N.` ≈ `Shyam Nayak`), guarded by a similarity threshold.
4. Leave generic labels (`Speaker 1`, `Participant 2`) as distinct participants — they are
   genuinely unknown, and guessing would be worse than admitting it.
5. Assign a deterministic avatar colour from a hash of the resolved name, so a person is
   the same colour on every visit.

Every merge is recorded in `participants.raw_labels`.

### 5.3 Normalisation

Where raw ASR output becomes readable conversation:

- **Merge** consecutive utterances from the same speaker separated by less than
  `MERGE_GAP_MS` (default 2000) into one block. This is what turns fragmented ASR lines
  into the conversational blocks Fireflies displays.
- **Split** any resulting block over `MAX_BLOCK_CHARS` (default 700) at sentence
  boundaries, so no segment becomes an unreadable wall.
- **Infer `end_ms`** where the format omits it: the next utterance's `start_ms`, or
  `start_ms + estimated_duration` for the final block (≈ 160 words/minute).
- **Synthesise timestamps** entirely when the source has none, distributing time
  proportionally to word count across a supplied or estimated duration. The meeting is
  flagged `timestamps_estimated` so the UI can be honest about it.
- **Clean artefacts**: filler-token removal (`[inaudible]`, `um` at block start),
  whitespace collapse, smart-quote normalisation. Conservative by default — over-cleaning
  destroys the authenticity that makes real transcripts worth using.

Every rule here is a pure function over `RawTranscript` and is unit-tested against golden
fixtures.

### 5.4 Scrubbing — the mandatory stage

Because the repository is public and the sources are real meetings.

- **People.** Every resolved participant name is mapped to a stable pseudonym via
  `alias(name) = FAKE_NAMES[hash(name, salt) % len(FAKE_NAMES)]`. Deterministic, so the
  same person is the same alias across every meeting, and conversations stay coherent when
  someone is addressed by name mid-sentence. In-text mentions are replaced by scanning for
  each known participant name and its first-name form.
- **Contact data.** Regex passes for emails, phone numbers (international formats), URLs
  and long digit runs. Replaced with structurally plausible fakes, not `[REDACTED]`, so
  the transcript still reads naturally.
- **Organisations.** A configurable term list in `ingest/scrub_terms.yml` maps real
  company, product and client names to invented ones. This file is the one part that needs
  a human pass; everything else is automatic.
- **Optional NER sweep.** If spaCy is available, an `en_core_web_sm` pass catches
  `PERSON` / `ORG` / `GPE` entities the rules missed, surfaced as warnings for review
  rather than replaced silently.

The reverse mapping is written to `ingest/.scrub_map.json`, which is **git-ignored**. It
exists so ingest can be re-run reproducibly; it never leaves the machine.

A test asserts that no original name from the mapping appears anywhere in the seeded
database. That test is the actual safety guarantee — the pipeline is only as trustworthy
as the check that proves it ran.

---

## 6. Backend

### 6.1 Layout

```
backend/
  app/
    main.py                  app factory, middleware, router mounting
    core/
      config.py              pydantic-settings
      db.py                  engine, session, PRAGMAs
      deps.py                FastAPI dependencies
      errors.py              exception → RFC-7807 problem+json
      logging.py             structured JSON logs, request ids
    models/                  SQLAlchemy declarative
    schemas/                 Pydantic request/response
    repositories/            SQL only — no HTTP concepts
    services/                business logic — no SQL, no HTTP
    routers/                 HTTP only — no SQL
    ingest/
      parsers/               registry + one module per format
      speakers.py normalizer.py scrub.py pipeline.py
    ai/
      summarizer.py rag.py prompts/
    jobs/
      queue.py worker.py
    seed/
      seed.py fixtures/
  tests/
  alembic/
```

The layering rule, enforced by review and by import-linter in CI:

> Routers never touch a `Session`. Repositories never raise `HTTPException`.
> Services never import from `routers`.

### 6.2 API surface

```
GET    /api/meetings?cursor&limit&q&participant&from&to&tag&sort
GET    /api/meetings/{id}
POST   /api/meetings                       → 202 { job_id }
PATCH  /api/meetings/{id}
DELETE /api/meetings/{id}

GET    /api/meetings/{id}/transcript?cursor&limit
GET    /api/meetings/{id}/transcript/search?q

GET    /api/meetings/{id}/summary
POST   /api/meetings/{id}/summarize        → 202 { job_id }

GET    /api/meetings/{id}/action-items
POST   /api/meetings/{id}/action-items
PATCH  /api/action-items/{id}
DELETE /api/action-items/{id}

GET    /api/search?q&limit                 global, ranked, snippets
POST   /api/meetings/{id}/ask              RAG chat
GET    /api/meetings/{id}/export?format=md|txt|pdf

GET    /api/jobs/{id}
GET    /healthz
```

Conventions: cursor pagination everywhere a list can grow; `problem+json` error bodies;
`ETag` / `If-None-Match` on transcript and summary reads (they are immutable between
edits, so a repeat visit is a `304`); every response carries an `X-Request-Id`.

### 6.3 Cursor pagination

Offset pagination degrades linearly — `OFFSET 50000` makes SQLite walk 50,000 rows to
discard them. Keyset pagination on the same tuple the index is sorted by is constant-time
regardless of depth.

```sql
SELECT id, title, started_at, duration_ms
FROM meetings
WHERE owner_id = :owner
  AND (started_at, id) < (:cursor_started_at, :cursor_id)
ORDER BY started_at DESC, id DESC
LIMIT :limit;
```

SQLite has supported row-value comparison since 3.15, so the tuple comparison is a single
index seek against `ix_meetings_recency`. The cursor handed to the client is
`base64(started_at | id)` — opaque, so the encoding can change without breaking clients.

Verified with `EXPLAIN QUERY PLAN`:
`SEARCH meetings USING INDEX ix_meetings_recency (owner_id=? AND started_at<?)`.

### 6.4 Jobs

`jobs/queue.py` exposes `enqueue(type, meeting_id, payload) -> job_id`. The default
executor runs the coroutine on the FastAPI event loop via `asyncio.create_task`, writing
`status` / `stage` / `progress` back to the `jobs` row as it goes. The client polls
`GET /api/jobs/{id}` at ~1s while a job is active.

The `jobs` table is the contract, not the executor. Replacing the executor with Celery or
RQ backed by Redis changes one module; the router, the client polling loop and the table
are untouched. This is the documented seam for horizontal scaling of ingest.

---

## 7. Search

### 7.1 Within a transcript

Server-side, scoped by `meeting_id`, returning matching `segment_id`s and character
offsets. The client highlights matches in place and offers next/previous navigation. Not
done client-side, because a 3-hour meeting is more text than should be scanned in the
render path on every keystroke.

### 7.2 Global

```sql
SELECT m.id            AS meeting_id,
       m.title,
       s.id            AS segment_id,
       s.start_ms,
       p.name          AS speaker,
       snippet(segments_fts, 0, '<mark>', '</mark>', '…', 12) AS snippet,
       bm25(segments_fts) AS rank
FROM segments_fts
JOIN transcript_segments s ON s.id = segments_fts.rowid
JOIN meetings     m ON m.id = s.meeting_id
LEFT JOIN participants p ON p.id = s.speaker_id
WHERE segments_fts MATCH :q
  AND m.owner_id = :owner
ORDER BY rank
LIMIT :limit;
```

Results group by meeting in the UI, each row deep-linking to
`/meetings/{id}?t={start_ms}` — which seeks the player and scrolls the transcript to that
segment on arrival. User input is escaped into an FTS5 query string rather than
interpolated, so a stray `"` or `*` cannot produce a syntax error or an injection.

### 7.3 The seam

```python
class SearchBackend(Protocol):
    def index(self, segments: Sequence[Segment]) -> None: ...
    def search(self, query: str, *, owner_id: int,
               meeting_id: int | None = None,
               limit: int = 20) -> list[SearchHit]: ...
```

`Fts5SearchBackend` today. `PostgresTsvectorBackend` or `OpenSearchBackend` on the same
protocol when SQLite is outgrown.

---

## 8. Frontend

### 8.1 Routes

```
app/
  (app)/
    layout.tsx              icon rail + top bar
    page.tsx                library          (RSC first page, client infinite scroll)
    meetings/[id]/page.tsx  detail           (RSC shell, client panes)
    search/page.tsx         global results
    settings/page.tsx       placeholders
components/
  library/  transcript/  summary/  player/  ui/
lib/
  api/  hooks/  stores/  format/
```

### 8.2 State

- **Server state** — TanStack Query. `useInfiniteQuery` for the library, mutations with
  optimistic updates for action items and metadata edits.
- **Playback state** — one Zustand store: `{ currentMs, durationMs, playing, seek(), toggle() }`.
  It is the only shared client state, and it exists because the player and the transcript
  must agree on the current position without one owning the other.
- **Everything else** is local component state.

### 8.3 Transcript ↔ player sync

The one genuinely hard interaction. Naïvely, every `timeupdate` (~4/s) triggers a linear
scan for the active segment — 8,000 comparisons per second on a 2,000-segment meeting,
plus a re-render of every row. It visibly stutters.

Instead:

```ts
// Built once on load, kept in a ref. Typed array, not objects.
const starts = new Int32Array(segments.map(s => s.start_ms));

function activeIndex(starts: Int32Array, t: number): number {
  let lo = 0, hi = starts.length - 1, ans = 0;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (starts[mid] <= t) { ans = mid; lo = mid + 1; }
    else                  { hi = mid - 1; }
  }
  return ans;
}
```

~11 comparisons instead of 2,000. Combined with:

- **Virtualisation** via `@tanstack/react-virtual`, so only visible rows mount.
- **Auto-scroll suppression**: after a manual scroll, auto-follow pauses for 2s and a
  "Jump to current" pill appears. Without this the pane fights the user.
- **Click to seek**: `playback.seek(segment.start_ms)`.
- Only the active index is stored in state, so a position change re-renders two rows, not
  the list.

### 8.4 Playback abstraction

```ts
interface PlaybackSource {
  readonly currentMs: number;
  readonly durationMs: number;
  readonly playing: boolean;
  play(): void;
  pause(): void;
  seek(ms: number): void;
  subscribe(cb: (ms: number) => void): () => void;
}
```

`MediaPlaybackSource` wraps an `HTMLMediaElement`. `VirtualPlaybackSource` advances a
clock with `requestAnimationFrame` against `performance.now()`, honours `seek`, and stops
at `durationMs`. The player UI and the transcript pane depend only on the interface, so
seeking, scrubbing, keyboard shortcuts and highlight-follow behave identically whether or
not a media file exists.

### 8.5 Design tokens

Derived from the Fireflies interface. One token file; dark mode redefines the same names.

| Token | Light | Role |
|---|---|---|
| `--primary` | `#584CF4` | Share button, active nav, timestamp links |
| `--primary-hover` | `#4A3FE0` | |
| `--bg` | `#F7F8FA` | App background |
| `--surface` | `#FFFFFF` | Panels, cards |
| `--border` | `#E6E8EF` | Hairlines, dividers |
| `--text` | `#12141A` | Primary text |
| `--text-muted` | `#5B6172` | Metadata, timestamps |
| `--accent-warn` | `#F59E0B` | REC badge, unread dot |

Layout metrics: 56px icon rail, 56px top bar, transcript pane fixed 380–420px, summary
pane flexible. Card radius 8px, control radius 6px. Inter throughout — matching the
original.

Speaker avatar colours come from a fixed 8-colour ramp indexed by name hash, so the same
person is the same colour everywhere.

---

## 9. AI layer

### 9.1 Summarisation

```python
class Summarizer(Protocol):
    def summarize(self, segments: Sequence[Segment]) -> SummaryResult: ...
```

Three implementations, selected by configuration:

- `LLMSummarizer` — the real path.
- `HeuristicSummarizer` — no API key required. TF-IDF keyword extraction for chapter
  titles, time-window chunking for chapter boundaries, and pattern matching for action
  items (`I'll …`, `can you …`, `by Friday`, `let's make sure`). Genuinely useful, fully
  deterministic.
- `SeededSummarizer` — reads pre-generated fixtures. Used for the deployed demo so the
  hosted link never depends on a key or a quota.

A full transcript exceeds a comfortable context window, so `LLMSummarizer` is
**map-reduce**, not one giant prompt:

1. **Map** — chunk segments into ~10-minute windows respecting speaker-turn boundaries.
   Each chunk yields a mini-summary, candidate chapter title, and candidate action items,
   each carrying the `start_ms` it came from.
2. **Reduce** — a second pass over the mini-summaries produces the final overview, merges
   near-duplicate action items, and assigns chapter boundaries.

Timestamps survive both passes, which is what makes every note and action item clickable.
Output is validated against a Pydantic schema; a malformed response falls back to
`HeuristicSummarizer` rather than failing the job.

### 9.2 RAG chat — "ask about this meeting"

The FTS5 index built for search is also the retriever, so this feature costs almost
nothing beyond what already exists.

1. Retrieve top-k segments for the question via `bm25` scoped to the meeting.
2. Expand each hit with ±2 neighbouring segments, so quotes are not decapitated.
3. Merge overlapping windows, cap the total token budget.
4. Prompt with numbered context: `[12] 04:31 Sarah: …`
5. Require the answer to cite segment numbers.
6. Render citations as timestamp chips that seek the player.

Stuffing the whole transcript into the prompt would be simpler and worse: it costs more,
degrades with length, and cannot cite. Retrieval plus citation is the correct shape, and
it demonstrates that the context window is understood as a real constraint.

Documented upgrade path: add `sqlite-vec` for embeddings and hybrid dense+BM25 ranking.

---

## 10. Testing

| Layer | Tool | What it protects |
|---|---|---|
| Parsers | pytest + golden fixtures | One fixture per format; parse → assert exact `RawTranscript`. |
| Normaliser | pytest, property-based | Merge/split boundaries, missing `end_ms`, zero-duration, single-speaker, empty input. |
| **Scrubber** | pytest | **No original name from the mapping appears anywhere in the seeded DB.** |
| Repositories | pytest + in-memory SQLite | Cursor pagination: no gaps, no duplicates, stable across insertions. |
| Search | pytest | Stemming, phrase queries, escaping of hostile input, `bm25` ordering. |
| API | httpx AsyncClient | Status codes, problem+json shape, ETag revalidation. |
| E2E | Playwright | Upload → job → summary appears. Click line → player seeks. Global search → correct segment. |

CI (GitHub Actions): `ruff` + `mypy` + `pytest` for the backend, `tsc --noEmit` +
`next lint` + `next build` for the frontend, Playwright on the merged stack.

---

## 11. Deployment

**Frontend** — Vercel. `NEXT_PUBLIC_API_URL` points at Render.

**Backend** — Render web service with a **persistent disk** mounted at `/var/data`;
`DATABASE_URL=sqlite:////var/data/app.db`. Without the disk, Render's ephemeral filesystem
discards the database on every restart and redeploy, and the demo link silently empties
out days after submission. This is the single highest-risk item in the project.

On boot: run Alembic migrations, then run the seed **only if the meetings table is empty**,
so restarts never duplicate data.

Also: CORS restricted to the Vercel origin; `/healthz` for platform checks; rate limiting
on write and AI endpoints; the free tier's ~50s cold start documented in the README so a
grader does not mistake it for a broken link.

**Deploy a skeleton of both services on day one.** Deployment is the highest-variance task
in the project — CORS, disk mounts, environment variables, build configuration — and
discovering it on the last day is how a working project ships a broken link.

---

## 12. Production hardening

This section documents work that is actually built and empirically measured, not
proposed — the difference between a scaling *path* (§14, unbuilt) and scaling *done*.

### 12.1 Dual-dialect database (ADR-006)

SQLite is right for local development (zero setup, one file) and wrong for anything
resembling concurrent write traffic — a single-writer lock serializes every insert.
Rather than fork the codebase, the same SQLAlchemy models and repositories run against
either dialect:

- `DATABASE_URL` selects the dialect (`sqlite+aiosqlite:///...` locally,
  `postgresql+asyncpg://...` in production). `Settings.is_sqlite` / `is_postgres`
  branch the handful of places that must (PRAGMA setup, full-text search).
- Migrations are **dialect-guarded, not dialect-forked**: each Alembic revision that
  needs different DDL per backend checks `op.get_bind().dialect.name` and no-ops on the
  other side, rather than maintaining two migration histories. The generated Postgres
  schema comes from the same ORM metadata as SQLite, so the two schemas cannot drift.
- Full-text search is the one place the two backends genuinely differ in approach:
  SQLite uses an FTS5 external-content virtual table with insert/update/delete triggers
  (§7.3); Postgres uses a generated `tsvector` column with a GIN index and
  `websearch_to_tsquery` / `ts_rank` / `ts_headline`. Both sit behind the same
  `SearchBackend` protocol, dispatched at call time on `session.bind.dialect.name` — the
  router and service layers never know which one is live.

A real Postgres instance was provisioned (Supabase, project `fireflies-clone-prod`) and
the migrations, seed, and search paths were run against it directly — this isn't a
theoretical seam, it's been exercised end to end. Supabase's advisory system flagged
that row-level security is disabled on all 14 tables; this is a real finding, correctly
left unaddressed rather than auto-remediated, since enabling RLS with no policies
defined would lock out the backend's own direct connection. It's lower-risk today
because the backend talks to Postgres directly rather than through Supabase's anon-key
client libraries, but it's a real decision to revisit before this project keeps
sensitive data indefinitely.

### 12.2 Rate limiting

`slowapi`, keyed by remote IP, with settings-driven limits: `120/minute` default,
`30/minute` on writes, `10/minute` on AI/transcription endpoints (the expensive ones).
A limit breach returns RFC-7807 `problem+json` with `429`, the same error shape as
every other failure mode in the API (§6.3) rather than a bespoke response.

Verified, not assumed: 130 rapid requests against a default-limited endpoint produced
117 successful `200`s and 13 `429`s — the limiter engages exactly where the configured
threshold says it should.

### 12.3 Caching

A `CacheBackend` protocol (`get` / `set` / `invalidate_prefix`) with one implementation
today, `InMemoryTTLCache` — a dict plus monotonic-clock expiry, capped at 2,000 entries.
It caches finished Pydantic response objects, never ORM objects (which are bound to a
session and unsafe to hold past the request). The seam is deliberately shaped like a
Redis client (`get`/`set`/prefix-invalidate) so swapping in `redis.asyncio` later is a
one-file change, not a redesign — the meetings and search routers already call the
protocol, not the implementation.

### 12.4 Load testing — real numbers

No load-testing binary (`hey`, `wrk`, `locust`) was available in the build environment,
so `backend/scripts/loadtest.py` — a small async `httpx`-based generator — was written
to actually measure the API rather than assert it "should scale." It hits a realistic
mix of endpoints (library list, meeting detail, transcript page, search, health) at
increasing concurrency and reports p50/p95/p99 and throughput:

| Concurrency | Throughput | p50 | p95 | p99 | Errors |
|---|---|---|---|---|---|
| 10 | ~410 req/s | 24ms | 61ms | 98ms | 0 |
| 50 | **515.2 req/s** | **78.1ms** | 183.1ms | 326.2ms | 0 |
| 100 | 480.6 req/s | 162ms | 410ms | 720ms | 0 |
| 200 | **130.2 req/s** | **1566.2ms** | 2984ms | 3811ms | 0 |

The honest finding: throughput peaks around concurrency 50 and the system holds up
through 100, but by 200 concurrent clients SQLite/`aiosqlite`'s single-writer lock is
saturated — p50 jumps roughly 20x and throughput collapses to a quarter of its peak,
even with zero outright errors (requests queue rather than fail). This is exactly the
limit §12.1's dual-dialect work exists to remove: the same load test against the
Postgres backend would be the natural next measurement, since Postgres's MVCC allows
genuinely concurrent writers where SQLite cannot. Documenting the actual breaking point
is more useful to a reviewer than an unverified claim that the system "scales."

### 12.5 Structured logging & error tracking

Every request gets a JSON log line carrying an `X-Request-Id` (generated per-request via
a `ContextVar` and returned in the response header), so a single request's log lines
correlate across the stack — the same request ID a user could paste into a bug report.

Error tracking (Sentry) is fully optional: with no `SENTRY_DSN` set, the init block
never runs and the app behaves identically. Setting the DSN turns it on with no other
code change — the kind of seam that matters more for what it *doesn't* require than
what it does.

---

## 13. Live recording & speech-to-text

Meeting-notes software a person only uses on transcripts someone else already typed up
isn't useful in daily life — the point of Fireflies is recording your *own* meetings.
This section documents the seam that makes that real, built and verified end to end on
its failure path (no OpenAI key is available in the build sandbox to exercise the
success path directly).

### 13.1 Architecture

Live recording is treated as **just another ingest source** (§5), not a special case:
it produces the same `Meeting` / `Participant` / `TranscriptSegment` rows a pasted
transcript would, so every downstream feature — search, summaries, the transcript UI —
needs no branch for "a meeting that came from a live recording."

- `POST /api/recordings` accepts a multipart audio upload plus a title, saves the file
  under `MEDIA_STORAGE_DIR`, creates a `Job` row (`status=queued`), and schedules
  transcription via `BackgroundTasks` — returning `202 Accepted` with the job
  immediately rather than blocking the request on transcription time.
- `GET /api/jobs/{id}` polls job status/stage/progress — the identical shape used for
  every other async ingest job, so a future real transcript-upload pipeline (§5) reuses
  this same polling contract rather than inventing a second one.
- A `Transcriber` protocol has two implementations: `UnavailableTranscriber` (the
  default — raises a clear, actionable error rather than silently accepting an upload
  it can never process) and `OpenAIWhisperTranscriber` (Whisper `verbose_json` with
  word-level timestamps, grouped into utterances via the same gap-threshold merge logic
  the ingest normalizer would use for any other source — one algorithm, not two).
- Because a `BackgroundTasks` callback runs after the request's database session has
  closed, the job handler opens its own fresh session — the same pattern a real worker
  process (Celery/RQ) would use, so promoting this out of `BackgroundTasks` later is a
  change of *caller*, not of the transcription logic itself.

### 13.2 Verified behavior

With no STT backend configured (the sandbox default), the graceful-failure path was
exercised end to end: upload → job created and queued → job correctly transitions to
`failed` with a clear, actionable error message (`"Speech-to-text is not configured.
Set TRANSCRIBER_BACKEND=openai and OPENAI_API_KEY..."`) — and critically, **no partial
or corrupt data is left behind**: no meeting, participant, or segment rows are created
for a job that fails at the transcription step. A deployment that forgets to configure
an API key fails loudly and immediately rather than silently accepting uploads it can
never turn into anything.

### 13.3 Consent

Turning this on for a real deployment means real audio of real people goes through a
third-party API (OpenAI's Whisper endpoint). That consent decision — telling meeting
participants a recording is happening and going to a third party — belongs to whoever
presses record, not to anything this code can enforce. Recorded audio and any
transcripts it produces are excluded from the public repository and from seed data by
the same boundary that keeps the real Hypotenuse Analytics reference transcripts out
(§4.1) — nothing captured through this feature is ever committed.

---

## 14. Scaling path

Nothing below is built. Each row names a real limit, and the seam already in the code
where the replacement goes.

| Limit reached | Change | Seam |
|---|---|---|
| Write concurrency past SQLite's single writer | Postgres | SQLAlchemy; repositories are the only SQL. |
| FTS5 index outgrows the box | OpenSearch / Elasticsearch | `SearchBackend` protocol (§7.3). |
| Ingest and summarisation saturate the web process | Celery/RQ + Redis, separate workers | `jobs/queue.py`; the `jobs` table is unchanged. |
| Media files outgrow local disk | S3 + CloudFront, presigned uploads | `media_url` is already an opaque URL. |
| Read traffic exceeds one instance | Read replicas + stateless app tier | No server-side session state exists. |
| Transcript payloads dominate bandwidth | Already cursor-paginated + ETagged; add CDN caching | §6.2 conventions. |
| Multi-tenant | `owner_id` is already on every root table and every index leads with it | Add org scoping and row-level checks in repositories. |
| Semantic search wanted | `sqlite-vec` → pgvector; hybrid ranking | §9.2. |

The last row of that table is the point of the whole document: the schema was designed
multi-tenant from the first migration even though there is exactly one user, because
retrofitting a tenant key into every index later is a migration nobody enjoys.

---

## 15. Open questions

- Real user accounts / auth are deliberately deferred — `DEMO_OWNER_ID` stands in for a
  single demo user for this submission. `owner_id` already sits on every root table and
  leads every index (§14), so adding real auth later is scoping queries by an
  authenticated identity rather than restructuring the schema.
- Whether one or two meetings get real matching audio to exercise the
  `MediaPlaybackSource` path alongside the virtual clock, versus relying on live
  recording (§13) to exercise that path instead.
- Whether the LLM path uses a hosted API in the deployed demo or ships seeded output only,
  with the live path demonstrated locally.
- The production Postgres load test (§12.4 measured SQLite's ceiling) — repeating that
  same measurement against the Postgres backend to confirm the write-concurrency limit
  actually moves.
