"""Shared FastAPI dependencies (current-user resolution).

Single-user local demo: we resolve the user from the `conductor_user` cookie,
an `X-User-Id` header, or a `user_id` query param; failing that we fall back to
the most-recently-created user. Multi-tenant auth is a documented scaling step.
"""
from __future__ import annotations

import uuid

from fastapi import Cookie, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User

USER_COOKIE = "conductor_user"


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    conductor_user: str | None = Cookie(default=None),
    x_user_id: str | None = Header(default=None),
    user_id: str | None = Query(default=None),
) -> User:
    raw = user_id or x_user_id or conductor_user
    user: User | None = None
    if raw:
        try:
            uid = uuid.UUID(raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user id") from exc
        user = await session.get(User, uid)
    if user is None:
        # fallback: most recent connected user
        user = (
            await session.execute(select(User).order_by(User.created_at.desc()).limit(1))
        ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="No connected Google account. Visit /api/v1/auth/google")
    return user
