"""Sync service: pull recent Google items, embed them, upsert into *_cache.

Bounded for the demo (recent N items / lookback window per service). Full
incremental sync + a task queue (Celery) is the documented scaling step.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.google import fetchers
from app.google.clients import GoogleServices
from app.models import GcalCache, GdriveCache, GmailCache, SyncState, User
from app.search.embeddings import embed_texts_async

SERVICES = ("gmail", "gcal", "drive")


# ---- text used to build each item's embedding -------------------------------
def _gmail_text(it: dict) -> str:
    return f"{it.get('subject') or ''}\nFrom: {it.get('sender') or ''}\n{it.get('body_preview') or ''}"


def _gcal_text(it: dict) -> str:
    attendees = ", ".join(a.get("email") or "" for a in (it.get("attendees") or []))
    return (
        f"{it.get('title') or ''}\n{it.get('description') or ''}\n"
        f"Location: {it.get('location') or ''}\nAttendees: {attendees}"
    )


def _drive_text(it: dict) -> str:
    return f"{it.get('name') or ''} ({it.get('mime_type') or ''})"


_CONFIG = {
    "gmail": (GmailCache, fetchers.fetch_gmail, _gmail_text, "email_id", "uq_gmail_user_email"),
    "gcal": (GcalCache, fetchers.fetch_gcal, _gcal_text, "event_id", "uq_gcal_user_event"),
    "drive": (GdriveCache, fetchers.fetch_drive, _drive_text, "file_id", "uq_gdrive_user_file"),
}


async def _get_sync_state(session: AsyncSession, user_id: uuid.UUID, service: str) -> SyncState:
    row = (
        await session.execute(
            select(SyncState).where(SyncState.user_id == user_id, SyncState.service == service)
        )
    ).scalar_one_or_none()
    if row is None:
        row = SyncState(user_id=user_id, service=service, status="idle")
        session.add(row)
        await session.flush()
    return row


async def sync_service(session: AsyncSession, user: User, service: str) -> dict:
    model, fetch_fn, text_fn, ext_key, constraint = _CONFIG[service]
    state = await _get_sync_state(session, user.id, service)
    state.status = "syncing"
    state.error = None
    await session.commit()

    try:
        svc = GoogleServices(user)
        if svc.token_refreshed:
            await session.commit()

        # Learn the user's timezone from their calendar (drives temporal reasoning).
        if service == "gcal":
            try:
                from app.google.clients import execute as _exec

                tz = await asyncio.to_thread(
                    lambda: _exec(svc.calendar.settings().get(setting="timezone")).get("value")
                )
                if tz and tz != user.timezone:
                    user.timezone = tz
                    await session.commit()
            except Exception:  # noqa: BLE001 - non-fatal
                pass

        items = await asyncio.to_thread(
            fetch_fn, svc, settings.sync_lookback_days, settings.sync_max_items_per_service
        )
        if items:
            vectors = await embed_texts_async([text_fn(it) for it in items])
            rows = []
            for it, vec in zip(items, vectors):
                row = {"id": uuid.uuid4(), "user_id": user.id, "embedding": vec, **it}
                rows.append(row)

            stmt = pg_insert(model).values(rows)
            update_cols = {
                c.name: stmt.excluded[c.name]
                for c in model.__table__.columns
                if c.name not in ("id", "user_id", ext_key)
            }
            stmt = stmt.on_conflict_do_update(constraint=constraint, set_=update_cols)
            await session.execute(stmt)

        state.status = "idle"
        state.item_count = len(items)
        state.last_synced_at = datetime.now(timezone.utc)
        await session.commit()
        return {"service": service, "synced": len(items)}
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        state = await _get_sync_state(session, user.id, service)
        state.status = "error"
        state.error = str(exc)[:500]
        await session.commit()
        return {"service": service, "error": str(exc)}


async def sync_all(session: AsyncSession, user: User, services: tuple[str, ...] = SERVICES) -> list[dict]:
    results = []
    for service in services:
        results.append(await sync_service(session, user, service))
    return results
