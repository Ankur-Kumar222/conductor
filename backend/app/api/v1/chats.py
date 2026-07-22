"""Chat thread CRUD — list, create, fetch (with messages), delete."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import Chat, Message, User
from app.schemas import ChatDetail, ChatSummary, MessageOut

router = APIRouter(prefix="/chats", tags=["chats"])


def _iso(dt) -> str:
    return dt.isoformat() if dt else ""


async def _owned_chat(session: AsyncSession, user: User, chat_id: str) -> Chat:
    try:
        cid = uuid.UUID(chat_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid chat id") from exc
    chat = await session.get(Chat, cid)
    if chat is None or chat.user_id != user.id:
        raise HTTPException(status_code=404, detail="chat not found")
    return chat


@router.get("", response_model=list[ChatSummary])
async def list_chats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ChatSummary]:
    counts = (
        select(Message.chat_id, func.count().label("n")).group_by(Message.chat_id).subquery()
    )
    rows = (
        await session.execute(
            select(Chat, counts.c.n)
            .outerjoin(counts, counts.c.chat_id == Chat.id)
            .where(Chat.user_id == user.id)
            .order_by(Chat.updated_at.desc())
        )
    ).all()
    return [
        ChatSummary(
            id=str(c.id), title=c.title, created_at=_iso(c.created_at),
            updated_at=_iso(c.updated_at), message_count=n or 0,
        )
        for c, n in rows
    ]


@router.post("", response_model=ChatSummary)
async def create_chat(
    title: str = Body(default="New chat", embed=True),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatSummary:
    chat = Chat(user_id=user.id, title=title or "New chat")
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return ChatSummary(
        id=str(chat.id), title=chat.title, created_at=_iso(chat.created_at),
        updated_at=_iso(chat.updated_at), message_count=0,
    )


@router.get("/{chat_id}", response_model=ChatDetail)
async def get_chat(
    chat_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatDetail:
    chat = await _owned_chat(session, user, chat_id)
    rows = (
        await session.execute(
            select(Message).where(Message.chat_id == chat.id).order_by(Message.created_at)
        )
    ).scalars().all()
    return ChatDetail(
        id=str(chat.id), title=chat.title, created_at=_iso(chat.created_at),
        updated_at=_iso(chat.updated_at),
        messages=[
            MessageOut(
                id=str(m.id), role=m.role, content=m.content, meta=m.meta,
                created_at=_iso(m.created_at),
            )
            for m in rows
        ],
    )


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    chat = await _owned_chat(session, user, chat_id)
    await session.execute(delete(Chat).where(Chat.id == chat.id))
    await session.commit()
    return {"ok": True, "deleted": str(chat.id)}
