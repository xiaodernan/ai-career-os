"""A tool that changes the world must say so, or the answered-cache serves stale reads.

`_run_loop` reuses a successful tool result when the model re-issues the identical
call, and it clears that cache after a `write=True` tool runs -- otherwise "save this
job, then show me my pipeline" answers with the pipeline as it was before the save,
from a cache entry that was correct a second earlier.

The flag cannot be derived from a tool's name, so it is declared on each `Tool`. A
declaration that can be forgotten needs a gate that reads the handlers themselves:
this one looks for writing SQL in the body of every tool that does *not* claim to
write, and pins the set of tools that do.
"""

import inspect
import re

import pytest

from app.agents import tools

WRITING_SQL = re.compile(r"\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b", re.I)
TOOL_WRITE = {t.name: t.write for t in tools.ALL_TOOLS}

# The tools that change stored state. `calculate_match` writes through
# `features.match.persist_match` rather than inline SQL, which is why it has to be
# named here instead of being found by the scan below.
EXPECTED_WRITERS = {
    "calculate_match",      # persists the match it computed
    "create_interview",     # inserts an interview session
    "save_job",             # saved_jobs + a `saved` application
    "update_application_status",
    "log_contact_touch",
}


def _handlers_with_writing_sql() -> list[str]:
    found = []
    for tool in tools.ALL_TOOLS:
        try:
            source = inspect.getsource(tool.handler)
        except (OSError, TypeError):  # a lambda or a builtin has no readable body
            continue
        if WRITING_SQL.search(source):
            found.append(tool.name)
    return found


def test_no_tool_writes_without_declaring_it():
    undeclared = [name for name in _handlers_with_writing_sql()
                  if not TOOL_WRITE[name]]
    assert undeclared == [], (
        f"{undeclared} run writing SQL but do not declare write=True -- the answered-cache "
        "will keep serving the pre-write answer for the rest of the turn")


def test_the_set_of_writing_tools_is_the_one_this_gate_names():
    declared = {t.name for t in tools.ALL_TOOLS if t.write}
    assert declared == EXPECTED_WRITERS, (
        f"the registry declares {sorted(declared)}; this gate names "
        f"{sorted(EXPECTED_WRITERS)}. A new writer belongs in both -- and a tool that "
        "stopped writing should leave both, or the cache stands down for no reason")


def test_the_declared_writers_really_do_write_something():
    """The other direction: a flag without a write is a cache cleared for nothing."""
    with_sql = set(_handlers_with_writing_sql())
    indirect = EXPECTED_WRITERS - with_sql
    assert indirect == {"calculate_match"}, (
        f"these tools declare write=True but no longer run writing SQL: "
        f"{sorted(indirect)} -- if a write moved into a feature module, say so here; "
        "if it disappeared, drop the flag")


@pytest.mark.parametrize("name", sorted(EXPECTED_WRITERS))
def test_each_declared_writer_is_in_the_registry(name):
    assert name in TOOL_WRITE, f"{name} is no longer a shipped tool"
