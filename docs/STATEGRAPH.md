# The StateGraph — explicit nodes, bounded edges, one ledger

Epic 269. This document is the answer to what this repository calls a "StateGraph" —
and, just as importantly, what it does not claim to be.

## What it is

The shape LangGraph made famous: a directed graph of **nodes** over a typed
**state** channel, each node seeing the whole state, each returning a partial update
plus a **goto** naming the next node. Compile once at module import; run bounded
by construction; every node lands in the same agent_traces ledger the copilot
writes, as a `graph_node` row visible in the AI Activity timeline as "Flow node" /
"图节点" behind a Workflow icon, EN+ZH.

Implementation: `ai-service/app/agents/stategraph.py` — `StateGraph(entry, nodes,
*, max_steps=6)` with `NodeResult(state, goto, trace)`.

The three promises the engine keeps:

1. **State is data.** Nodes never mutate the caller's dict — updates are shallow-merged
   on a copy; a node is a pure function from state to (partial state, goto, trace).
2. **Bounded before compile.** `max_steps` is a constructor argument. The loop stops
   at the cap and raises `StateGraphOverrun` with the count in the message; a node
   wiring to itself is a refusal, never a burn.
3. **One ledger.** Every node emits `observability.trace(run_id, "graph_node",
   agent, {node, goto, latency_ms, ...})`. No new table, no new dashboard surface —
   the Flow node rows render in the same timeline, collapsed by default like every
   other kind, inspectable like every other kind.

## What the install does with it today

`features/tailor` — the resume tailoring loop — was the first caller, restructured
from a straight-line pipeline into a graph:

```
retrieve → draft ──(verifier says the draft invents)── back to draft (once) ──┐
              └── verify ─────────────→ render                             ─┘
```

Nodes: `retrieve` (RAG over the candidate's own material), `draft` (LLM), `verify`
(deterministic — skills and numbers only; the LLM earns its second attempt or the
original wording ships), `render` (apply accepted edits, build the diff).

Verifier feedback is injected into the second draft's prompt ("VERIFIER REJECTION
(rewrite only the offending bullets…)"), budget is exactly two drafts, the whole
verifier history is retained in the emitted `diff.rejected` (an invented bullet
the verifier refused and a later draft cleaned is *still* a bullet the reader
deserved to see rejected), and the stats line reflects both worlds.

## How to add a node

- Write the node in the feature module: `async def my_node(state) -> NodeResult`.
- Register it in the `StateGraph(entry, {...})` literal in the feature.
- Route with `goto=` — `"render"`-style names, never a string of your imagination:
  an unknown target is a `ValueError` at write time, not a silent dead-end.
- Bump `max_steps` only when you add an edge; the cap is not a suggestion.
- Add a test: the engine (`tests/test_stategraph.py`) holds the invariants —
  branch merge order, conditional back-edges, the overrun cap, unknown-node
  refusal, shallow merge without mutating input.

## What this is not

- **Not a dependency.** LangGraph itself is deliberately not installed. The engine's
  hot loop must stay offline-deterministic and mockable under
  `LLM_PROVIDER=mock EMBEDDING_PROVIDER=hash`; a foreign API in that path is a
  promise we cannot keep to the mock.
- **Not a multi-agent runtime.** The agent system's handoffs remain tool-driven
  (`transfer_to`) tracked by the orchestrator's own loop and recorded in the same
  ledger. A StateGraph run here is one capability's internal flow, not a second
  topology over everything.
- **Not a compile-time typecheck of state.** Channels are plain dicts by design;
  the guarantees are runtime (merge order, step cap, trace), not static — same
  honesty tier as the rest of the repo.

## Honest limits

The verifier decides the branch, which is the whole power and the whole constraint
of the thing: a bullet that passes skill and number absence tests with a changed
tone still passes. StateGraph is exactly as good as its gate. The revise loop is
bounded at two drafts; a third would double the cost and catch almost none of what
the second does not.
