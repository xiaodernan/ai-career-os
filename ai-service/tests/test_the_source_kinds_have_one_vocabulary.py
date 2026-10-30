"""One vocabulary for source kinds, tied to the schema that defines it.

The nine kinds were written twice -- a literal in the query-understanding prompt and
a comment on `knowledge_sources.kind` -- and nowhere the model could see them, so
`search_knowledge_base` could only guess. A guess that misses (`notes` for `note`) is
dropped by `_clean_kinds`, which turns a scoped search into an unscoped one silently:
the answer cites a job description when the user asked about their notes.

`app/rag/kinds.py` is now the single source; the prompt and the tool schema derive
from it. This gate keeps it honest in the direction that matters -- the database can
hold a kind the code does not know about, and then nothing can filter on it.
"""

import re
from pathlib import Path

from app.agents import tools
from app.rag.kinds import KNOWLEDGE_KINDS

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "backend/src/main/resources/db/migration/V1__init_schema.sql"


def _declared_in_schema() -> set[str]:
    """The kinds the migration's own comment lists for `knowledge_sources.kind`."""
    sql = MIGRATION.read_text(encoding="utf-8", errors="replace")
    block = re.search(r"CREATE TABLE knowledge_sources \((.*?)\n\);", sql, re.S)
    assert block, "the knowledge_sources table is gone from the migration"
    line = re.search(r"kind\s+text[^\n]*--\s*([a-z_|]+)", block.group(1))
    assert line, "the kind column no longer documents its vocabulary"
    return set(line.group(1).split("|"))


def test_the_code_and_the_schema_agree_on_the_kinds():
    assert set(KNOWLEDGE_KINDS) == _declared_in_schema(), (
        "app/rag/kinds.py and `knowledge_sources.kind` disagree -- a kind the database "
        "can hold but the code does not name can never be filtered on, and a kind the "
        "code names but the database cannot hold makes every scoped search empty")


def test_the_kinds_are_unique_and_lower_snake_case():
    assert len(KNOWLEDGE_KINDS) == len(set(KNOWLEDGE_KINDS)), "a duplicate would hide"
    for kind in KNOWLEDGE_KINDS:
        assert re.fullmatch(r"[a-z]+(_[a-z]+)*", kind), f"{kind!r} is not snake_case"


def test_the_tool_schema_offers_the_whole_vocabulary():
    """The comment AGENTS.md makes about outreach applies here too: a list the handler
    accepts and the schema does not advertise is a shape the model cannot find."""
    schema = tools.TOOL_INDEX["search_knowledge_base"].spec().parameters
    offered = set(schema["properties"]["kinds"]["items"]["enum"])
    assert offered == set(KNOWLEDGE_KINDS), (
        f"the tool offers {sorted(offered)}; the store accepts {sorted(KNOWLEDGE_KINDS)}")
