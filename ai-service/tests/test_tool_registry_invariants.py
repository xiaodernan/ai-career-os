"""Structural invariants the live agent tool registry must satisfy.

These are cheap, import-time checks that catch accidental registry corruption:
duplicate names, empty metadata, or a handoff surface that disagrees with the
subagent whitelist the tools module declares.
"""

from app.agents import orchestrator
from app.agents.tools import ALL_TOOLS, SUBAGENT_TOOLS, TOOL_INDEX


def test_tool_names_are_unique_and_nonempty() -> None:
    names = [t.name for t in ALL_TOOLS]
    assert names, "registry is empty"
    assert len(names) == len(set(names)), f"duplicate tool names: {sorted(n for n in names if names.count(n) > 1)}"
    assert all(isinstance(n, str) and n.strip() for n in names), "tool names must be non-empty strings"
    assert all(isinstance(t.description, str) and t.description.strip() for t in ALL_TOOLS), (
        "every tool must have a non-empty description"
    )


def test_tool_index_matches_registry() -> None:
    assert set(TOOL_INDEX) == {t.name for t in ALL_TOOLS}
    for t in ALL_TOOLS:
        assert TOOL_INDEX[t.name] is t, f"TOOL_INDEX[{t.name!r}] is not the same instance"


def test_transfer_handoff_enum_matches_subagent_tools() -> None:
    # The orchestrator advertises transfer_to.agent as the subagent whitelist; that enum
    # must be exactly SUBAGENT_TOOLS' keys so the model can only hand off to real agents.
    enum = orchestrator.TRANSFER_SPEC.parameters["properties"]["agent"]["enum"]
    assert sorted(enum) == sorted(SUBAGENT_TOOLS), (
        f"transfer_to agent enum {sorted(enum)} != SUBAGENT_TOOLS keys {sorted(SUBAGENT_TOOLS)}"
    )
