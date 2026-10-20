"""Every number in the prose that counts tools is counted from a file that has the list.

Five places in this repository tell a reader how many agent tools there are. Three of
them are wrong by eight, and the wrong ones are the two a newcomer reads first:
`README.md`'s architecture table says "19 domain tools", `docs/architecture.md`'s tree
annotation says `tools/ (19 tools)` and its §6.4 says "15 domain tools". `docs/AGENTS.md`
says 23 and `docs/product-plan.md` says 23, which is what `app/agents/tools.py`
registers. A count that disagrees with the roster is not only untidy: the README figure
is how someone judges whether the agent described is the agent that runs, and the tree
annotation is the only place the module's size is stated at all.

The fourteenth claim is different, and the gate has to know that. §6.4's "15 domain
tools per PRD §18" is a *citation*: PRD §18 ("Agent Tool System") lists fifteen names and
asks for at least those, so the sentence is true about the requirement and stale about the
ship. Grading it against `tools.py` would be a false red -- the same mistake as blaming a
test for asserting a number the referenced file really does hold. So each claim is graded
against the referent its own sentence names: the PRD's list when the paragraph cites the
tool-system section, the registered roster otherwise. That is also what makes the
citation checkable instead of decorative: delete "per PRD §18" and the same 15 becomes a
ship claim, and fails.

Both numbers are read out of files, never typed into this gate: the roster from the `_t()`
definitions, the PRD list from the code block under the section whose *heading* names the
tool system (its number is looked up, not hard-coded). And the PRD's list is checked in
the other direction too -- every tool it promises must be one the code registers, since
"at least" is a floor, and a missing name is a requirement nobody notices was dropped.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
TOOLS = ROOT / "ai-service" / "app" / "agents" / "tools.py"
PRD = ROOT / "docs" / "MASTER_PROMPT.md"
CARRIERS = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]

CLAIM_RE = re.compile(r"(?:^|[^A-Za-z0-9])(\d+)\s+(?:[a-z]+\s+){0,2}?tools\b")
MIN_CLAIMS = 5
MIN_CLAIM_FILES = 3
MIN_SHIPPED = 19
MIN_PROMISED = 10


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def shipped_tools() -> list[str]:
    """Every tool `tools.py` registers, in file order."""
    return re.findall(r'_t\(\s*"([a-z_]+)"', read(TOOLS))


def prd_tool_system() -> tuple[int, list[str]]:
    """The PRD section that specifies the tool system: its number and the names it lists."""
    text = read(PRD)
    heading = re.search(r"^# (\d+)\.\s.*[Tt]ool [Ss]ystem.*$", text, re.M)
    assert heading, "MASTER_PROMPT.md no longer has a numbered tool-system section"
    number = int(heading.group(1))
    body = text[heading.end():]
    nxt = re.search(r"^# \d+\.", body, re.M)
    body = body[: nxt.start()] if nxt else body
    block = re.search(r"```(?:text)?\n(.*?)```", body, re.S)
    assert block, f"PRD section {number} no longer lists its tools in a fenced block"
    names = [line.strip() for line in block.group(1).splitlines()
             if re.fullmatch(r"[a-z][a-z0-9_]*", line.strip())]
    return number, names


def claims() -> list[dict]:
    """Every prose number that counts tools, with the paragraph that says it."""
    out: list[dict] = []
    for path in CARRIERS:
        lines = read(path).split("\n")
        for index, line in enumerate(lines, 1):
            for match in CLAIM_RE.finditer(line):
                out.append({
                    "where": f"{path.name}:{index}",
                    "number": int(match.group(1)),
                    "text": line.strip(),
                    "paragraph": paragraph(lines, index - 1),
                })
    return out


def paragraph(lines: list[str], offset: int) -> str:
    """The wrapped block around the claim: citations and numbers are rarely on one line."""
    start = offset
    while start > 0 and lines[start - 1].strip():
        start -= 1
    end = offset
    while end + 1 < len(lines) and lines[end + 1].strip():
        end += 1
    return " ".join(lines[start:end + 1])


def referent(claim: dict, prd_number: int, promised: list[str]) -> tuple[str, int]:
    """Which list the claim's own sentence points at, and how long that list is."""
    if re.search(rf"PRD\s*§{prd_number}\b", claim["paragraph"]):
        return f"PRD §{prd_number}'s list", len(promised)
    return "the roster tools.py registers", len(shipped_tools())


def test_the_census_finds_the_claims_it_is_there_to_grade():
    found, files = claims(), {claim["where"].split(":")[0] for claim in claims()}
    assert len(found) >= MIN_CLAIMS, f"only {len(found)} tool counts parsed: {found}"
    assert len(files) >= MIN_CLAIM_FILES, f"only {sorted(files)} carry a count"
    assert len(shipped_tools()) >= MIN_SHIPPED
    number, promised = prd_tool_system()
    assert len(promised) >= MIN_PROMISED, f"PRD §{number} lists only {len(promised)}"
    graded = [referent(claim, number, promised)[0] for claim in found]
    assert set(graded) != {graded[0]}, (
        "every claim resolved to one referent -- the citation branch is then untested, "
        f"and a wrong number passes by matching the wrong list: {graded}"
    )


def test_every_number_that_counts_tools_matches_the_list_its_sentence_names():
    number, promised = prd_tool_system()
    wrong = []
    for claim in claims():
        source, expected = referent(claim, number, promised)
        if claim["number"] != expected:
            wrong.append(
                f"{claim['where']} says {claim['number']} but {source} holds {expected} "
                f"({claim['text'][:70]!r})"
            )
    assert wrong == [], (
        "a reader sizes the agent against these numbers:\n  " + "\n  ".join(wrong)
    )


def test_every_tool_the_prd_promised_is_a_tool_the_code_registers():
    number, promised = prd_tool_system()
    missing = sorted(set(promised) - set(shipped_tools()))
    assert missing == [], (
        f"PRD §{number} asks for at least {len(promised)} tools and {missing} are not in "
        "`tools.py` -- the floor is unmet and the docs counting the roster agree with a "
        "shorter list than the requirement"
    )


def test_the_shipped_roster_has_no_duplicate_registration():
    names = shipped_tools()
    duplicated = sorted({name for name in names if names.count(name) > 1})
    assert duplicated == [], (
        f"{duplicated} is registered twice, so the roster's length is not the number of "
        "tools and every count graded above is graded against a bad denominator"
    )
