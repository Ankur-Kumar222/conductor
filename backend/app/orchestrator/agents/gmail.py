"""Gmail agent: semantic search, full-message context, and draft/send writes."""
from __future__ import annotations

import base64
from email.message import EmailMessage

from app.google.clients import execute_async
from app.orchestrator.agents.base import BaseAgent, filters_from_step
from app.schemas import PlanStep
from app.search import hybrid_search


def _decode(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def _find_mime(payload: dict, target: str) -> str:
    """Depth-first search for the first part matching `target` mime type."""
    if not payload:
        return ""
    if payload.get("mimeType") == target and payload.get("body", {}).get("data"):
        return _decode(payload["body"]["data"])
    for part in payload.get("parts") or []:
        found = _find_mime(part, target)
        if found:
            return found
    return ""


def _extract_body(payload: dict) -> str:
    """Return the message body, preferring text/plain across the whole MIME tree."""
    return _find_mime(payload, "text/plain") or _find_mime(payload, "text/html")


class GmailAgent(BaseAgent):
    service = "gmail"

    async def search(self, step: PlanStep, top_k: int = 5) -> list[dict]:
        async with self.ctx.new_session() as session:
            return await hybrid_search.search_gmail(
                session, self.ctx.user_id, step.query, top_k=top_k,
                filters=filters_from_step(step),
            )

    async def get_context(self, item_id: str) -> dict:
        svc = await self.ctx.get_services()
        msg = await execute_async(
            svc.gmail.users().messages().get(userId="me", id=item_id, format="full")
        )
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        return {
            "id": item_id,
            "thread_id": msg.get("threadId"),
            "subject": headers.get("subject"),
            "from": headers.get("from"),
            "to": headers.get("to"),
            "date": headers.get("date"),
            "body": _extract_body(msg.get("payload", {}))[:6000],
        }

    # ---- writes -------------------------------------------------------------
    def _raw(self, to: str, subject: str, body: str) -> str:
        msg = EmailMessage()
        if to:
            msg["To"] = to
        msg["Subject"] = subject or ""
        msg.set_content(body or "")
        return base64.urlsafe_b64encode(msg.as_bytes()).decode()

    async def create_draft(self, to: str, subject: str, body: str) -> str:
        """Create a real (unsent) Gmail draft; returns the draft id."""
        svc = await self.ctx.get_services()
        draft = await execute_async(
            svc.gmail.users().drafts().create(
                userId="me", body={"message": {"raw": self._raw(to, subject, body)}}
            )
        )
        return draft["id"]

    async def execute(self, action_type: str, payload: dict) -> dict:
        svc = await self.ctx.get_services()
        if action_type == "send_email":
            draft_id = payload.get("draft_id")
            if draft_id:
                sent = await execute_async(
                    svc.gmail.users().drafts().send(userId="me", body={"id": draft_id})
                )
            else:
                raw = self._raw(payload.get("to", ""), payload.get("subject", ""), payload.get("body", ""))
                sent = await execute_async(
                    svc.gmail.users().messages().send(userId="me", body={"raw": raw})
                )
            return {"executed": True, "message_id": sent.get("id"), "thread_id": sent.get("threadId")}
        raise ValueError(f"GmailAgent cannot execute {action_type}")
