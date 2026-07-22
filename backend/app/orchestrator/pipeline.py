"""End-to-end query pipeline: intent → plan → orchestrate → synthesize.

Conversations are organized into chat threads (`chats` + `messages`). Context is
loaded from the current chat's recent messages so follow-ups like "that email"
resolve within the thread. Each turn persists a user message and an assistant
message (with structured meta so the chat can be re-rendered later).
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import Chat, Message, User
from app.orchestrator import intent as intent_mod
from app.orchestrator import planner as planner_mod
from app.orchestrator import synthesizer as synth_mod
from app.orchestrator.agents import AgentContext
from app.orchestrator.orchestrator import Orchestrator
from app.schemas import PendingConfirmation, QueryResponse, SynthesizedResponse

CONTEXT_MESSAGES = 10  # ~5 exchanges of prior context within the chat


async def _load_chat(session: AsyncSession, user: User, chat_id: str | None, first_query: str) -> Chat:
    if chat_id:
        try:
            cid = uuid.UUID(chat_id)
        except ValueError:
            cid = None
        if cid:
            chat = await session.get(Chat, cid)
            if chat is not None and chat.user_id == user.id:
                return chat
    # create a new chat, titled from the first query
    title = first_query.strip().replace("\n", " ")
    title = (title[:60] + "…") if len(title) > 60 else title
    chat = Chat(user_id=user.id, title=title or "New chat")
    session.add(chat)
    await session.flush()
    return chat


async def _chat_context(session: AsyncSession, chat_id: uuid.UUID) -> str:
    rows = (
        await session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())
            .limit(CONTEXT_MESSAGES)
        )
    ).scalars().all()
    if not rows:
        return ""
    lines = ["Conversation so far (most recent last):"]
    for m in reversed(rows):
        who = "User" if m.role == "user" else "Conductor"
        lines.append(f"- {who}: {m.content[:300]}")
    return "\n".join(lines)


async def run_query(
    session: AsyncSession,
    user: User,
    query: str,
    chat_id: str | None = None,
    write_handler=None,
) -> QueryResponse:
    chat = await _load_chat(session, user, chat_id, query)
    context = await _chat_context(session, chat.id)

    # persist the user's message immediately
    session.add(Message(chat_id=chat.id, user_id=user.id, role="user", content=query))
    await session.flush()

    intent = await intent_mod.classify(query, context)

    if intent.needs_clarification and intent.clarification_question:
        msg = await _save_assistant(
            session, chat, user, intent.clarification_question, intent, [], [], []
        )
        return QueryResponse(
            chat_id=str(chat.id), message_id=str(msg.id), query=query, intent=intent,
            response=intent.clarification_question,
        )

    plan = await planner_mod.plan(query, intent, tz_name=user.timezone or "UTC", context=context)

    ctx = AgentContext(SessionLocal, user)
    orchestrator = Orchestrator(ctx)
    execution = await orchestrator.run(plan, write_handler=write_handler)

    synth: SynthesizedResponse = await synth_mod.synthesize(
        query, intent, execution, tz_name=user.timezone or "UTC"
    )

    pending = [
        PendingConfirmation(
            action_id=p["action_id"], service=p["service"],
            action_type=p["action_type"], preview=p["preview"],
        )
        for p in execution.pending_actions
    ]

    msg = await _save_assistant(
        session, chat, user, synth.response, intent,
        execution.step_results, synth.actions_taken, pending,
    )

    return QueryResponse(
        chat_id=str(chat.id),
        message_id=str(msg.id),
        query=query,
        intent=intent,
        response=synth.response,
        actions_taken=synth.actions_taken,
        steps=execution.step_results,
        pending_confirmations=pending,
        results=execution.data,
    )


async def _save_assistant(session, chat, user, content, intent, steps, actions, pending) -> Message:
    meta = {
        "intent": intent.model_dump() if intent else None,
        "steps": [s.model_dump() for s in steps],
        "actions_taken": [a.model_dump() for a in actions],
        "pending_confirmations": [p.model_dump() for p in pending],
    }
    msg = Message(chat_id=chat.id, user_id=user.id, role="assistant", content=content, meta=meta)
    session.add(msg)
    chat.updated_at = func.now()  # bump thread ordering
    await session.commit()
    await session.refresh(msg)
    return msg
