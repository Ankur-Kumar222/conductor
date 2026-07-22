"""Conductor FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import actions, auth, chats, query, sync
from app.config import settings

app = FastAPI(
    title="Conductor",
    description="Agentic Google Workspace Orchestrator",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "service": "conductor", "version": "0.1.0"}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(sync.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(actions.router, prefix="/api/v1")
app.include_router(chats.router, prefix="/api/v1")
