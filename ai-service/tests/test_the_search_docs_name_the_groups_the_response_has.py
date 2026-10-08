"""Every group list a document writes is `SearchResponse`'s own, and product-plan's counts are the code's.

`GET /api/v1/search` answers one object whose components *are* the ⌘K palette's groups. Two
documents spelled that list out longhand -- API.md's route table and product-plan's F8.3 -- and
both named `interviews` and `KB`, fields the response does not have, while omitting
`applications`, which it does. Nothing failed: the route-table gate reads paths and verbs and
never the prose beside them, and the frontend already pins its own decode table to the DTO
(`frontend/src/lib/api/normalize.test.ts`). A reader following either sentence hunts for a
search over interview sessions that does not exist and never learns the tracker's applications
are searchable -- and the missing half is the worse one, because applications are what a job
seeker actually comes back to.

So the list is read out of the record that defines it, and the whole docs tree is swept for
slash-separated runs of group names rather than a hand-copied table: the next copy somebody
pastes is checked the moment it lands, in whichever document it lands in.

The rest of product-plan.md's countable claims are pinned the same way. A roadmap is the
document a reader trusts for "how big is this thing and what is in it", and every number in it
has an author in the tree: the tool registry, the interview rubric, the seed script, the
schema's own status comment, the upload validator.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
AI = TESTS.parent
ROOT = AI.parent
PLAN = ROOT / "docs" / "product-plan.md"
SEED = ROOT / "scripts" / "seed" / "01_jobs.sql"
DTO = (ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "search" / "dto"
       / "SearchDtos.java")
FILE_TYPES = (ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "storage"
              / "FileValidator.java")
SCHEMA = ROOT / "backend" / "src" / "main" / "resources" / "db" / "migration" / "V1__init_schema.sql"
TOOLS = AI / "app" / "agents" / "tools.py"
INTERVIEW = AI / "app" / "features" / "interview.py"
DOCS = sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"]

# Words that can appear in a group list. The two the response does not carry are in here on
# purpose: a run naming them has to be caught, not skipped.
GROUP_VOCABULARY = {
    "jobs", "companies", "resumes", "notes", "conversations", "applications",
    "interviews", "kb",
}


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def split_top_level(text: str) -> list[str]:
    """Comma-separated parts, ignoring commas inside (), [] or <>."""
    parts: list[str] = []
    depth = 0
    current = ""
    for char in text:
        if char in "<([{":
            depth += 1
        elif char in ">)]}":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return [part.strip() for part in parts if part.strip()]


def response_groups() -> list[str]:
    """`SearchResponse`'s components minus `query`, in declaration order."""
    match = re.search(r"record SearchResponse\((.*?)\)\s*\{", read(DTO), re.S)
    assert match, "SearchDtos.java no longer declares a SearchResponse record"
    names = [re.search(r"(\w+)$", part).group(1) for part in split_top_level(match.group(1))]
    return [name for name in names if name != "query"]


def doc_group_runs() -> list[tuple[str, int, str]]:
    """(document, line, run) for every slash-run of group names any document writes."""
    found: list[tuple[str, int, str]] = []
    for path in DOCS:
        for number, line in enumerate(read(path).split("\n"), 1):
            for run in re.findall(r"[A-Za-z]+(?:/[A-Za-z]+){3,}", line):
                tokens = run.split("/")
                if sum(1 for token in tokens if token.lower() in GROUP_VOCABULARY) >= 4:
                    found.append((path.name, number, run))
    return found


def seed_roles() -> int:
    """How many job rows the seed script inserts.

    A tuple counts only when a comma follows its closing paren: the `) AS v(...)` closer and
    `ON CONFLICT (id)` both open and shut a paren without being rows, and counting either
    inflates the census by exactly the kind of one a census cannot afford.
    """
    body = read(SEED)[read(SEED).index("INSERT INTO jobs"):]
    index = body.index("VALUES") + len("VALUES")
    depth = 0
    rows = 0
    while index < len(body):
        char = body[index]
        if char == "(":
            if depth == 0:
                rows += 1
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0 and not body[index + 1:].lstrip().startswith(","):
                break
        index += 1
    return rows


