# Conductor Backend

FastAPI orchestration layer for the Agentic Google Workspace Orchestrator.

See the repo root `README.md` and (later) `DESIGN.md` / `API.md` for the full picture.

## Quickstart

```bash
cd backend
poetry install
cp .env.example .env   # fill in Google OAuth client id/secret
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the OpenAPI UI and http://localhost:8000/health for a health check.
