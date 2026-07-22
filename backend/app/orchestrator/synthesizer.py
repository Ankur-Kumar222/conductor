"""Response synthesizer — turn raw agent results into a natural-language answer."""
from __future__ import annotations

import json

from app.orchestrator import llm
from app.orchestrator.orchestrator import ExecutionResult
from app.schemas import Intent, SynthesizedResponse

SYSTEM = """You are Conductor's response synthesizer. Given the user's query and the raw \
results gathered by the gmail/gcal/drive agents, write a concise, helpful natural-language \
answer.

Guidelines:
- Ground every claim in the provided results; never invent emails, events, files, dates, or \
addresses. If nothing was found, say so plainly and suggest a next step.
- Prefer specifics: subjects, senders, dates/times, file names, attendees.
- If some steps failed (status=error), still answer with what succeeded and briefly note what \
couldn't be retrieved.
- For prepared writes (drafts / previews awaiting confirmation), describe what will happen and \
ask the user to confirm (e.g. "Would you like me to send it?"). Do NOT claim a write already \
happened unless a result says it executed.
- actions_taken: list only things actually done or drafted this turn.
- Render all dates and times in the user's timezone (provided below), not UTC. Use a friendly \
format like "Mon, Jul 27, 11:00 AM".
Keep it tight — a few sentences or a short bulleted list."""


def _serialize(execution: ExecutionResult) -> str:
    payload = {"steps": [], "data": {}}
    for sr in execution.step_results:
        payload["steps"].append({
            "id": sr.id, "service": sr.service, "operation": sr.operation,
            "status": sr.status, "count": sr.result_count, "error": sr.error,
        })
    # Trim large text fields to keep the prompt lean.
    for sid, d in execution.data.items():
        payload["data"][sid] = d
    return json.dumps(payload, default=str)[:12000]


async def synthesize(
    query: str, intent: Intent, execution: ExecutionResult, tz_name: str = "UTC", context: str = ""
) -> SynthesizedResponse:
    convo = f"Conversation so far:\n{context}\n\n" if context else ""
    user = (
        f"{convo}"
        f"User query: {query}\n"
        f"Intent: {intent.intent} (services={intent.services})\n"
        f"User timezone: {tz_name}\n\n"
        f"Agent results (JSON):\n{_serialize(execution)}"
    )
    return await llm.structured_async(SYSTEM, user, SynthesizedResponse, effort="low")
