"""Shared per-query agent context + base agent contract.

Each service agent implements search() (semantic), get_context() (full content
for LLM reasoning), and execute() (writes — drafted/previewed, confirmed later).

Concurrency: steps in a DAG level run in parallel, so each DB touch uses its own
AsyncSession (SQLAlchemy sessions are not safe for concurrent use). The shared
GoogleServices is built once behind a lock; a refreshed token is persisted via a
dedicated session.
"""
from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.google import oauth
from app.google.clients import GoogleServices
from app.models import User
from app.schemas import PlanStep
from app.search.hybrid_search import Filters


class AgentContext:
    def __init__(self, sessionmaker: async_sessionmaker, user: User):
        self._sm = sessionmaker
        self.user = user
        self.user_id = user.id
        self._services: GoogleServices | None = None
        self._svc_lock = asyncio.Lock()

    def new_session(self):
        """Return a fresh AsyncSession context manager for one step's DB work."""
        return self._sm()

    async def get_services(self) -> GoogleServices:
        async with self._svc_lock:
            if self._services is None:
                svc = GoogleServices(self.user)
                if svc.token_refreshed:
                    async with self._sm() as s:
                        db_user = await s.get(User, self.user_id)
                        if db_user is not None:
                            db_user.google_access_token = svc.creds.token
                            db_user.token_expiry = oauth.expiry_utc(svc.creds)
                            await s.commit()
                self._services = svc
        return self._services


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def filters_from_step(step: PlanStep) -> Filters:
    f = step.filters
    return Filters(
        sender=f.sender or None,
        attendee=f.attendee or None,
        after=_parse_iso(f.after),
        before=_parse_iso(f.before),
        mime_type=f.mime_type or None,
        name_contains=f.name_contains or None,
    )


class BaseAgent:
    service: str = ""

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    async def search(self, step: PlanStep, top_k: int = 5) -> list[dict]:
        raise NotImplementedError

    async def get_context(self, item_id: str) -> dict:
        raise NotImplementedError

    async def execute(self, action_type: str, payload: dict) -> dict:
        raise NotImplementedError
