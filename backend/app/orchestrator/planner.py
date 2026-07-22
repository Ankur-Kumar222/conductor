"""Query planner — turn an Intent into an execution DAG of PlanStep nodes.

Temporal reasoning happens here: we pass the current time + timezone so the LLM
resolves relative ranges ("next week", "tomorrow") into ISO bounds on filters.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.orchestrator import llm
from app.schemas import Intent, Plan

SYSTEM = """You are the query planner for Conductor. Given a user query and its classified \
intent, produce an execution DAG of steps over gmail / gcal / drive.

Rules:
- Independent reads run in PARALLEL: give them no dependencies (empty depends_on).
- Sequential work uses depends_on: e.g. a draft_email that needs a booking reference \
depends_on the gmail search step that finds it.
- operation is one of: search, get_context, draft_email, send_email, create_event, \
update_event, delete_event, share_file. For reads use 'search' (semantic) and optionally \
'get_context' (fetch full content of the top hit) when the answer needs the full body.
- For every WRITE (draft_email/create_event/update_event/delete_event/share_file), FIRST add \
the read steps needed to gather context, then the write step depending on them. Writes are \
executed as drafts/previews requiring user confirmation — never assume they auto-send.
- filters: fill only what applies; leave others as ''. Resolve relative dates to ISO8601 \
using the provided current time and timezone. For "next week" use the coming Mon–Sun range in \
the user's timezone. For Drive file types set mime_type hints like 'pdf' or 'document'.
- query: a concise semantic search string (for reads) or a clear description of the write.
- Keep the plan minimal — usually 1 step for single-service queries, 2–4 for multi-service.

Return ONLY the structured plan."""


def _time_context(tz_name: str) -> str:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001
        tz = ZoneInfo("UTC")
    now = datetime.now(tz)
    return (
        f"Current datetime: {now.isoformat()} ({tz_name}). "
        f"Today is {now.strftime('%A, %d %B %Y')}."
    )


async def plan(query: str, intent: Intent, tz_name: str = "UTC", context: str = "") -> Plan:
    entities = ", ".join(f"{e.name}={e.value}" for e in intent.entities) or "none"
    user = (
        f"{_time_context(tz_name)}\n"
        f"{context}\n\n"
        f"User query: {query}\n"
        f"Services: {intent.services}\n"
        f"Intent: {intent.intent}\n"
        f"Entities: {entities}"
    )
    return await llm.structured_async(SYSTEM, user, Plan, effort="low")
