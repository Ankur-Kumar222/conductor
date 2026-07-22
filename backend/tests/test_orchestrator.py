"""DAG topology + partial-failure isolation (no network)."""
from __future__ import annotations

import app.orchestrator.orchestrator as orch_mod
from app.orchestrator.orchestrator import Orchestrator, _topo_levels
from app.schemas import Plan
from tests.conftest import make_step


def _ids(levels):
    return [sorted(s.id for s in level) for level in levels]


def test_parallel_steps_single_level():
    steps = [make_step("a"), make_step("b"), make_step("c")]
    assert _ids(_topo_levels(steps)) == [["a", "b", "c"]]


def test_sequential_chain_orders_levels():
    steps = [
        make_step("s1"),
        make_step("s2", depends_on=["s1"]),
        make_step("s3", depends_on=["s2"]),
    ]
    assert _ids(_topo_levels(steps)) == [["s1"], ["s2"], ["s3"]]


def test_diamond_dependency():
    steps = [
        make_step("a"),
        make_step("b", depends_on=["a"]),
        make_step("c", depends_on=["a"]),
        make_step("d", depends_on=["b", "c"]),
    ]
    assert _ids(_topo_levels(steps)) == [["a"], ["b", "c"], ["d"]]


def test_cycle_does_not_deadlock():
    steps = [make_step("a", depends_on=["b"]), make_step("b", depends_on=["a"])]
    levels = _topo_levels(steps)
    assert sorted(s.id for level in levels for s in level) == ["a", "b"]


# ---- partial-failure isolation ----------------------------------------------
class _FakeAgent:
    def __init__(self, ctx):
        self.ctx = ctx

    async def search(self, step, top_k=5):
        if step.service == "gcal":
            raise RuntimeError("calendar boom")
        return [{"id": f"{step.service}-1", "title": "hit"}]


async def test_partial_failure_is_isolated(monkeypatch):
    monkeypatch.setattr(orch_mod, "AGENTS", {"gmail": _FakeAgent, "gcal": _FakeAgent})
    plan = Plan(steps=[make_step("g", service="gmail"), make_step("c", service="gcal")])
    execution = await Orchestrator(ctx=object()).run(plan)

    by_id = {s.id: s for s in execution.step_results}
    assert by_id["g"].status == "ok"
    assert by_id["g"].result_count == 1
    assert by_id["c"].status == "error"
    assert "boom" in by_id["c"].error
