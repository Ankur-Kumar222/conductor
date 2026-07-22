"""End-to-end query pipeline: intent → plan → orchestrate → synthesize.

Also loads recent conversation context (last 5 turns) so references like
"that email" resolve, and persists each turn.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import Conversation, User
from app.orchestrator import intent as intent_mod
from app.orchestrator import planner as planner_mod
from app.orchestrator import synthesizer as synth_mod
from app.orchestrator.agents import AgentContext
from app.orchestrator.orchestrator import Orchestrator
from app.schemas import (
    PendingConfirmation,
    QueryResponse,
    SynthesizedResponse,
)


async def _recent_context(session: AsyncSession, user_id: uuid.UUID, limit: int = 5) -> str:
    rows = (
        await session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    if not rows:
        return ""
    lines = ["Recent conversation (most recent last):"]
    for c in reversed(rows):
        lines.append(f"- User: {c.query}")
        if c.response:
            lines.append(f"  Conductor: {c.response[:200]}")
    return "\n".join(lines)


async def run_query(
    session: AsyncSession,
    user: User,
    query: str,
    conversation_id: str | None = None,
    write_handler=None,
) -> QueryResponse:
    context = await _recent_context(session, user.id)

    intent = await intent_mod.classify(query, context)

    conv_id = conversation_id or str(uuid.uuid4())

    if intent.needs_clarification and intent.clarification_question:
        await _save(session, user.id, conv_id, query, intent, intent.clarification_question)
        return QueryResponse(
            conversation_id=conv_id, query=query, intent=intent,
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

    await _save(session, user.id, conv_id, query, intent, synth.response)

    return QueryResponse(
        conversation_id=conv_id,
        query=query,
        intent=intent,
        response=synth.response,
        actions_taken=synth.actions_taken,
        steps=execution.step_results,
        pending_confirmations=pending,
        results=execution.data,
    )


async def _save(session, user_id, conv_id, query, intent, response) -> None:
    # Each turn is its own row (own PK). conv_id is a client-facing thread handle;
    # context is loaded per-user (last 5 turns), so threading needs no extra column.
    session.add(
        Conversation(
            user_id=user_id, query=query, intent=intent.model_dump(), response=response,
        )
    )
    await session.commit()
