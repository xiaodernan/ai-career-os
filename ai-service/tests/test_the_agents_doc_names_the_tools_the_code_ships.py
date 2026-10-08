"""AGENTS.md's subagent whitelists and tool table are the ones `tools.py` ships.

`docs/AGENTS.md` is the document a reader trusts to answer "what can this agent actually
do". Its §2 table is the load-bearing one: seven subagents, each with an explicit tool
whitelist, and the whole security argument for the design is that the interview agent
*physically cannot* save a job -- not that it is told not to. PRODUCT.md repeats that
claim, so it is not a throwaway sentence.

A whitelist that only exists in prose is a whitelist nobody audits. Adding a tool to
`rag` in `tools.py` is a one-line edit that grants every subagent sharing that entry a
new capability, and nothing in the repo would notice that the document describing the
boundary had stopped describing it. The same holds for §4's tool table: fifteen rows
naming each tool and the artifact it produces, which is what the UI renders.

So both tables are read out of the code and reconciled with the doc, in both directions.
The whitelists must match `SUBAGENT_TOOLS` exactly -- an entry the code grants that the
doc omits, and an entry the doc claims the code does not grant, both fail. The tool table
is matched on names against the `_t(...)` definitions, and on artifacts against what
`_collect_artifacts` can actually emit, because an artifact the orchestrator never
appends is a card the UI never draws.

The constants ride along for the same reason: §1 and §3 state the budget numbers
(`MAX_STEPS`, `MAX_SUB_STEPS`, `RESULT_CHARS`, the history window and its per-message
cap, the memory read limit and the extraction ceiling), and a reader sizing a prompt
against those numbers is sizing it against fiction if they move.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
DOC = ROOT / "docs" / "AGENTS.md"
TOOLS = ROOT / "ai-service" / "app" / "agents" / "tools.py"
ORCHESTRATOR = ROOT / "ai-service" / "app" / "agents" / "orchestrator.py"
MEMORY = ROOT / "ai-service" / "app" / "agents" / "memory.py"
CONVERSATION = (
    ROOT
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "careeros"
    / "conversation"
    / "service"
    / "ConversationService.java"
)

MINIMUM_TOOLS = 15
MINIMUM_SUBAGENTS = 7


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def section(start: str, end: str) -> str:
    text = read(DOC)
    return text[text.index(start) : text.index(end, text.index(start))]


def call_at(text: str, open_at: int) -> str:
    """Body of the call whose `(` sits at `open_at`, by paren depth."""
    depth = 0
    for index in range(open_at, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return text[open_at + 1 : index]
    raise AssertionError("unbalanced parentheses")


# ------------------------------------------------------------------ the whitelists


def code_whitelists() -> dict[str, list[str]]:
    """`SUBAGENT_TOOLS` as the code declares it."""
    text = read(TOOLS)
    block = text[text.index("SUBAGENT_TOOLS") :]
    block = block[: block.index("\n}\n") + 2]
    return {
        name: [
            t.strip().strip('"')
            for t in tools.replace("\n", " ").split(",")
            if t.strip()
        ]
        for name, tools in re.findall(r'"(\w+)":\s*\[(.*?)\]', block, re.S)
    }


def doc_whitelists() -> dict[str, list[str]]:
    """§2's table: subagent in the first cell, its tools in the second."""
    out: dict[str, list[str]] = {}
    for line in section(
        "## 2. Subagents and handoff", "Handoff is an explicit tool"
    ).split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or cells[0].startswith("---") or cells[0] == "Subagent":
            continue
        out[cells[0].strip("`")] = re.findall(r"`([^`]+)`", cells[1])
    return out


def test_the_subagent_whitelists_are_the_ones_the_code_ships():
    code, doc = code_whitelists(), doc_whitelists()
    assert len(code) >= MINIMUM_SUBAGENTS, (
        f"only {len(code)} subagents parsed from tools.py"
    )
    assert len(doc) >= MINIMUM_SUBAGENTS, (
        f"only {len(doc)} subagents parsed from AGENTS.md"
    )
    for agent in sorted(set(code) | set(doc)):
        assert code.get(agent) == doc.get(agent), (
            f"subagent {agent!r}: tools.py whitelists {code.get(agent)} and AGENTS.md §2 "
            f"documents {doc.get(agent)} -- the doc is the only place a reader can audit "
            f"what that agent may call"
        )


# ------------------------------------------------------------------- the tool table


def code_tools() -> dict[str, str | None]:
    """Every `_t(...)` definition: tool name -> declared artifact type."""
    text = read(TOOLS)
    out: dict[str, str | None] = {}
    for match in re.finditer(r"(?<!def )\b_t\(", text):
        body = call_at(text, match.end() - 1)
        name = re.match(r'\s*"([^"]+)"', body)
        if not name:
            continue
        artifact = re.search(r'artifact\s*=\s*"([^"]+)"', body)
        out[name.group(1)] = artifact.group(1) if artifact else None
    return out