def plan_claim(pattern: str, what: str) -> re.Match:
    match = re.search(pattern, read(PLAN))
    assert match, f"product-plan.md no longer states {what}"
    return match


def test_every_group_list_a_document_writes_is_the_responses_own():
    runs = doc_group_runs()
    assert len(runs) >= 2, (
        f"only {len(runs)} group lists found across the docs; the sweep has stopped seeing "
        "them, so API.md and product-plan.md are no longer held to SearchResponse")
    expected = "/".join(response_groups())
    wrong = [f"{name}:{line} says {run}" for name, line, run in runs if run != expected]
    assert wrong == [], (
        f"the ⌘K palette answers {expected}; these documents disagree: {wrong}")


def test_the_response_carries_a_real_set_of_groups():
    groups = response_groups()
    assert len(groups) >= 5, f"only {len(groups)} groups parsed from SearchResponse: {groups}"
    assert len(set(groups)) == len(groups), f"SearchResponse names a group twice: {groups}"


def test_the_tool_count_the_plan_claims_is_the_registrys():
    shipped = len(re.findall(r'^\s+_t\("', read(TOOLS), re.M))
    claimed = int(plan_claim(r"Tool system \((\d+) tools", "how many tools the agent has").group(1))
    assert claimed == shipped, (
        f"product-plan.md says {claimed} tools and tools.py registers {shipped}")


def test_the_interview_dimension_count_the_plan_claims_is_the_one_the_feature_declares():
    block = re.search(r"DIMENSIONS\s*=\s*\[(.*?)\]", read(INTERVIEW), re.S)
    assert block, "interview.py no longer declares its DIMENSIONS rubric"
    declared = len(re.findall(r'"([a-z_]+)"', block.group(1)))
    claimed = int(plan_claim(r"final evaluation \((\d+) dimensions", "an interview dimension count")
                  .group(1))
    assert claimed == declared, (
        f"product-plan.md says {claimed} interview dimensions and interview.py declares "
        f"{declared}")


def test_the_seeded_corpus_the_plan_claims_is_the_one_the_seed_inserts():
    roles = seed_roles()
    claimed = int(plan_claim(r"Seed dataset: ~(\d+) realistic jobs", "a seed corpus size").group(1))
    assert claimed <= roles <= claimed * 1.25, (
        f"product-plan.md says ~{claimed} jobs and scripts/seed/01_jobs.sql inserts {roles}")


def test_the_kanban_stages_the_plan_lists_are_the_schemas_own():
    schema = re.search(r"DEFAULT 'saved',\s*--\s*([^\n]+)", read(SCHEMA))
    assert schema, "the schema no longer comments the application statuses it defaults to"
    declared = [stage.strip() for stage in schema.group(1).strip().split("|")]
    listed = plan_claim(r"Kanban \(([^)]+)\)", "the Kanban's stages").group(1)
    claimed = [stage.strip() for stage in listed.split("→")]
    assert claimed == declared, (
        f"product-plan.md lists the Kanban as {claimed} and the schema declares {declared}")


def test_the_upload_formats_the_plan_names_are_the_validators_own():
    block = re.search(r"enum Type \{(.*?)\}", read(FILE_TYPES), re.S)
    assert block, "FileValidator no longer declares the types it accepts"
    # All-caps only: the enum body also holds its `Type(String mediaType)` constructor.
    declared = [name.lower() for name in re.findall(r"^\s+([A-Z]{2,})\(", block.group(1), re.M)]
    claimed = [fmt.strip().lower()
               for fmt in plan_claim(r"Upload \(([^)]+)\)", "the upload formats").group(1).split("/")]
    assert claimed == declared, (
        f"product-plan.md names {claimed} as the upload formats and FileValidator sniffs for "
        f"{declared}")
