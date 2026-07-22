"""Test helpers shared across the suite."""
from __future__ import annotations

from app.schemas import PlanStep, StepFilters


def make_step(step_id: str, service: str = "gmail", operation: str = "search",
              query: str = "q", depends_on: list[str] | None = None, **filters) -> PlanStep:
    return PlanStep(
        id=step_id,
        service=service,
        operation=operation,
        query=query,
        filters=StepFilters(
            sender=filters.get("sender", ""),
            attendee=filters.get("attendee", ""),
            after=filters.get("after", ""),
            before=filters.get("before", ""),
            mime_type=filters.get("mime_type", ""),
            name_contains=filters.get("name_contains", ""),
        ),
        depends_on=depends_on or [],
        description=f"step {step_id}",
    )
