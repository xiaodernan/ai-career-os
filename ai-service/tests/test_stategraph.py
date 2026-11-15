"""The StateGraph spine — its contracts before any feature is hung on it."""

import pytest

from app.agents.stategraph import NodeResult, StateGraph, StateGraphOverrun


async def _node_a(state):
    return NodeResult(state={"a": state["x"] + 1, "visited": state.get("visited", []) + ["a"]}, goto="b")


async def _node_b(state):
    return NodeResult(state={"b": state["a"] * 2, "visited": state["visited"] + ["b"]}, goto=None)


@pytest.mark.asyncio
async def test_a_simple_chain_merges_state_in_order():
    graph = StateGraph("a", {"a": _node_a, "b": _node_b})
    out = await graph.run({"x": 2}, run_id=None)
    assert out["a"] == 3 and out["b"] == 6
    assert out["visited"] == ["a", "b"]
    assert [s["node"] for s in out["_graph_steps"]] == ["a", "b"]


def _condition_node(state):
    async def node(st):
        return NodeResult(state={"attempt": st["attempt"] + 1}, goto="loop")

    return node


@pytest.mark.asyncio
async def test_conditional_back_edge_terminates_and_records_attempts():
    seen: list[str] = []

    async def loop(state):
        seen.append("loop")
        return NodeResult(state={"attempt": state.get("attempt", 0) + 1},
                          goto="loop" if state.get("attempt", 0) < 2 else None)

    graph = StateGraph("loop", {"loop": loop}, max_steps=6)
    out = await graph.run({"attempt": 0})
    assert out["attempt"] == 3
    assert len(seen) == 3


@pytest.mark.asyncio
async def test_a_node_that_keeps_wiring_back_to_itself_hits_the_step_cap():
    async def grow(state):
        return NodeResult(state={"n": state.get("n", 0) + 1}, goto="grow")

    graph = StateGraph("grow", {"grow": grow}, max_steps=4)
    with pytest.raises(StateGraphOverrun) as exc:
        await graph.run({"n": 0})
    assert "4" in str(exc.value)


@pytest.mark.asyncio
async def test_a_node_routing_to_an_unknowe_node_raises():
    async def stray(state):
        return NodeResult(state={}, goto="nowhere")

    graph = StateGraph("stray", {"stray": stray})
    with pytest.raises(ValueError, match="nowhere"):
        await graph.run({})


@pytest.mark.asyncio
async def test_every_step_merges_shallowly_without_mutating_input():
    async def picks(state):
        return NodeResult(state={"picked": state["x"]}, goto=None)

    graph = StateGraph("picks", {"picks": picks})
    src = {"x": "value"}
    out = await graph.run(src)
    assert out["picked"] == "value"
    assert src == {"x": "value"}, "node execution must not mutate the caller's state"
