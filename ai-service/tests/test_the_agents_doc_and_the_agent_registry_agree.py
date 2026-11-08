"""The agent registry the code ships and the contract `docs/AGENTS.md` describes must not drift.

AGENTS.md is the reader-facing contract for the orchestrator (loop bounds, memory window),
the tool system (count and names), and the subagent handoff (who exists, which tools each
may call). None of that is enforced by the type system: a tool added to `ALL_TOOLS` without
updating the doc, or a subagent's whitelist changed in code but not in the table, leaves the
doc and the product telling different stories. This gate reads both sides and fails on the
first disagreement.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS_DOC = ROOT / "docs" / "AGENTS.md"


def _doc_text() -> str:
    return AGENTS_DOC.read_text(encoding="utf-8")


def _registry():
    # Import the live registry: the gate measures what the app actually registers, not a
    # second copy of the same literals.
    from app.agents.tools import ALL_TOOLS, SUBAGENT_TOOLS, TOOL_INDEX
    from app.agents import orchestrator

    return ALL_TOOLS, SUBAGENT_TOOLS, TOOL_INDEX, orchestrator


def _tools_table_names(text: str) -> list[str]:
    """Tool names in AGENTS.md §4 table, in order."""
    names = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("## 4."):
            in_table = False
            continue
        if line.startswith("| Tool | Purpose |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            if names:
                break
            continue
        if re.match(r"^\|\s*-", line):
            continue
        m = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
        if m:
            names.append(m.group(1))
    return names


def _subagent_table(text: str) -> dict[str, list[str]]:
    """Subagent -> tool list from AGENTS.md §2 table."""
    out: dict[str, list[str]] = {}
    in_table = False
    for line in text.splitlines():
        if line.startswith("## 2."):
            in_table = False
            continue
        if line.startswith("| Subagent | Tools |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            if out:
                break
            continue
        if re.match(r"^\|\s*-", line):
            continue
        m = re.match(r"^\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|", line)
        if not m:
            continue
        agent = m.group(1)
        tools = re.findall(r"`([^`]+)`", m.group(2))
        out[agent] = tools
    return out


def test_tool_registry_matches_agents_doc():
    text = _doc_text()
    ALL_TOOLS, SUBAGENT_TOOLS, TOOL_INDEX, _ = _registry()

    registry_names = [t.name for t in ALL_TOOLS]
    doc_names = _tools_table_names(text)

    assert len(ALL_TOOLS) == 26, f"ALL_TOOLS count drifted: {len(ALL_TOOLS)}"
    assert "26 tools in `agents/tools.py`" in text, "AGENTS.md §4 must state the tool count"
    assert set(registry_names) == set(TOOL_INDEX), "TOOL_INDEX keys must equal ALL_TOOLS names"
    assert sorted(registry_names) == sorted(doc_names), (
        f"tool names differ: only-in-registry={sorted(set(registry_names)-set(doc_names))} "
        f"only-in-doc={sorted(set(doc_names)-set(registry_names))}"
    )
    assert len(doc_names) == 26, f"AGENTS.md tool table row count drifted: {len(doc_names)}"


def test_subagents_match_agents_doc():
    text = _doc_text()
    _, SUBAGENT_TOOLS, TOOL_INDEX, _ = _registry()
    doc_agents = _subagent_table(text)

    assert "Eight subagents" in text, "AGENTS.md §2 must state the subagent count"
    assert len(SUBAGENT_TOOLS) == 8, f"subagent count drifted: {len(SUBAGENT_TOOLS)}"
    assert set(SUBAGENT_TOOLS) == set(doc_agents), (
        f"subagent names differ: registry={sorted(SUBAGENT_TOOLS)} doc={sorted(doc_agents)}"
    )
    for agent, tools in SUBAGENT_TOOLS.items():
        missing = [t for t in tools if t not in TOOL_INDEX]
        assert not missing, f"subagent {agent} references unknown tools: {missing}"
        assert set(tools) == set(doc_agents[agent]), (
            f"subagent {agent} tool list drifted: registry={tools} doc={doc_agents[agent]}"
        )


def test_orchestrator_bounds_match_agents_doc():
    text = _doc_text()
    _, _, _, orchestrator = _registry()

    assert orchestrator.MAX_STEPS == 8
    assert orchestrator.MAX_SUB_STEPS == 5
    assert orchestrator.RESULT_CHARS == 6000
    assert "`MAX_STEPS = 8`" in text
    assert "`MAX_SUB_STEPS = 5`" in text
    assert "`RESULT_CHARS = 6000`" in text
    # Conversation window and memory read are stated claims; pin the code side too.
    assert getattr(orchestrator, "HISTORY_TURNS", None) == 12
    assert "last 12 turns" in text


def test_memory_read_limit_matches_agents_doc():
    text = _doc_text()
    mem = (ROOT / "ai-service" / "app" / "agents" / "memory.py").read_text(encoding="utf-8")
    assert "up to 40" in text
    assert re.search(r"get_memories\([^)]*limit\s*=\s*40", mem), (
        "memory.build_memory_context must read up to 40 memories (AGENTS.md §3)"
    )
