# Conductor

An AI-powered orchestration engine that coordinates **Gmail, Google Calendar, and Google Drive**
through natural language. Ask a question or give a command; Conductor classifies your intent, plans a
multi-service execution graph, runs the services in parallel over your **real** Workspace data, and
synthesizes a single grounded answer — proposing (never silently performing) any write.

> Built for the "Agentic Google Workspace Orchestrator" assignment. Orchestration is written from
> scratch — **no** LangChain / LlamaIndex / agent frameworks, and **no** managed vector DB (pgvector only).

---

## What it does

```
"What's on my calendar next week where john@company.com is invited?"
"Prepare for tomorrow's meeting with Acme Corp"      (Calendar + Gmail + Drive, in parallel)
"Draft a reply to my most recent Wellfound email"    (drafts + asks to confirm before sending)
"Move the meeting with John"                          (detects ambiguity → asks which one)
```

## Architecture

```
                 ┌─────────────── FastAPI backend ───────────────┐
  React UI  ──▶  │  Intent Classifier (GPT-5, structured)         │
  (Vite +        │        ↓                                       │
   Tailwind)     │  Query Planner  → execution DAG                │
                 │        ↓                                       │
                 │  Orchestrator (asyncio, parallel + partial-    │
                 │  failure isolation)                            │
                 │     ├─ Gmail agent   ┐                         │
                 │     ├─ Calendar agent ├─ search / get_context / │
                 │     └─ Drive agent   ┘  execute                │
                 │        ↓                                       │
                 │  Hybrid search (pgvector HNSW + metadata)      │
                 │        ↓                                       │
                 │  Response Synthesizer (GPT-5)                  │
                 └────────────────────────────────────────────────┘
                     │                        │
              PostgreSQL + pgvector      Google APIs (OAuth2)
              (cache + embeddings)       OpenAI (LLM + embeddings)
```

Deep dive: [`DESIGN.md`](./DESIGN.md) · API reference: [`API.md`](./API.md) · data model:
[`docs/ER.md`](./docs/ER.md) · worked examples: [`docs/SAMPLE_QUERIES.md`](./docs/SAMPLE_QUERIES.md).

## Tech stack

| Layer | Choice |
|---|---|
| API | FastAPI (async), Python 3.12, Poetry |
| DB | PostgreSQL 18 + **pgvector** (HNSW, cosine) via async SQLAlchemy + Alembic |
| LLM | OpenAI **GPT-5** (Responses API, native structured outputs) |
| Embeddings | `text-embedding-3-small` @ 1536-d |
| Google | `google-api-python-client` + OAuth2 web flow (real Gmail/Calendar/Drive) |
| Frontend | Vite + React + TypeScript + Tailwind v4 |

## Key design decisions

- **Draft + confirm safety.** Reads run freely; every write (send email, create/update/delete event,
  share file) is prepared as a `pending_action` and requires an explicit `/actions/confirm` call. Email
  writes create a real *unsent* Gmail draft first.
- **Metadata-first hybrid search.** Cheap SQL filters (sender, date range, mime type, attendee) narrow
  the set, then cosine KNN over the HNSW index ranks — faster and more precise than pure vector search.
- **From-scratch DAG orchestration.** Kahn topological levels; independent nodes run concurrently via
  `asyncio.gather`; a node failure is isolated so partial results still reach the synthesizer.
- **Structured outputs everywhere.** Intent, plan, write-builders, and synthesis all use Pydantic
  schemas validated at the API layer (the model retries on mismatch), so no brittle JSON parsing.
- **Temporal reasoning.** The planner is given the current time + the user's timezone (auto-detected
  from Calendar settings) and resolves "next week" / "tomorrow" to ISO bounds.

## Quickstart

Prereqs: Python 3.12 + Poetry, Node 20+, local PostgreSQL with the `vector` extension available, an
OpenAI key, and a Google Cloud **Web** OAuth client (Gmail/Calendar/Drive APIs enabled; redirect URI
`http://localhost:8000/api/v1/auth/google/callback`).

```bash
# 1. Database
createdb conductor
psql conductor -c 'CREATE EXTENSION IF NOT EXISTS vector;'

# 2. Backend
cd backend
cp .env.example .env          # fill OPENAI_API_KEY + GOOGLE_CLIENT_ID/SECRET
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload      # http://localhost:8000/docs

# 3. Frontend
cd ../frontend
npm install
npm run dev                    # http://localhost:5173
```

Then: open the UI → **Connect Google** → **Sync now** → start asking.

## Run with Docker (optional)

A full stack (Postgres+pgvector, backend, nginx-served frontend) is provided:

```bash
# root .env with OPENAI_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
docker compose up --build      # UI at http://localhost:5173, API at http://localhost:8000
```

Migrations run automatically on backend start.

## Testing

```bash
cd backend && poetry run pytest -q
```

Covers DAG topology (parallel / sequential / diamond / cycle), partial-failure isolation, filter
parsing, MIME body extraction, and embedding cleanup.