def emitted_artifacts() -> set[str]:
    """Every artifact type `_collect_artifacts` can append to an outcome."""
    text = read(ORCHESTRATOR)
    body = text[text.index("def _collect_artifacts") :]
    body = body[: body.index("\ndef ", body.index("def _collect_artifacts") + 10)]
    return set(re.findall(r'{"type":\s*"([^"]+)"', body))


def doc_tools() -> dict[str, str | None]:
    """§4's table: tool name -> the artifact the doc says it produces."""
    out: dict[str, str | None] = {}
    for line in section("## 4. Tool system", "Tools read domain data directly").split(
        "\n"
    ):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0].startswith("---") or cells[0] == "Tool":
            continue
        claimed = re.findall(r"`([^`]+)`", cells[2])
        out[cells[0].strip("`")] = claimed[0] if claimed else None
    return out


def test_the_tool_table_names_every_tool_the_code_defines():
    code, doc = code_tools(), doc_tools()
    assert len(code) >= MINIMUM_TOOLS, f"only {len(code)} tools parsed from tools.py"
    assert len(doc) >= MINIMUM_TOOLS, f"only {len(doc)} tools parsed from AGENTS.md"
    assert sorted(code) == sorted(doc), (
        f"AGENTS.md §4 and tools.py disagree about which tools exist: "
        f"only in the doc {sorted(set(doc) - set(code))}, only in the code "
        f"{sorted(set(code) - set(doc))}"
    )


def test_every_artifact_the_tool_table_claims_is_one_the_orchestrator_emits():
    emitted = emitted_artifacts()
    assert len(emitted) >= 5, (
        f"only {len(emitted)} artifact types found in _collect_artifacts"
    )
    inert = sorted(
        {
            name
            for name, artifact in doc_tools().items()
            if artifact and artifact not in emitted
        }
    )
    assert inert == [], (
        f"AGENTS.md §4 says these tools produce an artifact the orchestrator never "
        f"appends: {inert} -- the UI renders `Outcome.artifacts`, so a card the doc "
        f"promises is a card nobody sees"
    )


# --------------------------------------------------------------------- the numbers


def constant(module: Path, name: str) -> str:
    """The value a constant is given, in either language the stack is written in.

    Python writes `MAX_STEPS = 8`; Java writes `private static final int HISTORY_TURNS = 12;`.
    Both are the same claim about the same number, so the same reader covers both.
    """
    found = re.search(rf"\b{name}\s*=\s*([^\s;]+)", read(module))
    assert found, f"{module.name} no longer defines {name}"
    return found.group(1)


def test_the_budget_numbers_the_doc_states_are_the_ones_the_code_uses():
    text = read(DOC)
    claims = {
        "MAX_STEPS = 8": constant(ORCHESTRATOR, "MAX_STEPS") == "8",
        "MAX_SUB_STEPS = 5": constant(ORCHESTRATOR, "MAX_SUB_STEPS") == "5",
        "RESULT_CHARS = 6000": constant(ORCHESTRATOR, "RESULT_CHARS") == "6000",
        "HISTORY_TURNS = 12": constant(ORCHESTRATOR, "HISTORY_TURNS") == "12",
    }
    wrong = [claim for claim, holds in claims.items() if not holds]
    assert wrong == [], f"AGENTS.md states {wrong} and the orchestrator disagrees"
    for phrase in ("MAX_STEPS = 8", "MAX_SUB_STEPS = 5", "RESULT_CHARS = 6000"):
        assert phrase in text, f"AGENTS.md no longer states {phrase}"
    assert "last 12 turns" in text and "4 000 chars each" in text
    assert re.search(r'str\(h\["content"\]\)\[:4000\]', read(ORCHESTRATOR)), (
        "the orchestrator no longer caps each history message at 4000 characters, which "
        "AGENTS.md §3 states as the window's shape"
    )
    assert constant(CONVERSATION, "HISTORY_TURNS") == "12"


def test_the_memory_numbers_the_doc_states_are_the_ones_the_code_uses():
    text = read(MEMORY)
    assert re.search(r"get_memories\(user_id,\s*limit=40\)", text), (
        "memory.py no longer reads up to 40 memories, which AGENTS.md §3 states"
    )
    assert re.search(r'for m in \(data\.get\("memories"\) or \[\]\)\[:4\]', text), (
        "memory.py no longer caps extraction at 4 facts, which AGENTS.md §3 states"
    )
    assert re.search(r"len\(content\) < 8", text), (
        "memory.py no longer rejects content shorter than 8 characters, which AGENTS.md "
        "§3 states as the floor"
    )
    for phrase in ("up to 40", "at most 4 durable facts"):
        assert phrase in read(DOC), f"AGENTS.md no longer states {phrase!r}"
