"""docs/API.md section 4 is a script somebody is meant to run, not a sketch of one.

The endpoint tables are reconciled against the controllers
(`test_api_doc_contract.py` for the ai-service surface,
`test_the_backends_internal_surface_is_documented.py` for the backend's own), but the bash
block under "Worked examples" was written once and checked by eye. Two things had rotted by
the time this gate was written. The block curls `$B/resumes/$RID/parse` and
`$B/jobs/$JID/match` while assigning neither `RID` nor `JID`, so a copy-paste run asks for
`/resumes//parse` and reads the 404 as the API's answer. And it uploads a resume with
`-F title='Main resume'`, a multipart part `ResumeController.upload` does not bind -- the
same "binds by name, so an undeclared key is ignored, not rejected" rule the doc states two
sections earlier, applied to the doc's own example.

So the block is read as a script rather than as prose: every URL it curls has to be a route
a controller registers, every variable it interpolates has to have been assigned on an
earlier line, and every `-F` part has to be a parameter the handler declares. The
positive-control cases pin the population -- the block makes several requests, reads at
least one variable it captured itself, and sends at least one multipart part -- because a
block that did none of those things would pass all three checks vacuously.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
JAVA = ROOT / "backend" / "src" / "main" / "java"
DOC = ROOT / "docs" / "API.md"

MINIMUM_REQUESTS = 5
MINIMUM_CAPTURED = 2
MINIMUM_PARTS = 1

MAPPING = re.compile(r'@(Get|Post|Put|Patch|Delete)Mapping'
                     r'(?:\(\s*(?:value\s*=\s*)?"([^"]*)"\s*[,)])?')
BASE_MAPPING = re.compile(r'@RequestMapping\("([^"]+)"\)')
BINDING = re.compile(r'@Request(?:Param|Part)\("([^"]+)"')


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def norm(path: str) -> str:
    """One spelling for a path parameter, so `{id}` and `{resumeId}` are one route."""
    return re.sub(r"\{[^}]*\}|\*\*", "{}", path)


def worked_example() -> list[str]:
    """The section 4 bash block: continuations folded, comments and blanks dropped."""
    blocks = [b for b in re.findall(r"```bash\n(.*?)```", read(DOC), re.S) if "B=http" in b]
    assert len(blocks) == 1, f"{len(blocks)} bash blocks set the base URL, expected exactly 1"
    folded = blocks[0].replace("\\\n", " ")
    return [line.strip() for line in folded.split("\n")
            if line.strip() and not line.strip().startswith("#")]


def controllers() -> list[tuple[str, str]]:
    """(source text, class-level prefix) for every controller, prefix "" when it has none."""
    out = []
    for path in sorted(JAVA.rglob("*Controller.java")):
        text = read(path)
        base = BASE_MAPPING.search(text)
        out.append((text, base.group(1) if base else ""))
    return out


def backend_routes() -> set[tuple[str, str]]:
    """(VERB, path) for every route a backend controller registers."""
    out = set()
    for text, base in controllers():
        for match in MAPPING.finditer(text):
            out.add((match.group(1).upper(),
                     norm((base + (match.group(2) or "")).replace("//", "/"))))
    return out


def base_path() -> str:
    """The path the `B=` URL carries -- `/api/v1` -- which every request in the block builds on."""
    for line in worked_example():
        assigned = re.match(r"B=(\S+)", line)
        if assigned:
            return re.sub(r"^https?://[^/]+", "", assigned.group(1)).rstrip("/")
    raise AssertionError("the block never assigns B=, so no request it makes names a path")


def requests() -> list[dict]:
    """One entry per curl in the block: the verb, the path it asks for, the parts it sends."""
    out = []
    for line in worked_example():
        if "curl" not in line:
            continue
        url = re.search(r"\$B(/[^\s\"'|)]*)", line)
        assert url, f"a curl line names no URL: {line}"
        verb = re.search(r"-X\s+(\w+)", line)
        out.append({
            "verb": verb.group(1).upper() if verb else "GET",
            # a `$VAR` in a path is where a captured id goes: `/resumes/$RID/parse` is
            # `/resumes/{id}/parse` once the shell has expanded it
            "path": norm(re.sub(r"\$\w+", "{}", base_path() + url.group(1).split("?")[0])),
            "parts": re.findall(r"-F\s+([A-Za-z_]\w*)=", line),
            "line": line,
        })
    return out


def handler_window(verb: str, path: str) -> str | None:
    """The controller source around the mapping that answers (verb, path), if any."""
    for text, base in controllers():
        for match in MAPPING.finditer(text):
            if match.group(1).upper() != verb:
                continue
            if norm((base + (match.group(2) or "")).replace("//", "/")) != path:
                continue
            return text[match.start():match.start() + 900]
    return None


def test_every_url_the_block_curls_is_a_route_a_controller_registers():
    routes = backend_routes()
    problems = [f"{r['verb']} {r['path']} is not a route any controller registers: {r['line'][:80]}"
                for r in requests() if (r["verb"], r["path"]) not in routes]
    assert problems == [], "\n".join(problems)


def test_every_variable_the_block_reads_was_assigned_on_an_earlier_line():
    assigned: set[str] = set()
    problems = []
    for line in worked_example():
        for name in re.findall(r"\$(\w+)", line):
            if name not in assigned:
                problems.append(f"`${name}` is read before it is ever set, on: {line[:90]}")
        assigned.update(re.findall(r"^([A-Za-z_]\w*)=", line))
    assert problems == [], "\n".join(problems)


def test_every_multipart_part_the_block_sends_is_a_parameter_the_handler_binds():
    problems = []
    for request in requests():
        for part in request["parts"]:
            window = handler_window(request["verb"], request["path"])
            bound = BINDING.findall(window) if window else []
            if part not in bound:
                problems.append(
                    f"{request['verb']} {request['path']} binds {bound or 'no parameters'} "
                    f"but the example sends -F {part}=, which the handler drops without a word")
    assert problems == [], "\n".join(problems)


def test_the_block_is_a_real_script_and_not_a_vacuous_one():
    """Positive control: enough requests, captured variables and parts to fail on."""
    asked = requests()
    assert len(asked) >= MINIMUM_REQUESTS, (
        f"the block makes {len(asked)} requests, pinned at least {MINIMUM_REQUESTS}")
    captured = {name for line in worked_example()
                for name in re.findall(r"^([A-Za-z_]\w*)=", line)} - {"B"}
    assert len(captured) >= MINIMUM_CAPTURED, (
        f"the block captures {sorted(captured)}, pinned at least {MINIMUM_CAPTURED} values it "
        f"then interpolates -- otherwise the variable check above has nothing to hold")
    parts = [p for r in asked for p in r["parts"]]
    assert len(parts) >= MINIMUM_PARTS, (
        f"the block sends {len(parts)} multipart parts, pinned at least {MINIMUM_PARTS} -- "
        f"otherwise the binding check above has nothing to hold")
    routes = backend_routes()
    assert len(routes) > 20, f"only {len(routes)} backend routes walked; the parser is broken"
