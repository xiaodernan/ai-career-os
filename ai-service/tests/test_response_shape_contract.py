"""The return direction of the backend <-> ai-service boundary: keys read off an AI answer.

`HttpAiServiceClient` hands its callers a bare `Map<String, Object>` and each consumer picks
values out with `Json.str(result, "answer")` / `result.get("artifacts")`. Every one of those
reads is silent when the key is missing: `Json.strOr` falls back to `""`, `Json.obj` to an
empty map, `Json.arr` to an empty list. If `/internal/agents/chat/sync` renamed `answer`, the
copilot would keep replying -- with an empty bubble -- and nothing anywhere would fail.

The producer side needs no parser guesswork: ai-service is Python, so handlers are walked with
`ast`, following `return out` / `return fn(...)` / `return out.to_dict()` one hop to where the
literal dict is actually built. The consumer side is Java, read the way the request-side gate
reads it: which local or parameter holds an AI answer, and which keys get read off it --
including the maps drilled out of it, one level down.
"""

import ast
import inspect
import re
from collections import namedtuple
from functools import lru_cache
from pathlib import Path

from fastapi.routing import APIRoute

from tests.test_internal_contract import (
    AI_PACKAGE,
    _argument_list,
    _calls,
    _java_methods,
    _routes,
    _top_level,
)

JAVA_ROOT = AI_PACKAGE.parents[2]
ROOT_FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"


def _app_root() -> Path:
    import app.main

    return Path(app.main.__file__).resolve().parent


# ------------------------------------------------------------- python: what comes back

def _index_defs() -> tuple[dict[str, list], dict[str, str], dict[str, list]]:
    """Functions by name, the names that exist only because an import renamed them, and the
    Pydantic models.

    `from app.features.cover_letter import generate as cover_generate` means the handler's
    `await cover_generate(...)` has no def to follow by that name: without the alias, that
    endpoint's answer reads as invisible -- and a shape the gate cannot read is a shape it
    never checks.

    A model matters the same way. `/internal/features/match` answers with
    `result = MatchResult(...)` then `result.model_dump()`: no function builds those keys, the
    *class* does, and its annotated fields are exactly what `model_dump` emits.
    """
    defs: dict[str, list] = {}
    models: dict[str, list] = {}
    aliased: dict[str, set] = {}
    for path in sorted(_app_root().rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs.setdefault(node.name, []).append(node)
            elif isinstance(node, ast.ClassDef):
                if any(getattr(b, "id", getattr(b, "attr", None)) in {"BaseModel", "Model"}
                       for b in node.bases):
                    models.setdefault(node.name, []).append(node)
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    if a.asname:
                        aliased.setdefault(a.asname, set()).add(a.name)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.asname:
                        aliased.setdefault(a.asname, set()).add(a.name.rsplit(".", 1)[-1])
    return defs, {k: next(iter(v)) for k, v in aliased.items() if len(v) == 1}, models


DEFS, ALIASES, MODELS = _index_defs()


def _model(name: str):
    """The one Pydantic model class under `name`, or None."""
    found = MODELS.get(name) or MODELS.get(ALIASES.get(name, "")) or []
    return found[0] if len(found) == 1 else None


def _model_fields(node) -> set[str]:
    """What `model_dump()` will emit: the annotated names, `model_config` and privates aside."""
    return {stmt.target.id for stmt in node.body
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            and not stmt.target.id.startswith("_")}


def pydantic_fields(name: str) -> set[str]:
    """The keys a model puts on the wire, for a gate in another file to check its reads against."""
    node = _model(name)
    if node is None:
        raise AssertionError(f"{name} is not exactly one BaseModel subclass under app/: the table "
                             "names a producer that moved, so the rule it feeds compares nothing")
    return _model_fields(node)


def _sole(name: str):
    """The one definition of `name` -- or of whatever it was imported as -- or None."""
    found = DEFS.get(name) or DEFS.get(ALIASES.get(name, "")) or []
    return found[0] if len(found) == 1 else None


def _returns(fn) -> list[ast.Return]:
    """Returns belonging to `fn` itself, not to a function nested inside it."""
    out, stack = [], [fn]
    while stack:
        node = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Return):
                out.append(child)
            elif not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                stack.append(child)
    return out


