"""A StateGraph: an explicit, typed flow machine for the engine's bounded loops (Epic 269).

The name is the shape LangGraph made famous, implemented at zero dependencies: a
compile-time graph of nodes over typed state channels, conditional edges between
them, per-node ledger entries in the same trace the copilot writes, and a hard
step cap. What it is NOT is a wrapper around that library — the engine's hot
loop must stay offline-deterministic, mockable under `LLM_PROVIDER=mock`, and
legible without resolving a foreign API.

Design, in three promises:

1. **State is data, not side effects.** Nodes receive the whole state dict,
   return a partial update (shallow-merged) plus the name of the next node, and
   never mutate in place. A node therefore reads like a pure function over a
   typed-ish channel map and a `goto`; tests can.
2. **The graph is bounded before it is compiled.** The cap (`max_steps`) is a
   constructor argument, and the loop refuses to run longer than it, turning a
   bug (a node that keeps wiring back to itself) into a `StateGraphOverrun`
   refusal with the loop's step count in the message, never into a run-away
   token burn.
3. **Everything is traced into the existing ledger.** Each node emits a
   `graph_node` trace under the run id, so the AI Activity timeline shows the
   graph's own steps as first-class rows, with the node's outcome attached.
"""

from __future__ import annotations

import dataclasses
import logging
import time
from typing import Any, Awaitable, Callable

from app.db import observability

log = logging.getLogger("agents.stategraph")

Step = dict[str, Any]
Node = Callable[[Step], Awaitable["NodeResult"]]


class StateGraphOverrun(RuntimeError):
    """A node ran more than `max_steps` times; the bounded graph refused to continue."""


@dataclasses.dataclass(frozen=True)
class NodeResult:
    """One node's answer: a partial state update, plus where to go, plus anything worth tracing."""

    state: Step
    goto: str | None
    trace: Step = dataclasses.field(default_factory=dict)


class StateGraph:
    """A compiled StateGraph: entry, named nodes, a hard step cap, traced nodes."""

    def __init__(self, entry: str, nodes: dict[str, Node], *, max_steps: int = 6) -> None:
        if entry not in nodes:
            raise ValueError(f"entry node {entry!r} has no implementation in {sorted(nodes)}")
        self.entry = entry
        self.nodes = dict(nodes)
        self.max_steps = max_steps

    async def run(self, state: Step, *, run_id: str | None = None, agent: str = "stategraph") -> Step:
        current = state
        node_name = self.entry
        steps = []
        for step in range(self.max_steps):
            node = self.nodes[node_name]
            started = time.monotonic()
            result = await node(current)
            latency_ms = int((time.monotonic() - started) * 1000)
            steps.append({"node": node_name, "latency_ms": latency_ms,
                          "goto": result.goto, **result.trace})
            merged: Step = {**current, **result.state}
            merged["_graph_steps"] = steps
            if run_id:
                await observability.trace(run_id, "graph_node", agent, {
                    "node": node_name, "goto": result.goto, "latency_ms": latency_ms,
                    **result.trace,
                })
            trace = merged
            if result.goto is None:
                return trace
            if result.goto not in self.nodes:
                raise ValueError(f"node {node_name!r} routed to unknown node {result.goto!r}")
            current, node_name = merged, result.goto
        raise StateGraphOverrun(
            f"StateGraph exceeded {self.max_steps} node executions; the bounded graph refused to continue")
