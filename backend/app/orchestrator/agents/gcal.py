"""Calendar agent: semantic search, full-event context, and event writes."""
from __future__ import annotations

from app.google.clients import execute_async
from app.orchestrator.agents.base import BaseAgent, filters_from_step
from app.schemas import PlanStep
from app.search import hybrid_search


class GCalAgent(BaseAgent):
    service = "gcal"

    async def search(self, step: PlanStep, top_k: int = 5) -> list[dict]:
        async with self.ctx.new_session() as session:
            return await hybrid_search.search_gcal(
                session, self.ctx.user_id, step.query, top_k=top_k,
                filters=filters_from_step(step),
            )

    async def get_context(self, item_id: str) -> dict:
        svc = await self.ctx.get_services()
        event = await execute_async(
            svc.calendar.events().get(calendarId="primary", eventId=item_id)
        )
        return {
            "id": item_id,
            "title": event.get("summary"),
            "description": event.get("description"),
            "location": event.get("location"),
            "start": event.get("start"),
            "end": event.get("end"),
            "attendees": [a.get("email") for a in event.get("attendees", [])],
            "organizer": (event.get("organizer") or {}).get("email"),
            "html_link": event.get("htmlLink"),
        }

    # ---- writes -------------------------------------------------------------
    def _body(self, payload: dict) -> dict:
        body: dict = {}
        if payload.get("title"):
            body["summary"] = payload["title"]
        if payload.get("description"):
            body["description"] = payload["description"]
        if payload.get("location"):
            body["location"] = payload["location"]
        if payload.get("start"):
            body["start"] = {"dateTime": payload["start"], "timeZone": payload.get("timezone", "UTC")}
        if payload.get("end"):
            body["end"] = {"dateTime": payload["end"], "timeZone": payload.get("timezone", "UTC")}
        if payload.get("attendees"):
            body["attendees"] = [{"email": e} for e in payload["attendees"]]
        return body

    async def execute(self, action_type: str, payload: dict) -> dict:
        svc = await self.ctx.get_services()
        events = svc.calendar.events()
        if action_type == "create_event":
            ev = await execute_async(events.insert(calendarId="primary", body=self._body(payload)))
            return {"executed": True, "event_id": ev.get("id"), "html_link": ev.get("htmlLink")}
        if action_type == "update_event":
            ev = await execute_async(
                events.patch(calendarId="primary", eventId=payload["event_id"], body=self._body(payload))
            )
            return {"executed": True, "event_id": ev.get("id"), "html_link": ev.get("htmlLink")}
        if action_type == "delete_event":
            await execute_async(events.delete(calendarId="primary", eventId=payload["event_id"]))
            return {"executed": True, "event_id": payload["event_id"], "deleted": True}
        raise ValueError(f"GCalAgent cannot execute {action_type}")
