"""Pydantic schemas: LLM structured outputs + API request/response models.

Structured-output models are kept strict-mode friendly (no open dicts / optionals);
"absent" values are represented as empty strings / empty lists.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ServiceName = Literal["gmail", "gcal", "drive"]
Operation = Literal[
    "search", "get_context",
    "draft_email", "send_email",
    "create_event", "update_event", "delete_event",
    "share_file",
]


# ---- Intent classification ---------------------------------------------------
class Entity(BaseModel):
    name: str = Field(description="entity name, e.g. airline, person, company, file_type, sender")
    value: str


class Intent(BaseModel):
    services: list[ServiceName] = Field(description="services this query touches")
    intent: str = Field(description="short snake_case intent label, e.g. search_email, cancel_flight")
    entities: list[Entity]
    needs_clarification: bool = Field(description="true only if the query is too ambiguous to act on")
    clarification_question: str = Field(description="question to ask the user, or '' if none")


# ---- Query planning (the execution DAG) -------------------------------------
class StepFilters(BaseModel):
    sender: str = Field(description="email sender substring, or ''")
    attendee: str = Field(description="calendar attendee email, or ''")
    after: str = Field(description="ISO8601 lower bound for the item's date, or ''")
    before: str = Field(description="ISO8601 upper bound for the item's date, or ''")
    mime_type: str = Field(description="Drive mime type hint e.g. 'pdf','document','spreadsheet', or ''")
    name_contains: str = Field(description="Drive filename substring, or ''")


class PlanStep(BaseModel):
    id: str = Field(description="unique step id like 's1'")
    service: ServiceName
    operation: Operation
    query: str = Field(description="semantic search text or a description of the write to perform")
    filters: StepFilters
    depends_on: list[str] = Field(description="ids of steps that must complete first")
    description: str = Field(description="human-readable purpose of this step")


class Plan(BaseModel):
    steps: list[PlanStep]


# ---- Write builders (LLM turns a plan step + context into a concrete write) --
class EmailDraftSpec(BaseModel):
    to: str = Field(description="recipient email address; '' if it must be asked")
    subject: str
    body: str


class EventChangeSpec(BaseModel):
    event_id: str = Field(description="target event id for update/delete, else ''")
    title: str
    start: str = Field(description="ISO8601 start, or ''")
    end: str = Field(description="ISO8601 end, or ''")
    attendees: list[str]
    description: str
    location: str


class FileShareSpec(BaseModel):
    file_id: str
    email: str = Field(description="email to share with")
    role: str = Field(description="reader | commenter | writer")


# ---- Response synthesis ------------------------------------------------------
class ActionTaken(BaseModel):
    service: ServiceName
    action: str
    detail: str


class SynthesizedResponse(BaseModel):
    response: str = Field(description="natural-language answer for the user")
    actions_taken: list[ActionTaken]


# ---- API request/response ----------------------------------------------------
class QueryRequest(BaseModel):
    query: str
    chat_id: str | None = None


class ChatSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    meta: dict | None = None
    created_at: str


class ChatDetail(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[MessageOut] = []


class StepResult(BaseModel):
    id: str
    service: str
    operation: str
    description: str
    status: str  # ok | error | skipped | pending_confirmation
    result_count: int = 0
    error: str = ""


class PendingConfirmation(BaseModel):
    action_id: str
    service: str
    action_type: str
    preview: str


class QueryResponse(BaseModel):
    chat_id: str
    message_id: str = ""
    query: str
    intent: Intent | None = None
    response: str
    actions_taken: list[ActionTaken] = []
    steps: list[StepResult] = []
    pending_confirmations: list[PendingConfirmation] = []
    results: dict = {}
