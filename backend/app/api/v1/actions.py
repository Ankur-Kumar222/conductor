"""Confirm / cancel drafted writes (the draft + confirm safety gate)."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import PendingAction, User
from app.orchestrator import writes

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("")
async def list_pending(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rows = (
        await session.execute(
            select(PendingAction)
            .where(PendingAction.user_id == user.id, PendingAction.status == "pending")
            .order_by(PendingAction.created_at.desc())
        )
    ).scalars().all()
    return {
        "pending": [
            {"action_id": str(r.id), "service": r.service, "action_type": r.action_type, "preview": r.preview}
            for r in rows
        ]
    }


@router.post("/confirm")
async def confirm(
    action_id: str = Body(..., embed=True),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        return await writes.confirm_action(session, user, action_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/cancel")
async def cancel(
    action_id: str = Body(..., embed=True),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        return await writes.cancel_action(session, user, action_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
