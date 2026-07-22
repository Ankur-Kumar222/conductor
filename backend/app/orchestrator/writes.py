"""Draft + confirm writes.

`write_handler` is invoked by the orchestrator for write steps. It builds a
concrete write from the plan step + dependency context, creates a *safe*
artifact (a real unsent Gmail draft) or a preview (calendar/drive), records a
PendingAction, and returns a confirmation stub. Nothing is sent/created/deleted
until `confirm_action` is called.
"""
from __future__ import annotations

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import PendingAction, User
from app.orchestrator import llm
from app.orchestrator.agents import AGENTS, AgentContext
from app.schemas import EmailDraftSpec, EventChangeSpec, FileShareSpec, PlanStep

EMAIL_SYS = """You draft an email for the user based on the instruction, the conversation so far, \
and the content gathered this turn (emails/events/files found by prior steps). References like \
"that", "it", or "the doc" refer to items discussed earlier in the conversation — use the \
conversation context to resolve them and pull the actual content into the email body. Infer the \
correct recipient from context when possible (e.g. an airline support address, a sender to reply \
to). Write a complete, polite, ready-to-send email grounded in the real content — never invent \
details or leave placeholders like [TBD]. If you genuinely have no content to summarize, say so \
briefly in the body rather than fabricating. If the recipient cannot be determined, leave 'to' empty."""

EVENT_SYS = """You specify a calendar change from the instruction + context. For update/delete, \
set event_id from the context's top event. Use ISO8601 for start/end in the user's timezone. \
Leave fields you are not changing as ''/[]."""

SHARE_SYS = """You specify a Drive share from the instruction + context: the file_id (from \
context), the recipient email, and a role (reader/commenter/writer, default reader)."""


def _ctx_json(dep_ctx: list[dict]) -> str:
    return json.dumps(dep_ctx, default=str)[:8000]


async def write_handler(agent, step: PlanStep, dep_ctx: list[dict], context: str = "") -> dict:
    op = step.operation
    ctx_text = _ctx_json(dep_ctx)
    convo = f"Conversation so far:\n{context}\n\n" if context else ""
    user: User = agent.ctx.user

    if op in ("draft_email", "send_email"):
        spec = await llm.structured_async(
            EMAIL_SYS,
            f"{convo}Instruction: {step.query}\n\nContent gathered this turn:\n{ctx_text}",
            EmailDraftSpec,
        )
        draft_id = await agent.create_draft(spec.to, spec.subject, spec.body)
        payload = {"draft_id": draft_id, "to": spec.to, "subject": spec.subject, "body": spec.body}
        preview = f"To: {spec.to or '(recipient not determined)'}\nSubject: {spec.subject}\n\n{spec.body}"
        action_type = "send_email"

    elif op in ("create_event", "update_event", "delete_event"):
        spec = await llm.structured_async(
            EVENT_SYS,
            f"{convo}Operation: {op}\nInstruction: {step.query}\nUser timezone: {user.timezone}\n\n"
            f"Content gathered this turn:\n{ctx_text}",
            EventChangeSpec,
        )
        payload = {
            "event_id": spec.event_id, "title": spec.title, "start": spec.start, "end": spec.end,
            "attendees": spec.attendees, "description": spec.description, "location": spec.location,
            "timezone": user.timezone or "UTC",
        }
        preview = _event_preview(op, spec)
        action_type = op

    elif op == "share_file":
        spec = await llm.structured_async(
            SHARE_SYS, f"{convo}Instruction: {step.query}\n\nContent gathered this turn:\n{ctx_text}", FileShareSpec
        )
        payload = {"file_id": spec.file_id, "email": spec.email, "role": spec.role or "reader"}
        preview = f"Share file {spec.file_id} with {spec.email} as {spec.role or 'reader'}"
        action_type = "share_file"
    else:
        raise ValueError(f"unsupported write operation {op}")

    async with agent.ctx.new_session() as s:
        pa = PendingAction(
            user_id=agent.ctx.user_id, service=step.service, action_type=action_type,
            payload=payload, preview=preview, status="pending",
        )
        s.add(pa)
        await s.commit()
        await s.refresh(pa)
        action_id = str(pa.id)

    return {"action_id": action_id, "service": step.service, "action_type": action_type, "preview": preview}


def _event_preview(op: str, spec: EventChangeSpec) -> str:
    if op == "delete_event":
        return f"Delete event {spec.event_id or '(unspecified)'}"
    when = f"{spec.start} → {spec.end}" if spec.start else "(time unspecified)"
    who = f" with {', '.join(spec.attendees)}" if spec.attendees else ""
    verb = "Create" if op == "create_event" else "Update"
    return f"{verb} event: {spec.title or '(untitled)'} — {when}{who}\n{spec.description}".strip()


async def confirm_action(session: AsyncSession, user: User, action_id: str) -> dict:
    pa = await session.get(PendingAction, uuid.UUID(action_id))
    if pa is None or pa.user_id != user.id:
        raise ValueError("action not found")
    if pa.status != "pending":
        return {"status": pa.status, "result": pa.result, "note": "already resolved"}

    ctx = AgentContext(SessionLocal, user)
    agent = AGENTS[pa.service](ctx)
    result = await agent.execute(pa.action_type, pa.payload)

    pa.status = "executed"
    pa.result = result
    await session.commit()
    return {"status": "executed", "action_type": pa.action_type, "service": pa.service, "result": result}


async def cancel_action(session: AsyncSession, user: User, action_id: str) -> dict:
    pa = await session.get(PendingAction, uuid.UUID(action_id))
    if pa is None or pa.user_id != user.id:
        raise ValueError("action not found")
    if pa.status == "pending":
        pa.status = "cancelled"
        await session.commit()
    return {"status": pa.status, "action_type": pa.action_type, "service": pa.service}
