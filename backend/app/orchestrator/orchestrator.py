"""Execution engine: run a Plan's DAG level-by-level, parallel within a level.

Built from scratch on asyncio. A node's failure is isolated (recorded, not
raised) so partial results still flow to the synthesizer.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.orchestrator.agents import AGENTS, AgentContext
from app.schemas import Plan, PlanStep, StepResult

WRITE_OPS = {"draft_email", "send_email", "create_event", "update_event", "delete_event", "share_file"}


@dataclass
class ExecutionResult:
    step_results: list[StepResult] = field(default_factory=list)
    data: dict = field(default_factory=dict)  # step_id -> payload (search hits / context / write)
    pending_actions: list[dict] = field(default_factory=list)


def _topo_levels(steps: list[PlanStep]) -> list[list[PlanStep]]:
    """Kahn's algorithm → list of levels (each level runs in parallel)."""
    by_id = {s.id: s for s in steps}
    indeg = {s.id: 0 for s in steps}
    deps = {s.id: [d for d in s.depends_on if d in by_id] for s in steps}
    for sid, ds in deps.items():
        indeg[sid] = len(ds)

    levels: list[list[PlanStep]] = []
    remaining = set(by_id)
    while remaining:
        ready = [sid for sid in remaining if indeg[sid] == 0]
        if not ready:  # cycle / bad plan — run the rest in one level to avoid deadlock
            ready = list(remaining)
        levels.append([by_id[sid] for sid in ready])
        for sid in ready:
            remaining.discard(sid)
            for other in remaining:
                if sid in deps[other]:
                    indeg[other] -= 1
    return levels


class Orchestrator:
    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    async def run(self, plan: Plan, write_handler=None) -> ExecutionResult:
        result = ExecutionResult()
        for level in _topo_levels(plan.steps):
            coros = [self._run_step(step, result, write_handler) for step in level]
            await asyncio.gather(*coros, return_exceptions=True)
        return result

    async def _run_step(self, step: PlanStep, result: ExecutionResult, write_handler) -> None:
        sr = StepResult(
            id=step.id, service=step.service, operation=step.operation,
            description=step.description, status="ok",
        )
        try:
            agent_cls = AGENTS.get(step.service)
            if agent_cls is None:
                raise ValueError(f"unknown service {step.service}")
            agent = agent_cls(self.ctx)

            if step.operation == "search":
                hits = await agent.search(step)
                result.data[step.id] = {"type": "search", "hits": hits}
                sr.result_count = len(hits)

            elif step.operation == "get_context":
                ids = self._dependency_top_ids(step, result)
                contexts = []
                for item_id in ids:
                    contexts.append(await agent.get_context(item_id))
                result.data[step.id] = {"type": "context", "items": contexts}
                sr.result_count = len(contexts)

            elif step.operation in WRITE_OPS:
                dep_ctx = self._dependency_payloads(step, result)
                if write_handler is None:
                    sr.status = "skipped"
                    sr.error = "writes are handled in the write phase"
                    result.data[step.id] = {"type": "write", "status": "skipped"}
                else:
                    pending = await write_handler(agent, step, dep_ctx)
                    result.data[step.id] = {"type": "write", "pending": pending}
                    result.pending_actions.append(pending)
                    sr.status = "pending_confirmation"
                    sr.result_count = 1
            else:
                sr.status = "skipped"
                sr.error = f"unsupported operation {step.operation}"
        except Exception as exc:  # noqa: BLE001 - isolate node failure
            sr.status = "error"
            sr.error = str(exc)[:300]
        result.step_results.append(sr)

    def _dependency_top_ids(self, step: PlanStep, result: ExecutionResult, limit: int = 1) -> list[str]:
        ids: list[str] = []
        for dep in step.depends_on:
            payload = result.data.get(dep, {})
            if payload.get("type") == "search":
                ids.extend(h["id"] for h in payload.get("hits", [])[:limit])
        return ids

    def _dependency_payloads(self, step: PlanStep, result: ExecutionResult) -> list[dict]:
        return [result.data[dep] for dep in step.depends_on if dep in result.data]