Shape = dict  # key -> nested keys of that value, or None when that value is not a visible map


def _called_name(node: ast.AST) -> str | None:
    """`fn(...)`, `mod.fn(...)` and `x.to_dict()` each name the definition to follow."""
    if isinstance(node, ast.Await):
        node = node.value
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    return func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)


def _assigned_call(fn, variable: str) -> str | None:
    """The call whose result was bound to `variable`: `out = await iv.advance(...)`."""
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == variable for t in node.targets):
            name = _called_name(node.value)
            if name:
                return name
    return None


def _dumped(node: ast.AST, fn) -> str | None:
    """`x.model_dump()` names the model whose fields `x` holds, via the call that built it."""
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"model_dump", "dict"} and isinstance(node.func.value, ast.Name)):
        return _assigned_call(fn, node.func.value.id)
    return None


def _follow(node: ast.AST, fn, hops: int) -> Shape | None:
    """The shape of a returned expression: a literal, or a hop into where it is built.

    Two hops is the deepest chain on this boundary today -- the interview handler returns
    `nxt`, which `advance` returns from `decide_next` -- and the budget is bounded so a wide
    search cannot turn into a guess.
    """
    if isinstance(node, ast.Dict):
        literal = [k.value for k in node.keys
                   if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        if len(literal) != len(node.keys):
            return None  # a computed or **spread key: the shape is not statically visible
        return {key: _subshape(value, fn, hops + 1) for key, value in zip(literal, node.values)}
    if hops > 2:
        return None
    name = _called_name(node)
    if name in {"model_dump", "dict"}:
        name = _dumped(node, fn) or name
    if name is None and isinstance(node, ast.Name):
        name = _assigned_call(fn, node.id)
    target = _sole(name) if name else None
    if target is not None:
        return _shape_of(target, hops + 1)
    model = _model(name) if name else None
    # A model's own values are typed, not literal dicts, so they stay unseen -- the field names
    # are what this boundary needs, and `model_dump` is what puts them on the wire.
    return dict.fromkeys(_model_fields(model)) if model is not None else None


def _subshape(value: ast.AST, fn, hops: int) -> set | None:
    """Keys of a nested map field, when they can be named without guessing."""
    if isinstance(value, ast.Dict):
        literal = [k.value for k in value.keys
                   if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        return None if len(literal) != len(value.keys) else set(literal)
    shape = _follow(value, fn, hops)
    return None if shape is None else set(shape)


def _merge(paths: list[Shape]) -> Shape | None:
    """Keys every return path provides; a shape unknown on any path is unknown overall."""
    if not paths:
        return None
    merged = dict(paths[0])
    for other in paths[1:]:
        for key in list(merged):
            if key not in other:
                merged.pop(key)
            elif merged[key] is None or other[key] is None:
                merged[key] = None
            else:
                merged[key] = merged[key] & other[key]
    return merged


def _shape_of(fn, hops: int = 0) -> Shape | None:
    if fn is None:
        return None
    paths = []
    for ret in _returns(fn):
        # a bare `return` means this path answers with None, so no key set is guaranteed
        shape = _follow(ret.value, fn, hops) if ret.value is not None else None
        if shape is None:
            return None
        paths.append(shape)
    return _merge(paths)


def _returned(route: APIRoute) -> Shape | None:
    """What an endpoint answers with: top-level keys, and the nested keys of each of them."""
    body = ast.parse(inspect.getsource(route.endpoint)).body[0]
    return _shape_of(body)


# ------------------------------------------------------------------ java: what gets read

Endpoint = namedtuple("Endpoint", "verb path via")
BY_CLIENT_METHOD = {c["via"]: Endpoint(c["verb"], c["path"], c["via"]) for c in _calls()}
Flow = namedtuple("Flow", "file method var clients")

_READS = (r'Json\.\w+\(\s*{var}\s*,\s*"(\w+)"', r'\b{var}\.get\(\s*"(\w+)"\s*\)')
_NESTED = (r'Map<String,\s*Object>\s+(\w+)\s*=\s*Json\.\w+\(\s*{var}\.get\(\s*"(\w+)"\s*\)\s*\)',
           r'Map<String,\s*Object>\s+(\w+)\s*=\s*(?:\([^)]*\)\s*)?{var}\.get\(\s*"(\w+)"\s*\)')


@lru_cache(maxsize=None)
def _methods_of(path: Path) -> dict:
    return {m.name: m for m in _java_methods(path.read_text(encoding="utf-8"))}


def _consumer_files() -> list[Path]:
    """Backend classes that reach ai-service through the injected client field."""
    return sorted(p for p in JAVA_ROOT.rglob("*.java")
                  if re.search(r"\bai\.\w+\(", p.read_text(encoding="utf-8")))


def _sinks(path: Path, method, var: str) -> list[tuple]:
    """Same-class calls in `method` that `var` is passed into, with the argument position."""
    out = []
    methods = _methods_of(path)
    for match in re.finditer(r"(?<![\w.])(\w+)\(", method.body):
        callee = methods.get(match.group(1))
        if callee is None or callee is method:
            continue
        inner, _ = _argument_list(method.body, match.end() - 1)
        for position, arg in enumerate(_top_level(inner, ",")):
            if arg == var:
                out.append((callee, position))
    return out


def _flows() -> list[Flow]:
    """Which variables hold an AI answer, followed through same-class calls.

    A result is usually read two methods away from the request (`importJob` calls
    `persistImport(userId, request, result)`), so a local binding is propagated into the
    parameter it is passed to until nothing new appears.
    """
    flows: dict[tuple, set] = {}
    for path in _consumer_files():
        for method in _methods_of(path).values():
            for match in re.finditer(r"Map<String, Object>\s+(\w+)\s*=\s*ai\.(\w+)\(",
                                     method.body):
                flows.setdefault((path, method.name, match.group(1)), set()).add(match.group(2))
    for _ in range(6):
        added = False
        for (path, method_name, var), clients in list(flows.items()):
            for callee, position in _sinks(path, _methods_of(path)[method_name], var):
                if position >= len(callee.params):
                    continue
                key = (path, callee.name, callee.params[position][0])
                before = set(flows.get(key, set()))
                flows.setdefault(key, set()).update(clients)
                added = added or flows[key] != before
        if not added:
            break
    return [Flow(path, method, var, clients) for (path, method, var), clients in flows.items()]


def _reads_of(path: Path, method_name: str, var: str) -> tuple[set, list]:
    """Keys read straight off an AI answer, and the nested maps drilled out of it."""
    body = _methods_of(path)[method_name].body
    reads = {m.group(1) for pattern in _READS for m in re.finditer(pattern.format(var=var), body)}
    nested = [{"key": m.group(2), "var": m.group(1),
               "reads": {k for pattern in _READS
                         for k in re.findall(pattern.format(var=m.group(1)), body)}}
              for pattern in _NESTED for m in re.finditer(pattern.format(var=var), body)]
    return reads, nested


def reads_by_endpoint() -> dict[Endpoint, dict]:
    """Per internal endpoint: what the backend reads off its answer, and where."""
    out: dict[Endpoint, dict] = {}
    for flow in _flows():
        for client in sorted(flow.clients):
            endpoint = BY_CLIENT_METHOD[client]
            reads, nested = _reads_of(flow.file, flow.method, flow.var)
            entry = out.setdefault(endpoint, {"reads": set(), "nested": [], "sites": []})
            entry["reads"] |= reads
            site = f"{flow.file.name}#{flow.method}"
            entry["nested"] += [dict(item, site=site) for item in nested]
            entry["sites"].append(f"{site}.{flow.var}")
    return out


def _route(endpoint: Endpoint) -> APIRoute:
    return _routes()[(endpoint.verb, endpoint.path)]


# ---------------------------------------------------------------- the reconciliations

# ---------------------------------------------------------------- the reconciliations

def _findings() -> tuple[list[str], list[str]]:
    """(drifts, blind spots): keys read that no answer carries, and nested shapes unseen."""
    problems, unseen = [], []
    for endpoint, entry in reads_by_endpoint().items():
        shape = _returned(_route(endpoint))
        where = f"{endpoint.verb} {endpoint.path}"
        if shape is None:
            problems.append(f"{where} <- {entry['sites']} reads keys off an answer whose "
                            "shape this gate cannot read")
            continue
        phantom = sorted(entry["reads"] - set(shape))
        if phantom:
            problems.append(f"{where} <- {entry['sites']} reads {phantom}, which the answer "
                            "never carries")
        for nested in entry["nested"]:
            if nested["key"] not in shape:
                problems.append(f"{where} <- {nested['site']} drills into {nested['key']!r}, "
                                "which the answer never carries")
                continue
            keys = shape[nested["key"]]
            if keys is None:
                unseen.append(f"{endpoint.path}#{nested['key']}")
                continue
            extra = sorted(nested["reads"] - keys)
            if extra:
                problems.append(f"{where} <- {nested['site']}.{nested['var']} reads {extra}, "
                                f"which {nested['key']!r} does not carry")
    return problems, sorted(set(unseen))


def test_the_backend_reads_only_keys_the_answer_returns():
    """Two levels deep: a wrong top-level key blanks a field, a wrong nested one silently
    drops a follow-up question or a score, and both read as an empty value, never an error."""
    problems, _unseen = _findings()
    assert problems == [], "\n".join(problems)


def test_the_shapes_this_gate_cannot_see_stay_a_declared_list():
    """The nested maps whose keys the producer only builds at runtime are where this gate is
    blind -- so the blind spots are a fixed list that has to shrink, never grow quietly.
    `/internal/features/match#match` left this list when the walker learned to read a Pydantic
    model's fields: `result = MatchResult(...)` then `result.model_dump()` builds the map out of
    a class, which is as static as a literal dict."""
    _problems, unseen = _findings()
    assert unseen == [
        "/internal/features/jd/analyze#parsed",
        "/internal/features/resume/parse#parsed",
        "/internal/interview/answer#evaluation",
        "/internal/interview/finalize#evaluation",
    ], "a nested read that just became checkable should be removed from this list, not added to"


def test_the_backend_readers_this_gate_walks_are_the_ones_that_exist():
    """A new consumer class must widen the corpus here, not go unmeasured."""
    assert sorted(p.name for p in _consumer_files()) == [
        "ConversationService.java", "CopilotStreamService.java", "FileIngestService.java",
        "InterviewService.java", "JobService.java", "ResumeService.java",
    ]


def test_the_reads_are_actually_found():
    """Positive control: every assertion above stays green on an empty reading, so the census
    itself is pinned -- real sites, real keys, at both nesting levels."""
    by_path = {e.path: entry for e, entry in reads_by_endpoint().items()}
    assert by_path["/internal/agents/chat/sync"]["reads"] == {
        "answer", "artifacts", "sources", "actions", "run_id"}, \
        "the answer flows through a parameter hop; losing it would silently uncheck copilot"
    assert by_path["/internal/features/match"]["reads"] == {"match", "match_id", "jd"}
    assert by_path["/internal/interview/opening"]["reads"] == {"question", "meta"}
    assert by_path["/internal/features/jd/analyze"]["reads"] == {"parsed"}
    assert by_path["/internal/features/resume/parse"]["reads"] == {"parsed", "score"}
    drilled = {(entry["site"], entry["key"]) for e in reads_by_endpoint().values()
               for entry in e["nested"]}
    assert ("InterviewService.java#answer", "next") in drilled
    assert ("JobService.java#persistImport", "parsed") in drilled
    assert _returned(_routes()[("POST", "/internal/interview/answer")])["next"] == {
        "action", "question", "topic", "difficulty", "reasoning"}, \
        "a hop through `return decide_next(...)` must still name the nested keys"
    assert set(_returned(_routes()[("POST", "/internal/agents/chat/sync")])) == {
        "answer", "artifacts", "sources", "actions", "steps", "tools_used", "run_id"}, \
        "the copilot answer is resolved through `out.to_dict()`: the hop must name its keys"
    assert len(reads_by_endpoint()) >= 6
    assert len(_flows()) >= 8, "every consumer class should contribute several bindings"
    # A record component whose type carries a comma is one field, not two: `Map<String, Object>`
    # read naively yields `Map<String` as a name the response emits, which no reader can hit and
    # which this gate would have matched `normalizeMatch` against unnoticed.
    assert _record_components_at("job/dto/JobDtos.java", "MatchResponse") == {
        "match", "matchId", "jd"}


def test_the_files_that_hold_an_ai_answer_stay_declared():
    """Two censuses, deliberately different: classes that call ai-service, and classes that keep
    its answer in a variable long enough to read from it. FileIngestService is in the first and
    not the second -- it hands the map straight to its caller -- and naming the difference is
    what stops a file this gate stopped walking from looking covered.
    """
    holding = {flow.file.name for flow in _flows()}
    assert holding == {"ConversationService.java", "InterviewService.java",
                       "JobService.java", "ResumeService.java"}
    assert holding < {p.name for p in _consumer_files()}


# ------------------------------------------- the browser reads these answers verbatim too

NORMALIZE = ROOT_FRONTEND / "lib" / "api" / "normalize.ts"

# The backend hands three of these answers straight out as `Map<String, Object>`, so the keys the
# browser asks for are read off the ai-service payload with nothing translating them in between.
BROWSER_READS = {
    "normalizeTailor": ("/internal/features/tailor", "raw"),
    "coverLetterText": ("/internal/features/cover-letter", "raw"),
    "normalizeSuggestions": ("/internal/features/jd/suggestions", "raw"),
}

# Candidates the browser tries that no answer carries. #158 emptied this table: the cover letter's six
# (`content`/`text`/`markdown`/`body` beside the real `letter`, plus the `coverLetter`/`cover_letter`
# wrapper it drilled) were its last members, and `normalizeTailor`/`normalizeSuggestions` had already
# lost theirs to #144/#145. So the table's job changed from inventory to ban -- an empty set here means
# no read of a pass-through AI answer may ask for a name nothing writes, which is what the two tests
# below now assert in both directions. `taskId` was once in this list by accident and it silently killed
# a UI affordance; the cover letter's `taskId` read went the same way in the same commit.
DEAD_ALTERNATES: set[str] = set()


def _browser_reads(function_name: str, receiver: str) -> set[str]:
    source = NORMALIZE.read_text(encoding="utf-8")
    start = source.index(f"export function {function_name}(")
    body = source[start:source.index("\n}\n", start)]
    return {key for group in re.findall(rf"(?:str|num|pick|list)(?:<[^>]*>)?\(\s*{receiver}\s*,([^)]*)\)", body)
            for key in re.findall(r'"([^"]+)"', group)}


def _answers_read_by_the_browser(path: str) -> set[str]:
    return set(_returned(_routes()[("POST", path)]) or {})


def test_what_the_browser_reads_off_a_passed_through_answer_exists():
    problems = []
    for function_name, (path, receiver) in BROWSER_READS.items():
        read = _browser_reads(function_name, receiver)
        answers = _answers_read_by_the_browser(path)
        if not read & answers:
            problems.append(f"{function_name} reads {sorted(read)} off {path}, which answers "
                            f"{sorted(answers)}")
    assert problems == [], "\n".join(problems)


def test_the_alternate_spellings_with_no_producer_stay_declared():
    dead = set()
    for function_name, (path, receiver) in BROWSER_READS.items():
        dead |= _browser_reads(function_name, receiver) - _answers_read_by_the_browser(path)
    assert dead == DEAD_ALTERNATES, f"undocumented key the browser asks for: {sorted(dead ^ DEAD_ALTERNATES)}"


def test_the_browser_side_is_actually_read():
    """Positive control: the two gates above pass on an empty reading of either file."""
    assert _browser_reads("coverLetterText", "raw") == {"letter"}, \
        "one name, and it is the producer's own"
    assert _answers_read_by_the_browser("/internal/features/cover-letter") == {
        "letter", "sources", "mode", "model"}, \
        "resolving `cover_generate` through its import alias is what makes this answer readable"
    assert _browser_reads("normalizeTailor", "raw") >= {"stats", "notes"}
    # The ban is only as strong as the machinery that computes it, and an empty table is the shape a
    # broken scanner leaves behind too -- so the scanner's own reach is pinned here: the cover letter's
    # answer and the browser's read differ by exactly the three names the reader no longer asks for.
    assert _answers_read_by_the_browser("/internal/features/cover-letter") - _browser_reads(
        "coverLetterText", "raw") == {"mode", "model", "sources"}
    assert _browser_reads("coverLetterText", "raw") - _answers_read_by_the_browser(
        "/internal/features/cover-letter") == set()


# ------------------------------------- the same reading, against a Java record's fields

CHAT_DTOS = JAVA_ROOT / "com" / "careeros" / "conversation" / "dto" / "ConversationDtos.java"


def _record_components(record: str) -> set[str]:
    """The components of a Java record, which are the keys Jackson emits for it."""
    source = CHAT_DTOS.read_text(encoding="utf-8")
    opener = f"record {record}("
    if opener not in source:
        raise AssertionError(f"{opener!r} not found: the record this reader is supposed to hit has moved or been renamed")
    head = source[source.index(opener) + len(opener):]
    block = head[:head.index(") {")]
    names = []
    for declaration in _top_level(block, ","):
        tokens = declaration.strip().split()
        if tokens:
            names.append(tokens[-1])
    return set(names)


def _picks_off_reply(helper: str) -> set[str]:
    """The reply keys a `normalize.ts` mapper reads off its own parameter.

    Since #149 the copilot hands `raw` itself to `normalizeChatActions` and lets that reader pick
    `actions`, so a rule that only scans the reply block would report the action row as dropped --
    which the chips on a live page refute. The names come from the per-site gate's own reader rather
    than from a second list written here, and the delegation is only free if that gate binds the
    helper: an unbound mapper would take a piece of the record out of every contract's sight.
    """
    from tests import test_response_field_contract as field  # crosses back; safe at call time

    source = NORMALIZE.read_text(encoding="utf-8")
    start = source.index(f"export function {helper}(")
    param = re.match(r"export function \w+\(\s*([A-Za-z_$][\w$]*)", source[start:]).group(1)
    spec = field.READERS.get(helper)
    assert spec is not None, (f"the copilot reply delegates a piece of itself to {helper}, which the "
                              "per-site gate binds no reader for, so those reads go unchecked")
    assert param in spec["record_of"], f"{helper} reads the reply off {param!r}, named nowhere in its " \
                                       "own binding, so the delegation reaches an unchecked receiver"
    return {key for site in field._sites(helper) if site["receiver"] == param for key in site["keys"]}


def test_the_copilot_reads_line_up_with_chat_response():
    """The browser's copilot reply is built from `ChatResponse`, not from a passed-through AI
    answer, so its candidates have to be checked against the record -- which is where a key nothing
    serializes (`taskId`, before the tailor panel stopped looking for one) belongs."""
    actions = (ROOT_FRONTEND / "lib" / "hooks" / "actions.ts").read_text(encoding="utf-8")
    start = actions.index("return {\n        answer: str(raw,")
    block = actions[start:actions.index("\n      };", start)]
    read = {key for group in re.findall(r'(?:str|num|pick|list)\(\s*raw\s*,([^)]*)\)', block)
            for key in re.findall(r'"([^"]+)"', group)}
    emitted = _record_components("ChatResponse")
    assert read & emitted, f"the copilot reads {sorted(read)}, none of which is in {sorted(emitted)}"
    assert emitted - read == {"actions", "artifacts", "assistantMessageId", "userMessageId"}, \
        "the reply's own block reads its scalar components; `actions` and `artifacts` are the two "\
        "it delegates"
    # The delegation, resolved rather than excused: both names still reach the page, through mappers
    # the per-site gate binds to this record and to `MessageItem` at once. #145a moved `artifacts` into
    # this group by making the card mapper pick the name itself -- before that the block here read a
    # pre-picked list, so the probe had no author on either side of either contract.
    delegated = {helper: _picks_off_reply(helper)
                 for helper in re.findall(r"\b(normalize\w+)\(\s*raw\s*\)", block)}
    assert delegated == {"normalizeChatActions": {"actions"}, "normalizeArtifacts": {"artifacts"}}, \
        f"the reply now leans on {sorted(delegated)}, which this gate has to keep honest"
    read |= {key for names in delegated.values() for key in names}
    assert emitted - read == {"assistantMessageId", "userMessageId"}, \
        "the reply drops the two message ids today; if that changes, this line is where to look"
    # Candidates `ChatResponse` never serializes. Each is either a tolerant alias of a live key
    # (`content`/`text`/`message`/`reply` for `answer`, `run_id` for `runId`) or, like `taskId`, a
    # leftover of a field that has never been on the answer -- the shape of mistake that left the
    # tailor panel offering a stream it could not open. `citations` used to sit here too, until #152
    # measured that its only author is `/internal/rag/answer`, a route the app never calls.
    assert read - emitted == {
        "content", "text", "message", "reply", "run_id", "conversation_id",
        "taskId", "task_id",
    }, f"undocumented dead reads on the copilot answer: {sorted(read - emitted)}"


# ----------------------- the other DTO-backed reads, weakest form of the same rule

# Three more browser readers whose producer is a Java record rather than a passed-through AI
# answer. Only the coarse claim is checked here: at least one name the reader tries must be a real
# component. A per-key dead list, as the copilot case carries, would be useless on these --
# `normalizeMatch` alone asks for ~40 names because it reads the nested `MatchSummary` and the
# resume-shaped sub-maps in the same body, and mixing those together would hide a real wrong-name
# signal in noise. So: catch a wholesale rename or a record that moved, and leave the rest to the
# gates that can see one map at a time -- which `test_response_field_contract.py` now does for
# `normalizeApplication` and `normalizeMessages`, per read site and per receiver.
DTO_READS = {
    "normalizeMatch": ("MatchResponse", "job/dto/JobDtos.java"),
    "normalizeApplication": ("ApplicationItem", "application/dto/ApplicationDtos.java"),
    "normalizeMessages": ("MessageItem", "conversation/dto/ConversationDtos.java"),
}


def _dto_reads(function_name: str) -> set[str]:
    source = NORMALIZE.read_text(encoding="utf-8")
    opener = f"export function {function_name}("
    if opener not in source:
        raise AssertionError(f"{opener!r} is gone from normalize.ts: the table names a reader that moved, so this rule compares nothing")
    start = source.index(opener)
    body = source[start:source.index("\n}\n", start)]
    return {key for group in re.findall(r'(?:str|num|pick|list|bool)\(\s*\w+\s*,([^)]*)\)', body)
            for key in re.findall(r'"([^"]+)"', group)}


def _hide_generic_commas(block: str) -> str:
    """Blank out the commas that are inside a generic type, so one component stays one component.

    `Map<String, Object> match` split naively reads as two declarations and yields `Map<String` as
    a field the record emits: a name no response can ever carry, and one the check below would
    have happily matched a reader against.
    """
    depth, out = 0, []
    for char in block:
        if char == "<":
            depth += 1
        elif char == ">":
            depth = max(0, depth - 1)
        elif char == "," and depth:
            out.append("\x00")
            continue
        out.append(char)
    return "".join(out)


def _record_components_at(relative: str, record: str) -> set[str]:
    source = (JAVA_ROOT / "com" / "careeros" / relative).read_text(encoding="utf-8")
    opener = f"record {record}("
    if opener not in source:
        raise AssertionError(f"{opener!r} not found: the record this reader is supposed to hit has moved or been renamed")
    head = source[source.index(opener) + len(opener):]
    block = head[:head.index(") {")]
    names = []
    for declaration in _top_level(_hide_generic_commas(block), ","):
        tokens = declaration.strip().replace("\x00", ",").split()
        if tokens:
            names.append(tokens[-1])
    return set(names)


def test_the_dto_backed_readers_hit_a_field_the_record_has():
    for function_name, (record, relative) in DTO_READS.items():
        tried = _dto_reads(function_name)
        emitted = _record_components_at(relative, record)
        assert tried, f"{function_name}'s body was not read at all"
        assert tried & emitted, (f"{function_name} tries {sorted(tried)}, none of which "
                                 f"{record} serializes ({sorted(emitted)})")
