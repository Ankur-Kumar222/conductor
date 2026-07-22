"""Sync endpoints — fully implemented in P2 (sync + embeddings)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Body, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, get_session
from app.deps import get_current_user
from app.models import SyncState, User
from app.services import sync as sync_service

router = APIRouter(prefix="/sync", tags=["sync"])


async def _run_sync(user_id: uuid.UUID, services: tuple[str, ...]) -> None:
    """Background task: fresh session, load user, sync selected services."""
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is not None:
            await sync_service.sync_all(session, user, services)


@router.post("/trigger")
async def sync_trigger(
    background: BackgroundTasks,
    services: list[str] | None = Body(default=None, embed=True),
    wait: bool = Body(default=False, embed=True),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Trigger a sync. Runs in the background by default; pass wait=true to block
    and return per-service counts (handy for testing)."""
    selected = tuple(services) if services else sync_service.SERVICES
    invalid = [s for s in selected if s not in sync_service.SERVICES]
    if invalid:
        return {"error": f"unknown services: {invalid}", "valid": list(sync_service.SERVICES)}

    if wait:
        results = await sync_service.sync_all(session, user, selected)
        return {"status": "completed", "results": results}

    background.add_task(_run_sync, user.id, selected)
    return {"status": "started", "services": list(selected)}


@router.get("/status")
async def sync_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rows = (
        await session.execute(select(SyncState).where(SyncState.user_id == user.id))
    ).scalars().all()
    return {
        "user_id": str(user.id),
        "services": {
            r.service: {
                "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None,
                "status": r.status,
                "item_count": r.item_count,
                "error": r.error,
            }
            for r in rows
        },
    }
