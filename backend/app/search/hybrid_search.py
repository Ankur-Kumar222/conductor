"""Hybrid search over the *_cache tables: metadata filter + vector cosine KNN.

Per the assignment hint, we filter on cheap metadata (sender, date, mime type,
attendee) first and rank the survivors by cosine distance on the HNSW index.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, String, and_, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GcalCache, GdriveCache, GmailCache
from app.search.embeddings import embed_text_async


class Filters:
    """Optional structured filters extracted from a query/plan step."""

    def __init__(
        self,
        sender: str | None = None,
        attendee: str | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
        mime_type: str | None = None,
        name_contains: str | None = None,
    ):
        self.sender = sender
        self.attendee = attendee
        self.after = after
        self.before = before
        self.mime_type = mime_type
        self.name_contains = name_contains


def _score(distance: float | None) -> float:
    return round(1.0 - float(distance), 4) if distance is not None else 0.0


async def _run(session: AsyncSession, stmt: Select) -> list[tuple[Any, float]]:
    rows = (await session.execute(stmt)).all()
    return [(r[0], r[1]) for r in rows]


async def search_gmail(
    session: AsyncSession, user_id: uuid.UUID, query: str, top_k: int = 5, filters: Filters | None = None
) -> list[dict]:
    qvec = await embed_text_async(query)
    dist = GmailCache.embedding.cosine_distance(qvec)
    conds = [GmailCache.user_id == user_id, GmailCache.embedding.isnot(None)]
    f = filters or Filters()
    if f.sender:
        conds.append(GmailCache.sender.ilike(f"%{f.sender}%"))
    if f.after:
        conds.append(GmailCache.received_at >= f.after)
    if f.before:
        conds.append(GmailCache.received_at <= f.before)
    stmt = select(GmailCache, dist.label("d")).where(and_(*conds)).order_by(dist).limit(top_k)
    return [
        {
            "service": "gmail",
            "id": r.email_id,
            "thread_id": r.thread_id,
            "title": r.subject,
            "sender": r.sender,
            "snippet": r.body_preview,
            "received_at": r.received_at.isoformat() if r.received_at else None,
            "score": _score(d),
        }
        for r, d in await _run(session, stmt)
    ]


async def search_gcal(
    session: AsyncSession, user_id: uuid.UUID, query: str, top_k: int = 5, filters: Filters | None = None
) -> list[dict]:
    qvec = await embed_text_async(query)
    dist = GcalCache.embedding.cosine_distance(qvec)
    conds = [GcalCache.user_id == user_id, GcalCache.embedding.isnot(None)]
    f = filters or Filters()
    if f.after:
        conds.append(GcalCache.start_at >= f.after)
    if f.before:
        conds.append(GcalCache.start_at <= f.before)
    if f.attendee:
        # attendees is JSONB [{"email": ...}]; substring match handles both a full
        # email ("sarah@company.com") and a bare name ("Sarah").
        conds.append(cast(GcalCache.attendees, String).ilike(f"%{f.attendee}%"))
    stmt = select(GcalCache, dist.label("d")).where(and_(*conds)).order_by(dist).limit(top_k)
    return [
        {
            "service": "gcal",
            "id": r.event_id,
            "title": r.title,
            "description": r.description,
            "location": r.location,
            "attendees": r.attendees,
            "organizer": r.organizer,
            "start_at": r.start_at.isoformat() if r.start_at else None,
            "end_at": r.end_at.isoformat() if r.end_at else None,
            "score": _score(d),
        }
        for r, d in await _run(session, stmt)
    ]


async def search_drive(
    session: AsyncSession, user_id: uuid.UUID, query: str, top_k: int = 5, filters: Filters | None = None
) -> list[dict]:
    qvec = await embed_text_async(query)
    dist = GdriveCache.embedding.cosine_distance(qvec)
    conds = [GdriveCache.user_id == user_id, GdriveCache.embedding.isnot(None)]
    f = filters or Filters()
    if f.mime_type:
        conds.append(GdriveCache.mime_type.ilike(f"%{f.mime_type}%"))
    if f.name_contains:
        conds.append(GdriveCache.name.ilike(f"%{f.name_contains}%"))
    if f.after:
        conds.append(GdriveCache.modified_at >= f.after)
    if f.before:
        conds.append(GdriveCache.modified_at <= f.before)
    stmt = select(GdriveCache, dist.label("d")).where(and_(*conds)).order_by(dist).limit(top_k)
    return [
        {
            "service": "drive",
            "id": r.file_id,
            "title": r.name,
            "mime_type": r.mime_type,
            "owners": r.owners,
            "web_view_link": r.web_view_link,
            "modified_at": r.modified_at.isoformat() if r.modified_at else None,
            "score": _score(d),
        }
        for r, d in await _run(session, stmt)
    ]


SEARCHERS = {"gmail": search_gmail, "gcal": search_gcal, "drive": search_drive}


async def search(
    session: AsyncSession, service: str, user_id: uuid.UUID, query: str,
    top_k: int = 5, filters: Filters | None = None,
) -> list[dict]:
    return await SEARCHERS[service](session, user_id, query, top_k=top_k, filters=filters)
