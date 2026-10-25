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
import os
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
        "/internal/features/growth-report#gap",
        "/internal/features/jd/analyze#parsed",
        "/internal/features/resume/parse#parsed",
        "/internal/interview/answer#evaluation",
        "/internal/interview/finalize#evaluation",
    ], "a nested read that just became checkable should be removed from this list, not added to"


def test_the_backend_readers_this_gate_walks_are_the_ones_that_exist():
    """A new consumer class must widen the corpus here, not go unmeasured."""
    assert sorted(p.name for p in _consumer_files()) == [
        "ConversationService.java", "CopilotStreamService.java", "FileIngestService.java",
        "GrowthService.java", "InterviewService.java",
        "JobService.java", "MemoryController.java", "QueryEmbeddingService.java",
        "ResumeService.java",
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
    # `MemoryController` is here because it reads the ai-service's own camelCase JSON into
    # `MemoryItem` — it holds the answer long enough to read five keys off it, which is the
    # same reason `InterviewService` is. A controller that forwards a map untouched would not
    # be, but that would leave the casing unmapped.
    assert holding == {"ConversationService.java", "GrowthService.java",
                       "InterviewService.java", "JobService.java",
                       "MemoryController.java", "QueryEmbeddingService.java",
                       "ResumeService.java"}
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


# The two shapes a declaration in this project can take, declared once (#160). Both halves of each
# pattern are load-bearing: a generic before the paren is part of the declaration, so a probe that
# dropped it walked straight past `normalizePage<T>`, `pick<T>`, `list<T>` and `PageDTO<T>` (#159's
# scanner fix); and four of normalize.ts's mappers are module-private, so a probe that required the
# export keyword named declarations that were never exported. Any third pattern of this shape is a
# third probe that can silently match nothing, which the ban at the bottom of this file refuses.
TS_OPENER = r"(?:export )?function {name}\s*(?:<[^<>]*>)?\("
JAVA_OPENER = r"record {name}\s*(?:<[^<>]*>)?\("


def _ts_function_body(function_name: str) -> str:
    """The body of one mapper in normalize.ts, through the one probe both gates use.

    Three tables here read mapper bodies, so the opener lives in one place rather than being copied a
    fourth time: it used to be two copies that differed only in whether the export keyword was
    required, which is how `changeFrom` came to fail one probe and pass the other.
    """
    source = NORMALIZE.read_text(encoding="utf-8")
    opener = re.search(TS_OPENER.format(name=function_name), source)
    if opener is None:
        raise AssertionError(f"{function_name} has no function declaration in normalize.ts: the table "
                             "names a reader that moved, so this rule compares nothing")
    start = opener.start()
    if "\n}\n" not in source[start:]:
        raise AssertionError(f"{function_name}'s body has no closing brace after its declaration in "
                             "normalize.ts: the file shape changed under this probe")
    return source[start:source.index("\n}\n", start)]


def _names_read_off(typescript: str, receiver: str) -> set[str]:
    """The names an accessor call tries off one receiver in an arbitrary slice of TypeScript.

    This file carried three copies of that scan, each spelling four or five of the ten accessor names
    `_ACCESSORS` keeps, none of them able to see a typed call like `list<string>(m, "whyMatch")` or
    the `idOf` fold at all. The vocabulary is composed here so it is written in exactly one place,
    which is what #161's ban then checks.
    """
    from tests import test_response_field_contract as field  # crosses back; safe at call time

    pattern = field._ACCESSORS + re.escape(receiver) + r"\s*,([^)]*)\)"
    return {key for group in re.findall(pattern, typescript)
            for key in re.findall(r'"([^"]+)"', group)}


def _browser_reads(function_name: str, receiver: str) -> set[str]:
    """What one `normalize.ts` mapper asks for off one receiver, from the per-site scanner itself."""
    from tests import test_response_field_contract as field

    return {key for site in field._sites(function_name) if site["receiver"] == receiver
            for key in site["keys"]}


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

# Relative to `com/careeros`, the same form DTO_READS uses, so one path serves both the copilot's own
# record and the reader table that names it.
CONVERSATION_DTOS = "conversation/dto/ConversationDtos.java"


def _picks_off_reply(helper: str) -> set[str]:
    """The reply keys a `normalize.ts` mapper reads off its own parameter.

    Since #149 the copilot hands `raw` itself to `normalizeChatActions` and lets that reader pick
    `actions`, so a rule that only scans the reply block would report the action row as dropped --
    which the chips on a live page refute. The names come from the per-site gate's own reader rather
    than from a second list written here, and the delegation is only free if that gate binds the
    helper: an unbound mapper would take a piece of the record out of every contract's sight.
    """
    from tests import test_response_field_contract as field  # crosses back; safe at call time

    body = _ts_function_body(helper)
    param = re.match(TS_OPENER.format(name=r"\w+") + r"\s*([A-Za-z_$][\w$]*)", body).group(1)
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
    read = _names_read_off(block, "raw")
    emitted = _record_components_at(CONVERSATION_DTOS, "ChatResponse")
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
    "normalizeMessages": ("MessageItem", CONVERSATION_DTOS),
}


def _dto_reads(function_name: str) -> set[str]:
    """The names one browser reader tries, out of the field gate's site scanner.

    This used to spell its own accessor vocabulary -- `(?:str|num|pick|list|bool)\\(` -- which is five
    of the ten names `_ACCESSORS` carries, without its generic slot and without the `idOf` fold. The
    gap is measured at this plane, per reader: `pick<Record<string, unknown>>(raw, "company")` and
    three `list<string>(m, ...)` calls name fields the copy could never see, and every one of
    `id`/`_id`/`uuid`/`eventId`/`event_id`/`key` comes only through the fold. #160's lesson repeated
    one level up: a second copy is not a redundant scanner, it is a blind one."""
    from tests import test_response_field_contract as field

    return {key for site in field._sites(function_name) for key in site["keys"]}


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


def _declared_records() -> list[tuple[str, str]]:
    """Every record the backend declares, as (`path under the package`, name), located by the one
    Java opener either gate has. The probes below are shared by readers this file never names, so the
    population they have to survive is the whole repository, not the handful of DTOs bound here."""
    package = JAVA_ROOT / "com" / "careeros"
    found = []
    for path in sorted(package.rglob("*.java")):
        source = path.read_text(encoding="utf-8")
        for match in re.finditer(JAVA_OPENER.format(name=r"(\w+)"), source):
            found.append((path.relative_to(package).as_posix(), match.group(1)))
    return found


def _component_list(source: str, open_paren: int) -> str:
    """Everything between `source[open_paren]` and its matching `)`, strings and comments skipped.

    Counting parentheses is the only way to find the end of a component list, because the character
    that follows it is not always a brace: `SavedJob.SavedJobId(UUID userId, UUID jobId) implements
    Serializable {` puts an `implements` clause in between, so scanning for the text `") {"` walked
    straight on into the entity's own accessor declarations and read `getUserId(`, `false` and
    `"created_at"` as fields the record serializes -- while losing `jobId`, the one name in the real
    list. Measured at this plane: 101 record declarations, 2 with an `implements` clause, and one of
    those two is the entity above.
    """
    depth, index, length = 0, open_paren, len(source)
    while index < length:
        char = source[index]
        if source.startswith("//", index):
            index = source.index("\n", index)
            continue
        if source.startswith("/*", index):
            index = source.index("*/", index) + 2
            continue
        if char in '"\'':
            quote, index = char, index + 1
            while index < length and source[index] != quote:
                index += 2 if source[index] == "\\" else 1
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[open_paren + 1:index]
        index += 1
    raise AssertionError("a component list never closes: the file shape changed under this probe")


def _java_record_body(relative: str, record: str) -> str:
    """The component list of one Java record, off its own declaration, through the only Java opener
    either gate has (#160).

    A generic is part of the declaration, not a move: `PageDTO<T>` answers every paged route and
    `ApiResponse<T>` wraps every public one, so a literal `record X(` probe walked straight past both
    -- the blind spot #159 fixed on the reader side, where a producer the census cannot locate is a
    producer no rule can bind. Two other probes of this shape were still in these files, one of them
    also splitting `Map<String, Object>` into a field named `Map<String`; they now call this.

    The list itself is found by `_component_list`, not by the `") {"` this used to cut on: an
    `implements` clause after the list sent that scan into the record's (or its enclosing class's)
    methods, which yield plausible-looking component names. A probe that cannot find the list says so
    instead of returning something else.
    """
    source = (JAVA_ROOT / "com" / "careeros" / relative).read_text(encoding="utf-8")
    opener = re.search(JAVA_OPENER.format(name=record), source)
    if opener is None:
        raise AssertionError(f"record {record} has no declaration in {relative}: the record this "
                             "reader is supposed to hit has moved or been renamed")
    return _component_list(source, opener.end() - 1)



def _component_names(block: str) -> list[str]:
    """The declared name of each top-level component: the last word of a comma-separated entry, with
    generic commas hidden so `Map<String, Object> match` stays one component."""
    names = []
    for declaration in _top_level(_hide_generic_commas(block), ","):
        tokens = declaration.strip().replace("\x00", ",").split()
        if tokens:
            names.append(tokens[-1])
    return names


def _java_record_tail(relative: str, record: str) -> str:
    """What follows one record's component list: `{` for almost every declaration in the backend, and
    an `implements` clause for the two that do not."""
    source = (JAVA_ROOT / "com" / "careeros" / relative).read_text(encoding="utf-8")
    opener = re.search(JAVA_OPENER.format(name=record), source)
    if opener is None:
        raise AssertionError(f"record {record} has no declaration in {relative}")
    block = _component_list(source, opener.end() - 1)
    return source[opener.end() + len(block) + 1:].lstrip()


def _stop_scan_components(relative: str, record: str) -> set[str]:
    """The `") {"` cut `_java_record_body` used to stop on, kept as a foil for the rule below.

    A rule that only checks a property has to show the property is what catches the bug, and the bug
    here is invisible from the probe's own output: the old cut produced a set of names for
    `SavedJobId` that looks like a record until you read it closely."""
    source = (JAVA_ROOT / "com" / "careeros" / relative).read_text(encoding="utf-8")
    opener = re.search(JAVA_OPENER.format(name=record), source)
    head = source[opener.end():]
    return set(_component_names(head[:head.index(") {")])) if ") {" in head else set()


def _record_components_at(relative: str, record: str) -> set[str]:
    return set(_component_names(_java_record_body(relative, record)))


def test_the_dto_backed_readers_hit_a_field_the_record_has():
    for function_name, (record, relative) in DTO_READS.items():
        tried = _dto_reads(function_name)
        emitted = _record_components_at(relative, record)
        assert tried, f"{function_name}'s body was not read at all"
        assert tried & emitted, (f"{function_name} tries {sorted(tried)}, none of which "
                                 f"{record} serializes ({sorted(emitted)})")


# --------------------- the probes themselves, since a probe that cannot see is indistinguishable from

LOOKUP_METHODS = {"index", "search", "match", "findall", "finditer", "compile"}


def _calls_in(scope) -> list:
    """Call nodes written in one scope, without descending into the functions it declares."""
    found = []
    for child in ast.iter_child_nodes(scope):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(child, ast.Call):
            found.append(child)
        found.extend(_calls_in(child))
    return found


def _lookup_patterns(path: Path) -> list[tuple[str, str]]:
    """Every (scope, pattern string) a gate file hands to a lookup method as a literal first argument.

    Both bans below read this one walk, because both are about the same act: writing out a shape a
    probe already owns. A pattern built by `.format(...)` or by concatenating a shared constant is a
    `Call`/`BinOp` node rather than a string literal, so the canonical forms fall out by construction
    instead of by exemption.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    scopes = [("module", tree)] + [(node.name, node) for node in ast.walk(tree)
                                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    found = []
    for scope, node in scopes:
        for call in _calls_in(node):
            if not (isinstance(call.func, ast.Attribute) and call.func.attr in LOOKUP_METHODS):
                continue
            if not call.args:
                continue
            first = call.args[0]
            if isinstance(first, ast.Constant):
                text = first.value
            elif isinstance(first, ast.JoinedStr):
                text = "".join(value.value if isinstance(value, ast.Constant) else "{}"
                               for value in first.values)
            else:
                continue
            if isinstance(text, str):
                found.append((scope, text))
    return found


def _declaration_lookups(path: Path) -> list[tuple[str, str]]:
    """Where a gate file looks one declaration up by hand: a lookup call whose first argument is a
    string naming a `function` or a `record` beside the name slot.

    The pattern is `\b(function|record)` followed by a name slot -- the interpolated `{name}` of a
    fixed literal (`export function idOf(`) or the first letter of one -- which is what both hand-typed
    forms write, and what the two canonical constants do not: their `.format(name=...)` arguments are
    calls, not string literals. An enumeration like `^function (\\w+)[<(]` reads as `function (` and is
    deliberately out of scope -- listing every declaration cannot miss one category the way locating one
    can.
    """
    return [(scope, text) for scope, text in _lookup_patterns(path)
            if re.search(r"\b(?:function|record)\s*[\w{]", text)]


def _accessor_alternatives() -> set[str]:
    """The accessor vocabulary, read out of the one constant that defines it -- including the helpers
    whose own call sites a scanner folds into their caller's census."""
    from tests import test_response_field_contract as field

    group = re.search(r"\(\?:([^)]*)\)", field._ACCESSORS)
    if group is None:
        raise AssertionError("_ACCESSORS no longer holds an alternation to read: the ban that keeps "
                             "this file from re-spelling it would pass on an empty vocabulary")
    return set(group.group(1).split("|")) | set(field.FOLDED_ACCESSORS)


def _accessor_list_lookups(path: Path, vocabulary: set[str]) -> list[tuple[str, str]]:
    """Where a gate file writes its own list of accessor names into a pattern.

    Three copies lived in this file, found by walking it rather than by reading it: `_browser_reads`
    spelled `(?:str|num|pick|list)` with a generic slot, `_dto_reads` spelled five names without one,
    and the copilot test spelled the four again over `actions.ts`. A copy is not a smaller version of
    the scanner it duplicates -- it is a scanner that cannot see the calls the original was widened
    for, which is how `list<string>(raw, "skills", "requiredSkills", ...)` and every name `idOf` tries
    stayed out of the read sets these gates compare against a record.
    """
    found = []
    for scope, text in _lookup_patterns(path):
        for group in re.findall(r"\(\?:([^)]*)\)", text):
            named = {token for token in group.split("|") if token in vocabulary}
            if len(named) >= 3:
                found.append((scope, group))
    return found



def test_no_gate_looks_a_declaration_up_by_hand():
    """#160's ban. Four of these probes were copies of the same two openers, each missing a different
    half of what a declaration can carry: `source.index("export function idOf(")` could not see a
    generic, and the copy in the field gate could not see the four module-private mappers -- which is
    how `statusCountsToRows` sat outside every reader census while reading `count`/`total` off values
    the record types as `Map<String, Long>`. A hand-typed opener is a rule that passes when the code it
    was written to check has moved, so the only place either shape may be typed is the two constants."""
    from tests import test_response_field_contract as field  # both files, one rule

    offenders = {}
    for path in (Path(__file__), Path(field.__file__)):
        found = _declaration_lookups(path)
        assert {scope for scope, _ in found} <= {"module"}, \
            f"{path.name}: a declaration probe is written in {sorted({s for s, _ in found})}"
        offenders[path.name] = sorted({text for _, text in found})
    assert offenders == {"test_response_shape_contract.py": [],
                         "test_response_field_contract.py": []}, offenders


def test_the_declaration_probes_reach_the_shapes_a_copy_would_miss():
    """Positive control for the ban above: it is only worth having while the shared probes really do
    what the hand-written copies did not, and each of these shapes is measured at this plane."""
    source = NORMALIZE.read_text(encoding="utf-8")
    # 49 rather than 48 since `normalizeAttention` joined the module-private mappers: the dashboard's
    # attention rows are the fifth non-exported reader, and the opener has to see it like the others.
    # 50 with `normalizeMemory`: one more exported mapper, the reader the memory surface added.
    # 51 with `normalizeFollowUp`: the follow-up tile's row reader (11.3), the sixth non-exported one.
    assert len(re.findall(TS_OPENER.format(name=r"(\w+)"), source)) == 52, \
        "46 exported mappers and 6 module-private ones, all through one opener"
    assert "export function normalizePage(" not in source, \
        "the generic really does sit between the name and the paren, so a literal opener finds nothing"
    assert _ts_function_body("normalizePage").startswith("export function normalizePage<T>(")
    assert _ts_function_body("changeFrom").startswith("function changeFrom("), \
        "the reader #159's exported census could not name, found by the probe that does not require export"
    page = (JAVA_ROOT / "com" / "careeros" / "common" / "PageDTO.java").read_text(encoding="utf-8")
    assert "record PageDTO(" not in page, "same blind spot on the producer side"
    assert _record_components_at("common/PageDTO.java", "PageDTO") == {"items", "total", "page", "size"}
    assert _record_components_at("common/ApiResponse.java", "ApiResponse") == {
        "success", "data", "error"}, "the other generic record, which no reader is bound to yet"


def test_the_java_probe_reads_every_record_the_backend_declares():
    """#161's coverage rule: the probes are shared machinery, so their population is the repository,
    not the dozen records a table happens to bind.

    The reason is a defect the old cut had already committed. `SavedJob.SavedJobId(UUID userId, UUID
    jobId) implements Serializable {` ends its component list with an `implements` clause, so scanning
    for the text `\") {\"` ran on to the enclosing entity's `public UUID getUserId() {` and reported the
    record's components as `getUserId(`, `false`, `\"created_at\"`, `\"job_id\"`, `\"user_id\"` -- with the
    real `jobId` missing. Both directions wrong, and nothing downstream could tell, because a set of
    plausible strings is exactly what the callers expect. The second such record, `ResumeSkillId(...)
    implements Serializable {}`, refused outright instead, since `\") {}\"` never contains `\") {\"`.

    So the rule checks properties a wrong cut cannot satisfy -- every derived name is a bare Java
    identifier, no list comes back empty -- and pins the assumption the whole family rests on: a
    component's name is its wire name, which holds only while no record renames or hides one.
    """
    declared = _declared_records()
    # 104 rather than 103 since `ResumeService.OriginalFile`: the download route's answer record --
    # bytes, media type, save name -- which is a record like the rest, so the shared opener has to
    # read it. Before it, `JobDtos.CompanyDetail` was the last one to join (102 -> 103).
    # `MemoryItem` / `UpdateMemoryRequest` (ai/dto/) took it to 106 for the memory-correction
    # surface; `GrowthReportRequest` to 107 as the 10.2 bridge's first request record; the
    # contacts registry's `ContactRequest`/`ContactItem` (11.1) to 109: the records the
    # backend declares, whether or not a response carries them.
    # 117 with the 13.x/14.x/16.x bridges: `FollowUpItem` (the 11.3 follow-up tile's row),
    # `ExportRequest`/`ImportPlanRequest`/`RedactRequest` (13.1-13.3), and
    # `ParseFeedRequest`/`DedupeRequest`/`FreshnessSweepRequest`/`PlanIngestRequest` (14.2-14.3).
    # 123 with the 12.x bridge: `SalaryRequest`, `NegotiationRequest`, `EquityGrant`,
    # `OfferItem`, `CompareOffersRequest` and `CounterOfferRequest` — the six records the
    # salary & offer surface binds.
    # 128 with the 13.x/14.x/16.x bridges: `ExportRequest`, `ImportPlanRequest`,
    # `RedactRequest` (13.1-13.3), `ParseFeedRequest`, `DedupeRequest`,
    # `FreshnessSweepRequest`, `PlanIngestRequest` (14.2-14.3) and `CompanyBriefRequest`
    # (4.8) — the five records those surfaces bind.
    # 130 with the import-apply and render records: `ImportApplyRequest` and
    # `RenderRequest` — the two the 13.2 apply and the 13.1 render bind.
    assert len(declared) == 130, \
        f"{len(declared)} records carry a declaration the shared opener reads, not the 130 measured"
    problems, renamed = [], []
    for relative, record in declared:
        names = _record_components_at(relative, record)
        junk = sorted(name for name in names if not re.fullmatch(r"[A-Za-z_$][\w$]*", name))
        if junk:
            problems.append(f"{relative}#{record} yields {junk}")
        elif not names:
            problems.append(f"{relative}#{record} yields no component at all from "
                            f"{_java_record_body(relative, record)[:40]!r}")
        if re.search(r"@(JsonProperty|JsonNaming|JsonIgnore)\b",
                     _java_record_body(relative, record)):
            renamed.append(f"{relative}#{record}")
    assert problems == [], "\n".join(problems)
    assert renamed == [], (f"a record renames or hides a component, so `_record_components_at` is no "
                           f"longer reading the names that go on the wire: {renamed}")
    # The foil, so the check above is known to be load-bearing rather than lucky: the records the old
    # cut misread are exactly the ones whose list is followed by something other than a brace, and both
    # ends of that claim are read out of the declarations.
    hazard = {entry for entry in declared if not _java_record_tail(*entry).startswith("{")}
    ran_past = {entry for entry in declared
                if _stop_scan_components(*entry) != _record_components_at(*entry)}
    assert ran_past == hazard, (f"the stop disagrees on {sorted(ran_past)}, which is not the set of "
                                f"records with a clause after their list: {sorted(hazard)}")
    assert len(hazard) == 2, f"measured two `implements Serializable` records: {sorted(hazard)}"
    assert _record_components_at("job/entity/SavedJob.java", "SavedJobId") == {"userId", "jobId"}, \
        "the foil's record, read through the balanced scan: the two real components and nothing from "\
        "the entity's accessors"


def test_no_gate_spells_an_accessor_list_by_hand():
    """#161's ban, beside #160's: the accessor vocabulary is `_ACCESSORS`, written once in the field
    gate, and nowhere else.

    Three copies lived in this file, each spelling four or five of the ten names: `_dto_reads` could
    not see a typed call, so `normalizeMatch`'s read set was 15 names where the scanner counts 25, and
    none of the six spellings `idOf` tries -- the identifier every conversation and match row is keyed
    by -- reached the record comparison at all. A copy of a scanner is not a redundant scanner; it is
    one whose blind spots nobody has measured.
    """
    from tests import test_response_field_contract as field

    vocabulary = _accessor_alternatives()
    assert len(vocabulary) == 11, sorted(vocabulary)  # `_ACCESSORS`' 10 plus the folded `idOf`
    offenders = {}
    for path in (Path(__file__), Path(field.__file__)):
        found = _accessor_list_lookups(path, vocabulary)
        offenders[path.name] = sorted(f"{scope}: {group}" for scope, group in found)
    assert offenders == {"test_response_shape_contract.py": [],
                         "test_response_field_contract.py": []}, offenders


def test_the_shared_read_scanners_see_the_calls_a_copy_missed():
    """Positive control for the ban above, on the copy whose gap was measurable.

    The other two (`_browser_reads` and the copilot block's scan) agree with the shared vocabulary on
    every name today, by measurement, so delegating them buys only the zero-copies claim. This one was
    strictly weaker, and the three causes are each named below."""
    assert len(_dto_reads("normalizeMatch")) == 25, "15 through the copied list, 25 through the scanner"
    assert "company" in _dto_reads("normalizeApplication"), \
        "a typed accessor (`pick<Record<string, unknown>>(raw, ...)`) is invisible without the generic slot"
    assert {"whyMatch", "matchedSkills", "interviewTopics"} <= _dto_reads("normalizeMatch"), \
        "same cause, on `list<string>(m, ...)`"
    assert {"id", "_id", "uuid", "event_id", "eventId", "key"} <= _dto_reads("normalizeMessages"), \
        "these six arrive only through the `idOf` fold a spelled list of accessor names cannot reach"
    # The three causes, measured on one reader: `normalizeJob` went from 66 names through the copied
    # list to 75 through the scanner, and the nine new ones are the typed `list<string>` form and the
    # fold -- no accessor *name* was missing there, which is why the claim below is about shapes.
    assert len(_dto_reads("normalizeJob")) == 75, "66 through the copied list, 75 through the scanner"
    assert {"skills", "tags", "requiredSkills", "required_skills"} <= _dto_reads("normalizeJob"), \
        "read from `list<string>(raw, ...)`, which a pattern that stops at the accessor name cannot see"
    assert {"_id", "uuid", "event_id", "key"} <= _dto_reads("normalizeJob"), \
        "the identifier spellings arrive only through the `idOf` fold a spelled list cannot reach"


# ------------------------------------------ #164: the two levels the Java census stops above

_MAP_LOCAL = re.compile(r"(?:Map<String,\s*Object>|var|Object)\s+(\w+)\s*=\s*([^;]+);")
_LIST_DRILL = re.compile(r'Json\.arr\((\w+)\.get\("(\w+)"\)\)')
_ELEMENT_READ = re.compile(r'->\s*Json\.\w+\(Json\.obj\((\w+)\),\s*"(\w+)"\)')
JD_PROMPT = Path(__file__).resolve().parents[1] / "app" / "features" / "jd_analyze.py"


def _drilled_locals(path: Path, method_name: str, var: str) -> list[tuple]:
    """Every local a flow variable is drilled into, and whether `_NESTED` binds it.

    The scanner's second level is not a walk, it is a pattern: `_NESTED` only recognises a drill
    written as `Map<String, Object> x = Json.obj(var.get("k"))` or as a cast of `var.get("k")`. A
    drill declared with `var` -- and these four files write `var` locals in 8 places -- is invisible
    to it: the reads below such a local would then be attributed to no key at all, and a renamed
    producer key would fall through to `Json.str`'s empty string while every rule here stayed green.
    This asks the same question by declaration shape rather than by `_NESTED`'s shape, so a drill the
    census loses costs a red instead of a silence.
    """
    body = _methods_of(path)[method_name].body
    bound = {m.group(1) for pattern in _NESTED
             for m in re.finditer(pattern.format(var=re.escape(var)), body)}
    out = []
    for name, init in _MAP_LOCAL.findall(body):
        if name != var and f'{var}.get("' in init:
            out.append((path.name, method_name, name, init.strip(), name in bound))
    return out


def _element_reads() -> list[tuple]:
    """Reads taken off one element of a list drilled out of an answer: the census's third level.

    `Json.arr(parsed.get("requiredSkills")).stream().map(o -> Json.str(Json.obj(o), "name"))` is
    how `JobService.persistImport` turns the analyzer's skills into rows. The scanner sees
    `requiredSkills` (a key of `parsed`) and stops: `name` belongs to the *element*, which no
    pattern here reads, so the name is checked against its producer by nothing in this direction.
    """
    out = []
    for path in _consumer_files():
        for method_name, method in sorted(_methods_of(path).items()):
            for drill in _LIST_DRILL.finditer(method.body):
                read = _ELEMENT_READ.search(method.body[drill.end():drill.end() + 240])
                if read and read.group(1) != drill.group(1):
                    out.append((path.name, method_name, drill.group(1), drill.group(2),
                                read.group(2)))
    return out


def _jd_element_keys(list_key: str) -> set[str]:
    """The keys the analyzer's own prompt skeleton puts inside one element of `list_key`."""
    skeleton = JD_PROMPT.read_text(encoding="utf-8")
    element = re.search(r'"' + list_key + r'"\s*:\s*\[\s*\{([^]]*)\}', skeleton)
    assert element, f"the analyze prompt no longer draws {list_key} as a list of objects"
    return set(re.findall(r'"(\w+)"\s*:', element.group(1)))


def test_the_java_census_binds_every_drill_and_names_the_level_it_stops_at():
    """#164: the Java census was re-derived through an independent rooting walk over every
    answer-carrying method (12 flows, 4 files) and agreed key-for-key, so nothing here is a fix.
    What the walk did expose are the two levels the census holds by pattern rather than by walk -- a
    drill's declaration shape and the element inside a drilled list -- and those two are pinned here
    the way the field gate pins its census: by population, with a control that says the probe still
    matches the shape it is claiming. A third drill level, or a `var` drill, is a red rather than a
    silence from now on.
    """
    drills = [row for flow in _flows() for row in _drilled_locals(flow.file, flow.method, flow.var)]
    unbound = [row[:4] for row in drills if not row[4]]
    assert unbound == [], (f"an AI answer is drilled into a local `_NESTED` does not bind, so every "
                           f"read below it is attributed to nothing: {unbound}")
    assert sorted({(row[0], row[1], row[2]) for row in drills}) == [
        ("GrowthService.java", "coverageOf", "gap"),
        ("InterviewService.java", "answer", "evaluation"),
        ("InterviewService.java", "answer", "next"),
        ("InterviewService.java", "finalize", "evaluation"),
        ("JobService.java", "match", "match"),
        ("JobService.java", "persistImport", "parsed"),
        ("ResumeService.java", "persistParse", "parsed"),
        ("ResumeService.java", "persistParse", "score"),
    ], "a drill appeared or disappeared: the second level of the census moved"

    elements = sorted(_element_reads())
    assert elements == [
        ("JobService.java", "persistImport", "parsed", "preferredSkills", "name"),
        ("JobService.java", "persistImport", "parsed", "requiredSkills", "name"),
    ], (f"the element level is a two-site population and it moved: {elements} -- a third one has to "
        "be checked against its producer, not added to a list blindly")
    for _, _, _, list_key, element_key in elements:
        assert element_key in _jd_element_keys(list_key), (
            f"the backend reads {element_key!r} off an element of {list_key}, which the analyze "
            "prompt never draws -- every such read becomes null and the imported job loses its "
            "skills in silence")

    # The controls that keep the two claims above from being descriptions of an accident.
    var_drill = ('var drilled = Json.obj(result.get("evaluation"));\n'
                 '        String note = Json.str(drilled, "summary");')
    assert _MAP_LOCAL.findall(var_drill) == [("drilled", 'Json.obj(result.get("evaluation"))')], \
        "the declaration probe stopped seeing a `var` drill, so the claim above proves nothing"
    assert re.search(_NESTED[0].format(var="result"), var_drill) is None, \
        "_NESTED learned to bind a `var` drill; then this rule and the census are one scanner twice"
    assert _ELEMENT_READ.search('o -> Json.str(Json.obj(o), "plantedElement")') is not None, \
        "the element probe stopped matching, and the population above would read as empty forever"


# ------------------------------------------------------- the envelope: one wrapper, one unwrapper

SUCCESS_READ = re.compile(r"\b(\w+)\.(success)\b")
UNWRAP = re.compile(r"\b(\w+)\?\.data\b")


def _envelope_readers() -> tuple[list[dict], list[dict]]:
    """(Envelope reads, `toast.success` lines) over every non-test file under frontend/src.

    Both lists come out of the SAME walk on purpose: the toast count is the floor that proves the walk
    reached the pages and the hooks, not just the api directory. A second loop measuring the width would
    stay green while the reader walk quietly narrowed itself -- which is what the first witness run of
    this section caught.

    `success` is the envelope's own field -- `common/ApiResponse.java:10` declares
    `record ApiResponse<T>(boolean success, T data, ApiError error)` -- so a page that reads it has
    started consuming the wrapper rather than the payload. `toast.success(...)` from sonner is the same
    spelling in a different language, and it is separated by the receiver name rather than dropped.
    """
    rows, toasts = [], []
    for path in sorted(ROOT_FRONTEND.rglob("*.ts")) + sorted(ROOT_FRONTEND.rglob("*.tsx")):
        if ".test." in path.name:
            continue
        relative = str(path.relative_to(ROOT_FRONTEND)).replace("\\", "/")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "toast.success" in line:
                toasts.append({"file": relative, "line": number})
            for found in SUCCESS_READ.finditer(line):
                if found.group(1) == "toast":
                    continue
                rows.append({"file": relative, "line": number, "kind": "success", "text": line.strip()})
            for found in UNWRAP.finditer(line):
                rows.append({"file": relative, "line": number, "kind": "unwrap", "text": line.strip()})
    return rows, toasts


def test_the_response_envelope_has_exactly_one_wrapper_and_one_unwrapper():
    """#172: the pair that makes "no reader binds ApiResponse" true instead of suspicious.

    `EnvelopeAdvice.beforeBodyWrite` wraps every public body and the client unwraps once, which is why
    the producer census can honestly say no browser reader names the envelope. That is a claim about two
    files in two languages, and it is only safe while both halves stay where they are: widen the advice
    and the unwrap returns `undefined` for responses that were never wrapped, add a second unwrap and the
    one that is gated stops being the one that runs. Measured on this plane: two `success` reads and one
    `?.data` unwrap, all of them in `lib/api/client.ts`, plus 31 `toast.success` lines the exclusion has
    to keep out. `client.ts` belongs to a concurrent session's file list, so this gate reads it and never
    edits it -- if a third reader appears, the test names it and a human decides where it belongs.
    """
    advice = (JAVA_ROOT / "com" / "careeros" / "common" / "EnvelopeAdvice.java").read_text(encoding="utf-8")
    assert "return ApiResponse.ok(body);" in advice, \
        "the advice no longer wraps every public body, so the client's single unwrap is a lie"
    for skip in ("ApiResponse<?>", "SseEmitter", "Resource"):
        assert skip in advice, (f"{skip} is no longer in the advice's own exclusion list: the envelope "
                                "must not be applied twice, or to a stream or a file download")

    rows, toasts = _envelope_readers()
    assert sorted({row["file"] for row in rows}) == ["lib/api/client.ts"], \
        (f"{sorted({row['file'] for row in rows})}: only the client may touch the envelope, or a page is "
         "reading a wrapper field the shape gate binds to no record")
    kinds = sorted(row["kind"] for row in rows)
    # Two unwraps rather than one: `uploadWithProgress` reports upload progress over XHR, which
    # fetch cannot do, and the backend wraps the upload endpoint's answer in the same envelope --
    # so the XHR transport unwraps it a second time. This docstring invites a human decision when
    # a third reader appears; this is that decision, and what it rests on: the second unwrap is
    # another transport, not another consumer, and the assertion below is what keeps the two
    # spellings from drifting apart -- the drift the original one-unwrap census existed to catch.
    assert kinds.count("success") == 2 and kinds.count("unwrap") == 2, \
        f"{[(row['kind'], row['text']) for row in rows]}: two success checks and one unwrap per transport is the pair"
    assert all("json?.data ??" in row["text"] for row in rows if row["kind"] == "unwrap"), \
        f"{[row['text'] for row in rows if row['kind'] == 'unwrap']}: every unwrap reads `json?.data ??` -- " \
        "a differently-spelled unwrap would turn a wrapped-but-empty payload into something other than null"
    assert [row["text"] for row in rows if row["kind"] == "success"] == [
        'if (!res.ok || !json.success || !json.data) return null;',
        'if (!res.ok || (json && json.success === false)) {',
    ], f"{[row['text'] for row in rows if row['kind'] == 'success']}: the envelope's own guards, measured"
    # 35 rather than 32: the contacts registry's three writes each carry one success toast,
    # after the growth report's one had joined in 10.3.
    # 32 rather than 33 since the single-upload "Document queued" toast left source-actions:
    # the batch uploader replaced it with live per-row ingestion progress, which is the
    # feedback now, and a toast on top of a visible progress row would be the second word.
    # 33 rather than 31 since the memory-correction surface joined: `useUpdateMemory` and
    # `useDeleteMemory` each carry one success toast in actions.ts.
    # 31 rather than 30 since the paste-a-posting importer joined (one success toast in
    # actions.ts); 30 rather than 28 since the conversation list grew rename and delete,
    # each with its own success toast in actions.ts.
    assert len(toasts) == 48, (f"{len(toasts)} `toast.success` lines came out of the same walk: that is "
                               "the floor proving the scan reached the pages and the hooks, so a walk "
                               "narrowed to the api directory cannot pass quietly")


def test_a_message_frame_reader_names_only_keys_the_orchestrator_emits():
    """#173: a `message` frame has one producer, and this test is the ledger of the reader's inventions.

    `orchestrator.py:277` publishes `_emit(task_id, "message", out.to_dict())`, and the Java relay only
    defaults a frame's name to `message` when the upstream had none (`SseRelayService.java:109`) while
    every ai-service frame carries an event name (`api/tasks.py:30`, `core/taskbus.py:29`). So the keys of
    `Outcome.to_dict` are the frame's shape. `use-sse.ts` re-dispatches inside the `message` case on
    `payload.type`, `payload.token` and `payload.data` -- three fields no producer writes, under a cast
    that made the invention look like a contract -- and its vitest fixtures fed exactly those shapes, so
    the tests prove the branch runs, not that it is reachable. The branch is therefore pinned rather than
    deleted: deleting it needs one live stream check, and runtime verification is blocked on the owner.
    """
    source = (_app_root() / "agents" / "orchestrator.py").read_text(encoding="utf-8")
    builder = source[source.index("def to_dict"):]
    emitted = set(re.findall(r'"([A-Za-z_]\w*)":', builder[:builder.index("\n\n")]))
    assert emitted == {"answer", "artifacts", "sources", "actions", "steps", "tools_used", "run_id"}, \
        (f"{sorted(emitted)} are the keys `Outcome.to_dict` writes: this frame's only producer, read off "
         "its own source rather than copied into a cast")

    use_sse = (ROOT_FRONTEND / "lib" / "sse" / "use-sse.ts").read_text(encoding="utf-8")
    cases = set(re.findall(r'\n\s+case "(\w+)":', use_sse))
    assert cases == {"status", "progress", "token", "trace", "artifact", "done", "message", "error",
                    "ping"}, (f"{sorted(cases)}: the frame names the client routes -- every producer "
                             "event is either handled or deliberately dropped")
    block = use_sse[use_sse.index('case "message"'):use_sse.index('case "error"')]
    named = set(re.findall(r"\bpayload\.(\w+)", block))
    assert named - emitted == {"data", "token", "type"}, \
        (f"{sorted(named)} are read off a `message` frame; {sorted(emitted)} are what the producer "
         "emits. This ledger expects the hole to still be exactly these three fields: if a producer "
         "starts writing `type`, the branch becomes live and the test has to be re-read; if the branch "
         "is deleted, this assertion goes red on purpose and the test should be retired with it -- not "
         "loosened")
    assert named & emitted == set(), (f"{sorted(named & emitted)} would already be answered by the "
                                     "producer, which would shrink the hole below the three fields pinned")
    assert sorted({h for h in ("onToken", "onStatus", "onTrace") if f"{h}?." in use_sse}) == \
        ["onStatus", "onToken", "onTrace"], (
            "the three signals the unreachable branch forwards already have named-event handlers, which "
            "is what makes the branch dead code rather than a feature")


def _published_frame_names() -> set[str]:
    """Every SSE event name any service can put on the wire, read off the publishing call sites.

    Three spellings cover them all on the Python side -- `publish(task_id, "<name>", …)`,
    `_emit(task_id, "<name>", …)` (whose one body forwards to publish with the name as a variable, so the
    literal call sites ARE the inventory), and `{"event": "<name>", …}` yields. The backend re-sends two of
    these names as literals and invents no third, which `_backend_frame_name_sites` measures rather than
    assumes (see #181: the first version of this rule counted one spelling and reported zero).
    """
    names: set[str] = set()
    for path in _app_root().rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        names.update(re.findall(r'publish\(\s*task_id\s*,\s*"(\w+)"', text))
        names.update(re.findall(r'_emit\(\s*task_id\s*,\s*"(\w+)"', text))
        names.update(re.findall(r'\{\s*"event":\s*"(\w+)"', text))
    return names


BACKEND_NAME_SPELLINGS = (
    ("event-builder", re.compile(r'\.name\(\s*"(\w+)"')),
    ("sink-send", re.compile(r'\bsink\.send\(\s*"(\w+)"')),
    ("listener-callback", re.compile(r'\bonFrame\(\s*"(\w+)"')),
)


def _backend_frame_name_sites() -> dict[str, dict[str, list[str]]]:
    """file -> spelling -> the literal frame names written that way, over the whole backend tree.

    #175 counted one spelling -- `.name("<literal>")`, the builder the relay uses with a *variable* -- and
    concluded the backend hard-codes nothing. It does: `CopilotStreamService` answers `sink.send("done", …)`
    and re-sends `sink.send("error", …)`, and `SseRelayService` invents `listener.onFrame("error", …)` when
    the upstream answers a non-200. The spelling stays in the key so a census narrowed to one of them cannot
    pass quietly, and the repeated `error` entries stay because they are four sites, not one.
    """
    sites: dict[str, dict[str, list[str]]] = {}
    for path in sorted(JAVA_ROOT.rglob("*.java")):
        text = path.read_text(encoding="utf-8")
        found = {label: sorted(names) for label, pattern in BACKEND_NAME_SPELLINGS
                 for names in [pattern.findall(text)] if names}
        if found:
            sites[path.name] = found
    return sites


def _java_frame_names() -> set[str]:
    """Frame names the backend puts on the wire itself rather than relaying -- measured two, not zero."""
    return {name for by_spelling in _backend_frame_name_sites().values()
            for names in by_spelling.values() for name in names}


def _relay_synthesized_names() -> dict[str, list[str]]:
    """The name the relay gives a frame that arrived with data but no `event:` line, per file.

    Scoped to the `onFrame(` calls that carry a ternary, because a whole-tree `X == null ? "y"` scan also
    matches unrelated defaults (`ResumeService.java` answers `category -> other`) and would then be a census
    of Java's null-coalescing rather than of frame names.
    """
    out: dict[str, list[str]] = {}
    for path in sorted(JAVA_ROOT.rglob("*.java")):
        text = path.read_text(encoding="utf-8")
        names = [m.group(1) for m in re.finditer(r'onFrame\([^?]*\?\s*"(\w+)"', text)]
        if names:
            out[path.name] = names
    return out


def _terminal_flag_cases(stream: str) -> tuple[set[str], set[str]]:
    """(every name the relay listener's switch intercepts, the subset that marks the turn finished).

    `boolean[] finished` is what makes `CopilotStreamService.run` answer `the turn ended before it produced
    an answer` instead of closing an empty stream, so an arm that forwards or persists without setting the
    flag is a hang-shaped defect, not a style choice.
    """
    arms = re.findall(r'case\s+"(\w+)"\s*->\s*\{([^{}]*)\}', stream)
    if not arms:
        raise AssertionError("the switch over relayed frames is gone, so its arms cannot be measured")
    return {name for name, _body in arms}, {
        name for name, body in arms if "finished[0] = true" in body}


def _bus_terminal_names() -> set[str]:
    """The event names `taskbus.subscribe` treats as the end of a run, read off the bus's own test."""
    bus = (_app_root() / "core" / "taskbus.py").read_text(encoding="utf-8")
    clause = re.findall(r'ev\.get\("event"\)\s+in\s+\(([^)]*)\)', bus)
    if len(clause) != 1:
        raise AssertionError(f"{len(clause)} terminal-name clauses on the bus, expected exactly 1: "
                             "the subscription loop's stop condition must be a single readable tuple")
    return set(re.findall(r'"(\w+)"', clause[0]))


def test_the_client_dispatches_two_frame_kinds_no_service_can_send():
    """#175: the frame inventory across three services, and the ledger of two cases that cannot fire.

    `use-sse.ts` routes nine event names; the services publish seven of them -- status, progress, done,
    error, token, message, ping. `artifact` and `trace` appear in no publishing call site anywhere: the
    string `"artifact"` does not occur in `ai-service/app` at all, `trace` frames are never published
    because `observability.trace()` writes to the database instead of the task bus, and the backend adds no
    name of its own beyond re-sending `done`/`error` (`SseRelayService.java:109`, `CopilotStreamService.java:126`).
    Yet `components/ai/task-stream.tsx:98` turns trace frames into timeline rows and :125 flips a reporting
    state on an artifact frame, so the affordance is wired to a signal nothing sends -- and
    `use-sse.test.ts:75-76` feeds both by hand, which is how it has stayed green.

    Pinned as a ledger rather than fixed: the deletion or the publication both change what a user sees,
    and the live check that would settle it is the owner-blocked R1. A row here shrinking means a producer
    finally exists and the component is no longer decorative; a row appearing means the client grew another
    unreachable case. Either way this test has to be re-read, not re-numericled.
    """
    published = _published_frame_names()
    assert published == {"status", "progress", "done", "error", "token", "message", "ping"}, \
        (f"{sorted(published)} are the frames any service can send, read off the publish/_emit/yield "
         "call sites -- the inventory the client's cases are measured against")
    invented = _java_frame_names()
    assert invented <= published, \
        (f"{sorted(invented)} are named as literals by the backend itself, which re-sends two frames it "
         "also relays. The claim this carries is not 'the backend invents nothing' (it does, see #181) but "
         "'no name reaches the browser outside the inventory above' -- a new name here means the inventory "
         "has to be re-read, not that this subset check should be widened")

    use_sse = (ROOT_FRONTEND / "lib" / "sse" / "use-sse.ts").read_text(encoding="utf-8")
    cases = set(re.findall(r'\n\s+case "(\w+)":', use_sse))
    assert cases - published == {"artifact", "trace"}, \
        (f"{sorted(cases - published)} are dispatched by the client but published by nobody: each one is "
         "a UI affordance wired to a signal that cannot arrive. Add a producer and this ledger shrinks; "
         "add another client-only case and it grows -- do not fix the expected set to match new drift")
    assert published - cases == set(), \
        (f"{sorted(published - cases)} are published but dropped by the client's switch, which is a "
         "silent loss rather than a ledger entry")
    consumers = (ROOT_FRONTEND / "components" / "ai" / "task-stream.tsx").read_text(encoding="utf-8")
    assert "onTrace:" in consumers and "onArtifact:" in consumers, \
        ("the ledger above is only about real readers: task-stream subscribes to both handlers, so this "
         "is a visible affordance and not dead weight in the hook alone")


def test_the_backend_is_the_only_reader_of_the_frame_key_the_browser_never_touches():
    """#181: the run stream read from the server's side -- who consumes a frame besides the browser.

    #175–#180 all measured one direction: what a service publishes, and what a `.tsx`/`.ts` file reads.
    The frames have a second consumer on the way. `SseRelayService.consume` parses the event stream and
    hands `(event, data)` to a `FrameListener`; `CopilotStreamService.run` implements that listener, and its
    switch intercepts `done` (persist the turn, then re-send `done` with the *stored* reply), `error` (forward
    it) and `ping` (drop it), leaving `default -> sink.send(event, data)` for everything else. So the backend
    both *names* frames as literals and *reads keys* out of one -- and `result`, which #180 recorded as
    published but unread, is unread only by the browser: `persist` asks the done payload for exactly
    `result` and `error`.
    """
    sites = _backend_frame_name_sites()
    assert sites == {"CopilotStreamService.java": {"sink-send": ["done", "error", "error", "error"]},
                     "SseRelayService.java": {"listener-callback": ["error"]}}, \
        (f"{sites}: the backend's own frame-name literals, per file and per spelling. The relay's "
         "`upstream status <code>` error is a *third* producer of the error frame whose data is not JSON at "
         "all, which is why the payload ledger below is read off the parsed holder rather than off every "
         "error site; a new spelling here is a name the browser can be handed without appearing in #175's "
         "inventory")
    assert sum(len(names) for by_spelling in sites.values() for names in by_spelling.values()) == 5, \
        ("five literal frame-name sites: the floor that proves the walk reached both relay paths, so a "
         "census narrowed to the builder spelling cannot pass this file quietly")

    intercepted, flag_sets = _terminal_flag_cases(
        (JAVA_ROOT / "com" / "careeros" / "conversation" / "service" / "CopilotStreamService.java")
        .read_text(encoding="utf-8"))
    bus_text = (_app_root() / "core" / "taskbus.py").read_text(encoding="utf-8")
    # `findall` with two groups yields pairs, so they are flattened rather than summed: `sum`
    # over tuples raises instead of measuring, and a walk that cannot run proves nothing.
    ternary_publishes = re.findall(
        r'publish\(task_id,\s*"(\w+)"\s*if\s+\w+\s+else\s*"(\w+)"', bus_text)
    assert len(ternary_publishes) == 1, \
        (f"{len(ternary_publishes)} ternary `publish(task_id, ...)` sites on the bus, expected exactly 1: "
         "`finish` is the only place the bus chooses a terminal frame, and a second spelling here would "
         "be a name this census never reads")
    can_publish = {name for pair in ternary_publishes for name in pair}
    assert can_publish == _bus_terminal_names() == flag_sets == {"done", "error"}, \
        (f"the bus publishes {sorted(can_publish)}, stops its own subscription on "
         f"{sorted(_bus_terminal_names())}, and the backend marks a turn answered on "
         f"{sorted(flag_sets)}: three planes must name the same two frames or a run streams forever. "
         "The `ping` case is intercepted without setting the flag, which is the keep-alive's whole job")
    assert intercepted - flag_sets == {"ping"}, \
        (f"{sorted(intercepted - flag_sets)} are swallowed by the backend without marking the turn "
         "finished: exactly the keep-alive, so nothing here ends the stream silently")

    listener_files = sorted({path.name for path in JAVA_ROOT.rglob("*.java")
                             if "FrameListener" in path.read_text(encoding="utf-8")
                             or re.search(r'\.consume\(', path.read_text(encoding="utf-8"))})
    assert listener_files == ["CopilotStreamService.java", "SseRelayService.java"], \
        (f"{listener_files} are the files that declare, take or call the frame listener: this is the "
         "population the key ledger below walks, derived rather than hand-picked")
    parsed = {}
    reads: set[str] = set()
    for name in listener_files:
        path = next(p for p in JAVA_ROOT.rglob("*.java") if p.name == name)
        text = path.read_text(encoding="utf-8")
        holders = re.findall(r'Map<String, Object>\s+(\w+)\s*=\s*[^;]*readValue\(', text)
        parsed[name] = holders
        for holder in holders:
            reads.update(re.findall(rf'\b{re.escape(holder)}\.(?:containsKey|get|getOrDefault)\("(\w+)"',
                                    text))
            reads.update(re.findall(rf'Json\.\w+\(\s*{re.escape(holder)}\s*,\s*"(\w+)"', text))
    assert parsed == {"CopilotStreamService.java": ["payload"],
                      "SseRelayService.java": []}, \
        (f"{parsed}: which listener file turns a frame's data into a parsed holder, because keys read off "
         "any other receiver would be request JSON, not a frame")
    emitted = _published_payload_keys()
    frame_keys = emitted.get("done", set()) | emitted.get("error", set())
    assert reads == {"error", "result"}, \
        (f"{sorted(reads)} are the keys the backend reads off a frame payload: `result` is the run's "
         "answer and `error` the reason it had none. The browser half of this claim is pinned separately "
         "in the table test's `member_reads`, which finds no frontend file reading `.result` at all")
    assert reads <= frame_keys, \
        (f"{sorted(reads - frame_keys)} would be keys the only consumer of the terminal frames reads and "
         "no producer writes -- a turn that can never be persisted, not a ledger row")

    synthesized = _relay_synthesized_names()
    assert synthesized == {"SseRelayService.java": ["message", "message"]}, \
        (f"{synthesized}: a frame that arrives with data but no `event:` line is handed on as `message`, "
         "so the one frame name the relay invents is a *default*, and #179 records that no shipped file "
         "implements `onMessage`. Unreachable through our own ai-service (every frame it writes carries an "
         "event name, `api/tasks.py:30`), live through any other upstream")
    assert set(synthesized.get("SseRelayService.java", [])) <= _published_frame_names(), \
        ("the defaulted name must still be in #175's inventory, or an unnamed frame reaches the browser "
         "under a name nothing routes")
    unscoped = {path.name for path in JAVA_ROOT.rglob("*.java")
                if re.search(r'\w+\s*==\s*null\s*\?\s*"\w+"', path.read_text(encoding="utf-8"))}
    assert len(unscoped) >= 2 and "ResumeService.java" in unscoped, \
        (f"{sorted(unscoped)}: the null-default shape is common in this backend, which is why the census "
         "above is scoped to `onFrame(` calls -- an unscoped scan would count unrelated defaults as frame "
         "names and the ledger would look longer than the wire")

    relay = (JAVA_ROOT / "com" / "careeros" / "ai" / "SseRelayService.java").read_text(encoding="utf-8")
    invented = re.findall(r'onFrame\(\s*"(\w+)",\s*(.+?)\);', relay)
    assert [name for name, _body in invented] == ["error"], \
        (f"{invented}: the frame names the relay hands a listener with a literal, which is the one place "
         "the backend adds a frame rather than forwarding one")
    json_authored = {name for name, body in invented
                     if "writeValueAsString" in body or "Map.of" in body}
    assert json_authored == set(), \
        (f"{json_authored} would be invented frames whose body the backend authors as JSON; measured none, "
         "because `SseRelayService.java:76` hands on `\"upstream status \" + response.statusCode()`, a bare "
         "string. So the name `error` reaches the browser in two shapes: an object with `error`/`result` "
         "from ai-service, and this plain text. Harmless today only because #180 records that no `onError` "
         "handler reads a key off its payload -- wire one up and this disagreement becomes the bug")
    feeds = (JAVA_ROOT.parent.parent / "test" / "java" / "com" / "careeros" / "conversation" / "service" /
             "CopilotStreamServiceTest.java").read_text(encoding="utf-8")
    assert "upstream status" not in feeds, \
        ("the Java suite drives the listener with done/status/token frames but never with the relay's own "
         "non-JSON error, so the shape disagreement above has no test on either side; if a case appears "
         "here, re-read this ledger rather than deleting the sentence")


PUBLISH_CALL = re.compile(r'(?:taskbus\.)?(?:publish|_emit)\(\s*task_id\s*,\s*"(\w+)"\s*,\s*')


def _published_payload_keys() -> dict[str, set[str]]:
    """event name -> the literal payload keys published with it, braces paired, not line-grabbed.

    The payload is often written across several lines (`ingestion/pipeline.py:69`), so a `[^\n]*` grab
    would silently lose the later keys -- the mistake #171 found in the TypeScript mirror of this rule.
    A payload that is a call rather than a literal is kept as a marker, because the census must not
    report "no keys" where the truth is "keys come from elsewhere".

    Two spellings publish a frame: the call sites `PUBLISH_CALL` walks, and the yield spelling
    `{"event": "<name>", "data": {…}}` that `taskbus.subscribe` and `core/ai.py` use. Only the first was
    read when #176 pinned its ledgers, so `error` and `ping` had no row at all -- and `error` is the frame
    whose `{error}` key `errorText` exists to read (#179 pairs them).

    #180 adds the third spelling, which is the *terminal* frame: `taskbus.finish` picks the event name and
    the payload with the same condition, so neither walk above matches it and `done` had no payload row
    while `error`'s row came only from `subscribe`'s "task not found" yield. See `_ternary_publish_rows`.
    """
    out: dict[str, set[str]] = {}
    for path in _app_root().rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for found in PUBLISH_CALL.finditer(text):
            start = found.end()
            if start < len(text) and text[start] == "{":
                depth, index = 0, start
                while index < len(text):
                    depth += text[index] == "{"
                    depth -= text[index] == "}"
                    index += 1
                    if depth == 0:
                        break
                payload = text[start:index]
            else:
                payload = text[start:text.index("\n", start)] if "\n" in text[start:] else text[start:]
            keys = set(re.findall(r'"(\w+)":', payload))
            if not keys and "(" in payload:
                keys = {f"<{payload.split('(')[0].strip()}>"}
            out.setdefault(found.group(1), set()).update(keys)
        for found in YIELD_FRAME.finditer(text):
            start = text.index("{", found.end() - 1)
            depth, index = 0, start
            while index < len(text):
                depth += text[index] == "{"
                depth -= text[index] == "}"
                index += 1
                if depth == 0:
                    break
            out.setdefault(found.group(1), set()).update(set(re.findall(r'"(\w+)":', text[start:index])))
        for name, keys in _ternary_publish_rows(text):
            out.setdefault(name, set()).update(keys)
    return out


YIELD_FRAME = re.compile(r'\{\s*"event":\s*"(\w+)",\s*"data":\s*\{')


def _balanced(text: str, start: int, opener: str, closer: str) -> str:
    """The characters from `start` (an `opener`) through the `closer` that empties the depth."""
    depth, index = 0, start
    while index < len(text):
        depth += text[index] == opener
        depth -= text[index] == closer
        index += 1
        if depth == 0:
            return text[start:index]
    raise AssertionError(f"no closing {closer!r} after offset {start}: an unpaired body would be read "
                         "as running to the end of the file")


def _function_body(text: str, name: str) -> str:
    """The body of `function <name>`, with its parameter list skipped rather than assumed empty."""
    at = re.search(rf"\bfunction\s+{re.escape(name)}\s*(?:<[^<>]*>)?\s*\(", text)
    if at is None:
        raise AssertionError(f"{name} is no longer declared, so the reads taken from its body below "
                             "would come from an empty string comparing nothing")
    params_at = at.end() - 1
    params = _balanced(text, params_at, "(", ")")
    brace = text.index("{", params_at + len(params))
    return _balanced(text, brace, "{", "}")


TERNARY_PUBLISH = re.compile(
    r'(?:taskbus\.)?(?:publish|_emit)\(\s*task_id\s*,\s*"(\w+)"\s+if\s+(\w+)\s+else\s+"(\w+)"\s*,\s*\{')
PAYLOAD_GATE = re.compile(r"\s*if\s+(not\s+)?(\w+)\s+else\s*\{")


def _literal_keys(text: str, at: int) -> tuple[set[str], int]:
    """The quoted keys of the `{…}` literal at `at`, plus the offset just past it."""
    group = _balanced(text, at, "{", "}")
    return set(re.findall(r'"(\w+)":', group)), at + len(group)


def _ternary_publish_rows(text: str) -> list[tuple[str, set[str]]]:
    """(frame name, payload keys) for a publish call that picks the name *and* the payload by condition.

    `taskbus.finish` (`core/taskbus.py:38`) is how every run ends, and neither walk in
    `_published_payload_keys` describes it: the event is `"done" if ok else "error"` and the payload on the
    same statement is `{"result": …, "error": …} if not ok else {"result": …}`. The consequence for #179's
    table was asymmetric and silent -- `error` looked like it carried one key (from `subscribe`'s separate
    "task not found" yield, which is a *different* publisher) while `done` carried no row at all, so
    `table["done"]["reads"] == []` read as "nobody reads a payload" about a payload the scan had never
    measured.

    The two conditionals are aligned by their own conditions, not by which dict looks like the success
    case: `X if C else Y` takes X when C holds, so a payload gated on `not <C>` puts its first branch with
    the *second* name. A site whose conditions do not line up that way raises, because attributing a
    payload to a frame by guesswork is the species of ledger this artifact exists to catch.
    """
    rows: list[tuple[str, set[str]]] = []
    for found in TERNARY_PUBLISH.finditer(text):
        true_name, condition, false_name = found.group(1), found.group(2), found.group(3)
        first, after = _literal_keys(text, found.end() - 1)
        gate = PAYLOAD_GATE.match(text, after)
        if gate is None:
            raise AssertionError(f"{true_name}/{false_name} are published on {condition!r} but the payload "
                                 f"is not a readable ternary at offset {after}: {text[after:after + 40]!r} "
                                 "-- without a gate the payload cannot be attributed to either name")
        second, _ = _literal_keys(text, gate.end() - 1)
        negated, gated = bool(gate.group(1)), gate.group(2)
        if gated != condition:
            raise AssertionError(f"{true_name}/{false_name} gate the name on {condition!r} but the payload "
                                 f"on {gated!r}: the alignment rule has no way to say which dict the "
                                 "success frame carries, so both rows below would be invented")
        rows.append((true_name, second if negated else first))
        rows.append((false_name, first if negated else second))
    return rows


def _handler_sites(text: str, spans: list[tuple[int, int, str]] | None = None,
                   vocabulary: set[str] | None = None) -> list[dict]:
    """The `onKey: (…) => {…}` subscribe sites in one file, with the fields that body reads.

    A subscribe site is distinguished from a declaration by its own shape: an interface writes
    `onDone?: (data: unknown) => void;` (note the `?` before the colon, and no body), while a subscriber
    writes `onDone: (data) => {`. Reading `task-stream.tsx` through the loose rule #177 first tried made
    its two interface lines look like subscriptions, so the file appeared to subscribe to frames it only
    offers to its own callers -- which is why this walks the colon-with-paren shape and pairs the body.

    `spans`, when given, is the second half of the same question: `onError:` is also react-query's option
    key, so a site only counts when it sits inside a call that hands handlers to a frame entry point.
    Without it the census reported three auth forms and twenty-odd mutation callbacks as stream readers.
    #180 adds the JSX twin of that rule, because the same relationship is written `<Entry onDone={…} />`
    when the entry point is a component: see `_jsx_entry_spans` and `_jsx_handler_sites`.

    `vocabulary` is the set of handler names a frame can reach; it defaults to the transport's own dispatch
    rather than to a list written here, so a name no frame carries cannot be counted as a subscription.
    """
    keys = sorted(_frame_handler_vocabulary() if vocabulary is None else vocabulary)
    rows: list[dict] = []
    for found in re.finditer(rf"\b({'|'.join(keys)})\s*:\s*\(", text):
        via = ""
        if spans is not None:
            hits = [(stop - start, entry) for start, stop, entry in spans if start <= found.start() < stop]
            if not hits:
                continue
            via = min(hits)[1]  # innermost enclosing call, when entry calls nest
        rows.append(_arrow_site(text, found.group(1), found.end() - 1, via))
    return rows


def _expression_body(text: str) -> str:
    """An arrow's expression body: up to the first `,`, `;` or closing bracket at depth zero.

    #179's slice for a handler without a `{…}` block looked for a `{` and, finding the next one several
    lines later, returned the *following* site's body -- `onArtifact: () => setReporting(true),` at
    `task-stream.tsx:125` was read as owning `onDone`'s statements. The reads taken from it stayed correct
    only because that handler has no parameter to read off. Bounding the expression at depth zero is what
    makes the body mean the body for `onToken: (t) => setText(t)` as well.
    """
    depth = 0
    for index, char in enumerate(text):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif char in ",;" and depth == 0:
            break
    else:
        return text.strip()
    return text[:index].strip()


def _arrow_site(text: str, handler: str, params_at: int, via: str = "") -> dict:
    """One subscribe site: its parameter list, its body, and the payload fields that body reads.

    Shared by the two spellings a handler is written in -- `onDone: (data) => {…}` as an object member and
    `onDone={(data) => {…}}` as a JSX attribute -- so a table row cannot describe one form while being
    blind to the other. Fields are read off the handler's own parameter, optionally chained (`data?.id`),
    because `tokenText` reads `d?.text` and a `\\.()`-only pattern loses it (#179).
    """
    params = _balanced(text, params_at, "(", ")")
    tail = text[params_at + len(params):]
    arrow = re.match(r"\s*(?:async\s*)?=>", tail)
    rest = tail[arrow.end():] if arrow else tail
    brace = rest.find("{")
    if brace >= 0 and not rest[:brace].strip():
        body = _balanced(rest, brace, "{", "}")
    else:
        body = _expression_body(rest)
    names: list[str] = []
    destructured: list[str] = []
    inner = params.strip()
    if re.fullmatch(r"\(\s*\w+\s*\)", inner):
        names = [re.sub(r"[() ]", "", inner)]
    else:
        dm = re.fullmatch(r"\(\s*\{([^}]*)\}\s*\)", inner)
        if dm:
            destructured = [n for n in re.split(r"[,\s]+", dm.group(1)) if re.fullmatch(r"\w+", n)]
    reads: set[str] = set()
    for var in names:
        reads |= set(re.findall(rf"\b{var}(?:\.|\?\.)(\w+)", body))
    return {"handler": handler, "via": via, "params": tuple(names),
            "destructured": tuple(destructured), "reads": reads | set(destructured), "body": body}


def _jsx_entry_spans(text: str, entries: set[str]) -> list[tuple[int, int, str]]:
    """Spans of `<Name …>` tags whose name is one of `entries`: the other spelling of an entry call.

    #179 admitted subscribers through `Name(…)` alone, which is how a hook is called and so missed how a
    component is used: `TaskProgress` takes a frame handler in its props, and two screens render it as
    `<TaskProgress … onDone={…} />`. The tag runs to the first `>` at brace depth zero, since an attribute
    expression may hold a comparison or another tag.
    """
    spans: list[tuple[int, int, str]] = []
    for name in sorted(entries):
        for tag in re.finditer(rf"<{re.escape(name)}(?=[\s/>])", text):
            depth, index, closed = 0, tag.start(), False
            while index < len(text):
                char = text[index]
                depth += char == "{"
                depth -= char == "}"
                if char == ">" and depth == 0:
                    closed = True
                    break
                index += 1
            if not closed:
                raise AssertionError(f"<{name} at offset {tag.start()} never closes outside its attribute "
                                     "expressions, so handler attributes taken from it would run to the end "
                                     "of the file")
            spans.append((tag.start(), index + 1, name))
    return spans


def _jsx_handler_sites(text: str, spans: list[tuple[int, int, str]],
                       vocabulary: set[str] | None = None) -> list[dict]:
    """The handler attributes inside `spans`, in the same site shape as `_handler_sites`.

    A JSX attribute and an object member name the same relationship -- the value is the callback -- so one
    table holds both spellings instead of reaching the same subscription twice by two rules. An attribute
    whose value is not an arrow (`onDone={forwarded}`) still counts as an edge, with no parameter to read
    off it; that is why it gets a row rather than being skipped.
    """
    keys = sorted(_frame_handler_vocabulary() if vocabulary is None else vocabulary)
    rows: list[dict] = []
    for start, stop, entry in spans:
        tag = text[start:stop]
        for found in re.finditer(rf"\b({'|'.join(keys)})\s*=\s*\{{", tag):
            value = _balanced(tag, found.end() - 1, "{", "}")
            if value.lstrip("{ \n\t").startswith("("):
                rows.append(_arrow_site(tag, found.group(1), tag.index("(", found.end() - 1), entry))
            else:
                rows.append({"handler": found.group(1), "via": entry, "params": (),
                             "destructured": (), "reads": set(), "body": value})
    return rows


def _case_blocks(text: str) -> list[tuple[str, str]]:
    """Each `case "<frame>":` label paired with the statements it actually runs.

    Two details are what make this a routing table rather than a slice of text. (1) The switch's own body
    bounds every block: #179 first read to the next label and let the last block (`case "ping": break;`)
    run on to the end of the file, which would have charged it any `h.on*?.(` call in the module.
    (2) A case label with no statements falls through to the next one -- `case "status":` at
    `use-sse.ts:191` is immediately followed by `case "progress":`, whose body calls `h.onStatus`. Read
    label-by-label, `status` appeared to route to *nothing*, which is the opposite of the fold #176
    depends on. So an empty block (comments stripped) borrows the next label's handlers.
    """
    switch = re.search(r"\bswitch\s*\(", text)
    if switch is None:
        raise AssertionError("use-sse.ts has no `switch`: the routing read here would be an empty dict "
                             "comparing nothing")
    body_at = text.index("{", switch.end())
    body = _balanced(text, body_at, "{", "}")
    cases = [(m.group(1), m.start(), m.end()) for m in re.finditer(r'\n\s*case "(\w+)":', body)]
    if not cases:
        raise AssertionError("the switch dispatches no `case` block, so no frame is routed by name")

    def statements(index: int) -> str:
        stop = cases[index + 1][1] if index + 1 < len(cases) else len(body)
        return body[cases[index][2]:stop]

    runs = {i for i in range(len(cases))
            if re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", statements(i)).strip()}
    if not runs:
        raise AssertionError("every case block is empty, so no handler is ever called -- the routing "
                             "below would compare nothing against nothing")
    out: list[tuple[str, str]] = []
    for index in sorted(runs):
        out.append((cases[index][0], statements(index)))
        for skipped in range(index - 1, -1, -1):
            if skipped in runs:
                break
            out.append((cases[skipped][0], statements(index)))
    return out


def _client_case_routing() -> dict[str, set[str]]:
    """frame name -> the handler keys the client invokes inside that case's block.

    This is the join the three #175/#176/#177a ledgers each held half of: `use-sse.ts` folds `status` and
    `progress` into one handler, re-dispatches a wrapped token/status/trace out of `message`, and drops
    `ping` on purpose, so a frame's readers are only findable from the case body that receives it.
    """
    text = (ROOT_FRONTEND / "lib" / "sse" / "use-sse.ts").read_text(encoding="utf-8")
    out: dict[str, set[str]] = {}
    for name, block in _case_blocks(text):
        out.setdefault(name, set()).update(re.findall(r"\bh\.(on\w+)\?\.\(", block))
    return out


HANDLER_MEMBER = re.compile(r"\b(on[A-Z]\w*)\s*\??\s*:")


@lru_cache(maxsize=1)
def _frame_handler_vocabulary() -> frozenset[str]:
    """The handler keys a frame can reach, read off the transport's own dispatch instead of my list.

    #179 wrote this as a literal alternation of eight names, and one of them -- `Progress` -- is invoked by
    no code in the app, because `status` and `progress` share `onStatus` (#176's fold). A hand-written
    vocabulary can therefore carry a name no wire ever sends, and every rule downstream would then be
    counting an affordance that does not exist. Deriving it from the two dispatch spellings the transport
    uses -- `h.on*?.(` inside the switch, `handlers.on*?.(` in the relay -- makes the vocabulary the same
    object as the routing table, and the test below compares it against the *type* that lists the frames a
    subscriber may be handed, which is a second author over the same fact.

    Deriving it also forces a distinction #179 never had to make: `handlersRef.current
    .onTransportError?.(` (`use-sse.ts:100`, `:128`) is a third invocation spelling, outside the switch,
    and `onTransportError` is absent from `SSEHandlers`' `Pick` list. It is live code that is *not* a frame
    handler -- the connection dropping is a different question from which frame arrived.
    """
    out: set[str] = set()
    out |= set(re.findall(r"\bh\.(on\w+)\s*\??\.\(",
                          (ROOT_FRONTEND / "lib" / "sse" / "use-sse.ts").read_text(encoding="utf-8")))
    out |= set(re.findall(r"\bhandlers\.(on\w+)\s*\??\.\(",
                          (ROOT_FRONTEND / "lib" / "api" / "client.ts").read_text(encoding="utf-8")))
    if not out:
        raise AssertionError("the transport invokes no `on*` handler in either spelling, so every rule "
                             "keyed on this vocabulary would be counting an empty set")
    return frozenset(out)


def _frame_handler_types(vocabulary: set[str] | None = None) -> set[str]:
    """Declared types that carry frame handlers, read off their own members or their `Pick` base.

    `UseSSEOptions` and `CopilotStreamHandlers` are interfaces with `onToken?:` members; `SSEHandlers` is
    `Pick<UseSSEOptions, …>`, so it joins through the type it picks from rather than because anything
    listed it here. This is the discriminator #179 had to find: naming `onError:` says nothing on its own,
    because react-query uses the same key for mutation callbacks.
    """
    keys = set(_frame_handler_vocabulary() if vocabulary is None else vocabulary)
    found: set[str] = set()
    picked: list[tuple[str, str]] = []
    for path in ROOT_FRONTEND.rglob("*.ts*"):
        if ".test." in path.name or "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for decl in re.finditer(r"\b(?:export\s+)?(?:interface|type)\s+(\w+)[^;{]*\{", text):
            body = _balanced(text, decl.end() - 1, "{", "}")
            if set(HANDLER_MEMBER.findall(body)) & keys:
                found.add(decl.group(1))
        picked += re.findall(r"\b(?:export\s+)?type\s+(\w+)\s*=\s*Pick<\s*(\w+)\s*,", text)
    for name, base in picked:
        if base in found:
            found.add(name)
    return found


def _frame_entry_fns(vocabulary: set[str] | None = None) -> set[str]:
    """Functions taking a handler-carrying parameter: the call sites through which a frame can arrive.

    `useSSE(options: UseSSEOptions)`, `postSSE(path, options, handlers: SSEHandlers)` and the app's own
    `useCopilotChat(stream: CopilotStreamHandlers)` qualify, so a subscription is recognised one hop past
    the hook -- which is how `app/(app)/copilot/page.tsx` is found even though it never imports the SSE
    module. `useMutation` does not: its option type is declared outside this tree and no member of it is a
    frame handler this scan can see. Only *named* parameter types count, so a handler typed inline at the
    declaration would be missed -- the subscriber census below would then lose a file and go red.
    """
    types = _frame_handler_types(vocabulary)
    if not types:
        raise AssertionError("no declared type in the frontend carries a frame handler, so the entry set "
                             "below is empty by accident rather than by measurement")
    annotated = re.compile(rf":\s*(?:\w+\s*=\s*)?(?:{'|'.join(sorted(types))})\b")
    out: set[str] = set()
    for path in ROOT_FRONTEND.rglob("*.ts*"):
        if ".test." in path.name or "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for decl in re.finditer(r"\b(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*(?:<[^<>]*>)?\s*\(", text):
            if annotated.search(_balanced(text, decl.end() - 1, "(", ")")):
                out.add(decl.group(1))
    return out


def _entry_call_spans(text: str, entries: set[str]) -> list[tuple[int, int, str]]:
    """Spans of calls that pass a handler object to one of `entries`, paren group paired."""
    spans: list[tuple[int, int, str]] = []
    for name in sorted(entries):
        for call in re.finditer(rf"\b{re.escape(name)}\s*(?:<[^<>]*>)?\s*\(", text):
            group = _balanced(text, call.end() - 1, "(", ")")
            spans.append((call.end() - 1, call.end() - 1 + len(group), name))
    return spans


TRANSPORT = ("lib/api/client.ts", "lib/sse/use-sse.ts")


def _frame_reader_population(vocabulary: set[str] | None = None
                             ) -> tuple[list[dict], list[dict], dict[str, str]]:
    """(subscribers, second-hand readers, transport) for the run stream, each derived by its own rule.

    A *subscriber* has at least one handler site inside a frame-entry call, written either as an object
    member inside `Name({onDone: …})` or as an attribute inside `<Name onDone={…} />` -- #179 read only the
    first, which is how a hook is called, so the two screens that subscribe by *rendering* a component were
    missing from the table. A *second-hand* reader is a file that walks a frame-shaped parameter but has no
    entry call of its own: `processing-steps.tsx` classifies a `StatusEvent` someone else received, and
    `agent-timeline.tsx` renders `AgentTraceEvent[]` rows that `task-stream.tsx` built out of a trace frame
    -- so its `evt.id` is a field of a locally declared row type, not a field any producer sends, which is
    the conflation this split exists to prevent. *Transport* is the two files that route frames without
    consuming them; a skip list with no reach guard is a hiding place (#167), so each travels with the
    evidence that it only forwards.
    """
    keys = _frame_handler_vocabulary() if vocabulary is None else vocabulary
    entries = _frame_entry_fns(keys)
    subscribers: list[dict] = []
    second_hand: list[dict] = []
    transport: dict[str, str] = {}
    for path in sorted(ROOT_FRONTEND.rglob("*.ts*")):
        if ".test." in path.name or "node_modules" in path.parts:
            continue
        rel = str(path.relative_to(ROOT_FRONTEND)).replace("\\", "/")
        text = path.read_text(encoding="utf-8")
        if rel in TRANSPORT:
            transport[rel] = text
            continue
        jsx = _jsx_entry_spans(text, entries)
        sites = (_handler_sites(text, _entry_call_spans(text, entries), keys)
                 + _jsx_handler_sites(text, jsx, keys))
        evt_reads = set(re.findall(r"\bevt(?:\.|\?\.)(\w+)", text))
        if sites:
            subscribers.append({"file": rel, "sites": sites, "evt_reads": evt_reads, "jsx_tags": len(jsx)})
        elif evt_reads:
            second_hand.append({"file": rel, "reads": evt_reads})
    return subscribers, second_hand, transport


def test_the_run_stream_contract_is_one_table_of_publishers_cases_and_subscribers():
    """#179: the frame inventory, the client's routing and the subscribers' reads in one artifact.

    Three earlier ledgers each held a slice of the same system: #173 pinned the `message` frame's invented
    fields, #175 pinned two cases no service can send, #176/#177a pinned which `status` keys the step panel
    drops and which the action hook consumes. This table joins them along the axis the app uses -- per frame
    name, the keys its publishers write, the handler the client's own case body invokes, and the fields each
    subscriber reads inside that handler, split by whether it subscribed at the transport (`useSSE`,
    `postSSE`, `dispatchEvent`) or one hop past it at a forwarding hook (`useCopilotChat`). The distinction
    matters because the forwarded reader does not see the frame: `app/(app)/copilot/page.tsx` destructures
    `{step}` out of the `{agent, step}` object `lib/hooks/actions.ts` rebuilds, so its reads are a subset of
    another file's by construction, and a table that merged the two would hide who is reading the wire.

    Four measurements had to be corrected before anything here could be pinned; all four were found by this
    unit instead of assumed. (1) `case "status":` and `case "progress":` at `use-sse.ts:191-193` are a
    *fall-through* pair, so slicing per label made `status` route to nothing -- the opposite of the fold
    #176 depends on; a now-empty block now borrows the next label's statements. (2) The last block's slice
    ran to the end of the file, which would have charged `ping` any later `h.on*?.(` call; the switch body
    now bounds it. (3) A reader scan matching only `x.field` loses `d?.text` in `tokenText`, so `text`
    looked produced-and-dropped while the client in fact reads it. (4) A census that asks "does this file
    name `onError:`" reports three auth forms and three react-query callbacks as stream readers, because
    `useMutation` borrows the same key name; admission now requires the site to sit inside a call whose
    callee takes a handler-carrying parameter, a rule read off the type declarations themselves.

    The ledgers are pinned rather than fixed, as before: `state`/`count`/`intent` reach no handler body,
    `onMessage` is invoked by the client and subscribed to by nobody, `artifact`/`trace` carry reads no
    producer can send, `tokenText` falls back to a `token` key no frame carries, and the terminal frames
    publish a `result` no handler reads. Each one shrinks only when a producer or a reader changes, and the
    owner-blocked R1 stream is what would settle them.

    #180 then found four more blind spots in this same artifact, which is where their pins live. (1)
    Admission understood `Name({onDone: …})` only -- the spelling a hook is called with -- so a component
    used as `<TaskProgress … onDone={…} />` was invisible, and the two resume screens that show a run's
    progress were missing from the table entirely. (2) The handler vocabulary was a hand-written list of key
    names; it is now read off the transport's own dispatch (`h.on*?.(` and `handlers.on*?.(`) and
    cross-checked against the `Pick<UseSSEOptions, …>` list that declares `SSEHandlers`, so a key only one
    of those two authors knows about fails the gate instead of going unnoticed. (3) An expression-bodied
    handler was sliced into the *next* site's body, because the scanner hunted for a `{` rather than
    stopping at the comma that ends the member. (4) `taskbus.finish` publishes its terminal frame through a
    `publish(id, "done" if ok else "error", {…} if not ok else {…})` ternary that the payload walk could not
    pair, so `done` and `error` were recorded as carrying no keys at all -- a limit of the scanner reported
    as a fact about the wire, which is exactly the species of lie this arc exists to catch.
    """
    published = _published_frame_names()
    emitted = _published_payload_keys()
    routing = _client_case_routing()
    vocab = _frame_handler_vocabulary()
    subscribers, second_hand, transport = _frame_reader_population()

    assert _frame_handler_types() == {"CopilotStreamHandlers", "SSEHandlers", "TaskProgressProps",
                                      "UseSSEOptions", "UseTaskStreamOptions"}, \
        ("the declared types that carry frame handlers changed: this is the vocabulary every subscribe "
         "site below is admitted by, so a new member renames the whole population")
    entries = _frame_entry_fns()
    assert entries == {"TaskProgress", "dispatchEvent", "postSSE", "useCopilotChat", "useSSE",
                       "useTaskStream"}, \
        (f"{sorted(entries)} are the functions a handler object can be handed to: a new one is a new "
         "route from a frame to a component and the table below has to grow a reader column for it")
    assert sorted(transport) == ["lib/api/client.ts", "lib/sse/use-sse.ts"], \
        "the transport pair changed, so the direct/forwarded split below is measuring something else"
    transport_src = "\n".join(transport.values())
    direct = {n for n in entries if re.search(rf"\bfunction\s+{re.escape(n)}\b", transport_src)}
    assert direct == {"dispatchEvent", "postSSE", "useSSE"}, \
        (f"{sorted(direct)} are the entries declared inside the transport: an entry that moves in or out "
         "of this set silently reclassifies a reader as direct or forwarded")
    assert set(re.findall(r"\bhandlers\.(on\w+)\s*\??\.\(", transport["lib/api/client.ts"])) == \
        {"onDone", "onError"}, \
        ("the relay invokes these handlers itself, beside `dispatchEvent`: two of the nine frames reach "
         "the browser through a path the switch above does not describe, so the exemption is a forward")
    assert set(re.findall(r"\bevt(?:\.|\?\.)(\w+)", transport["lib/sse/use-sse.ts"])) == {"data", "event"}, \
        ("the hook reads only the relay envelope's own two fields -- anything more is the hook consuming "
         "a frame, which would make it a reader and not transport")

    assert sorted(s["file"] for s in subscribers) == ["app/(app)/copilot/page.tsx",
                                                      "app/(app)/resumes/[id]/page.tsx",
                                                      "components/ai/task-stream.tsx",
                                                      "components/resumes/upload-dropzone.tsx",
                                                      "lib/hooks/actions.ts"], \
        (f"{sorted(s['file'] for s in subscribers)}: the files with a frame handler inside an entry call, "
         "written either as an object member or as a JSX attribute -- a new subscriber has to join the "
         "table below, and one that disappears means an affordance was deleted rather than left wired to "
         "nothing. The two `resumes` files only appear because #180 taught the walk the second spelling; "
         "under #179 they subscribed to a run's terminal frame and were counted as reading nothing")
    assert sorted(s["file"] for s in second_hand) == ["components/ai/agent-timeline.tsx",
                                                      "components/ai/processing-steps.tsx"], \
        ("second-hand readers walk a frame-shaped parameter without subscribing: `processing-steps.tsx` "
         "is #176's panel, and `agent-timeline.tsx` renders rows another file built -- not frame readers, "
         "and not invisible either")
    walked = [(str(p.relative_to(ROOT_FRONTEND)).replace("\\", "/"), p.read_text(encoding="utf-8"))
              for p in sorted(ROOT_FRONTEND.rglob("*.ts*"))
              if ".test." not in p.name and "node_modules" not in p.parts]
    # the two spellings, counted by the two scanners and over one walk, so a floor cannot be satisfied by
    # the half of the census that still works
    unscoped = {rel: [(0, len(text), "")] for rel, text in walked}
    object_shaped = {rel: len(_handler_sites(text)) for rel, text in walked}
    jsx_shaped = {rel: len(_jsx_handler_sites(text, unscoped[rel])) for rel, text in walked}
    shaped = {rel: object_shaped[rel] + jsx_shaped[rel] for rel in object_shaped}
    admitted = {s["file"]: len(s["sites"]) for s in subscribers}
    rejected_files = sorted(f for f, n in shaped.items() if n and f not in admitted and f not in transport)
    assert rejected_files == ["components/auth/credentials-form.tsx",
                              "components/auth/forgot-password-form.tsx",
                              "components/auth/reset-password-form.tsx",
                              "components/knowledge/source-actions.tsx"], \
        (f"{rejected_files} name handler-shaped callbacks the entry rule rejects: their `onError:` belongs "
         "to react-query, not to a stream. Under #177's shape-only census three of these were stream "
         "readers -- if this list empties, the walk stopped reading rather than the collision going away")
    assert sum(shaped.values()) >= 20 and sum(jsx_shaped.values()) >= 2, \
        (f"only {sum(shaped.values())} handler-shaped callbacks exist in the app "
         f"({sum(jsx_shaped.values())} of them in the JSX spelling), against the {shaped} counted per file: "
         "the shape scan is reading less than it did, so the rejection count above would be measuring a "
         "narrowed scan -- and a JSX count of zero means the second spelling stopped being scanned at all")
    assert admitted == {"app/(app)/copilot/page.tsx": 2,
                        "app/(app)/resumes/[id]/page.tsx": 1,
                        "components/ai/task-stream.tsx": 6,
                        "components/resumes/upload-dropzone.tsx": 1,
                        "lib/hooks/actions.ts": 2}, \
        (f"{admitted}: admitted handler sites per file. `actions.ts` names five, of which three are "
         "mutation callbacks and two are the stream's own onToken/onStatus -- the whole point of the rule. "
         "The two `resumes` rows are the single JSX `onDone={…}` attribute each screen renders on "
         "`<TaskProgress>`, one per pair of tags because the other tag has no handler")

    jsx_tags = {rel: len(_jsx_entry_spans(text, entries)) for rel, text in walked}
    assert {rel: n for rel, n in jsx_tags.items() if n} == {"app/(app)/resumes/[id]/page.tsx": 2,
                                                             "components/resumes/upload-dropzone.tsx": 2}, \
        (f"{jsx_tags}: every `<Entry …>` tag rendered in the app. A tag appearing outside the subscriber "
         "list above is a run whose frames no file handles, and a tag disappearing is a screen losing its "
         "affordance -- either way the table has to be re-read, not re-numericled")
    assert sum(jsx_tags.values()) == sum(s["jsx_tags"] for s in subscribers), \
        ("a rendered frame entry was counted app-wide but charged to no subscriber: the reach guard on the "
         "JSX spelling, so a component used outside an admitted file cannot hide from the table")

    # The walk above skips `*.test.*`. A skip list with no reach guard is a hiding place (#167), so this
    # proves both that nothing shipped reads through it and that the skipped set is a population, not an
    # empty match: the app's own transport tests do call the entry points, and are excluded on purpose.
    skipped = [(str(p.relative_to(ROOT_FRONTEND)).replace("\\", "/"), p.read_text(encoding="utf-8"))
               for p in sorted(ROOT_FRONTEND.rglob("*.ts*"))
               if ".test." in p.name and "node_modules" not in p.parts]
    # 31 rather than 25 since six test files joined: `lib/hooks/memories.test.ts` (the memory
    # correction surface's unit tests) plus five committed across concurrent sessions --
    # `app/globals.test.ts`, `components/layout/skip-link.test.ts`, `lib/session-expiry.test.ts`,
    # `lib/jd-text.test.ts`, `lib/interview-modes.test.ts`.
    # 25 rather than 24 since `lib/page-window.test.ts` joined: the unit test for the pager's
    # shared window arithmetic, which the census skips because a test proves the rule rather
    # than shipping it.
    # 24 rather than 23 since `lib/profile-targets.test.ts` joined (the gate on the settings page's
    # target-list guard, #216's front-end half).
    # 23 rather than 22 since `components/knowledge/source-actions.test.ts`, 22 rather than 21 since
    # `lib/api/missing-endpoint.test.ts`. The pin is a population, not a budget: a new test file belongs
    # in it, and the guard below still has to prove none of them ships.
    # 33 rather than 31 since `lib/hooks/actions.test.ts` and `lib/resume-upload.test.ts` joined.
    # 37 with the four that joined after that: `components/ai/agent-timeline.test.ts`,
    # `components/ai/task-stream.test.ts`, `lib/api/upload-limit-parity.test.ts` and
    # `lib/profile-maps.test.ts`. 41 with the four the forward bridges' own tests
    # added: `lib/api/normalize-followups.test.ts`, `lib/hooks/analytics.test.ts`,
    # `lib/i18n/translations.test.ts` and `components/common/bar-chart.test.tsx`.
    # 43 with the portability and ingestion bodies' own:
    # `lib/hooks/portability.test.ts`.
    # 44 with the copilot artifact renderers' own:
    # `components/copilot/artifacts.test.tsx`.
    # 45 with the collapsed sidebar's own:
    # `components/layout/collapsed-sidebar-tooltip.test.tsx`.
    # 46 with the action chips' own:
    # `lib/api/normalize-actions.test.ts`.
    # 47 with the landing page's own:
    # `app/landing-page.test.ts`.
    # 48 with the browser copy census' own:
    # `lib/i18n/copy-census.test.ts`.
    # 49 with the outreach draft's field names' own:
    # `lib/outreach-draft.test.ts`.
    # 51 with the score dimensions' own and the page title's own:
    # `lib/dimensions.test.ts` and `lib/i18n/metadata.test.ts`.
    # 52 with the used keys' own:
    # `lib/i18n/used-keys.test.ts`.
    # 53 with the error codes' own:
    # `lib/i18n/error-codes.test.ts`.
    # 54 joined with `components/jobs/job-card.test.tsx` (#264), and the pin took it as a floor rather
    # than a re-number. The sentence several lines above already calls this a population and not a
    # budget, but `== 53` capped it, so a legitimate new test file could only land by editing a number
    # in another service's suite -- which is how one gate can veto the other half of the repository.
    # The floor still refuses a walk that stopped reaching, and the claim the number never carried is
    # carried by the rule beside it: a non-test file inside this set is a subscriber hidden from the
    # table by the pattern rather than by measurement, and no total can tell you whether one is there.
    assert len(skipped) >= 53 and all(rel.endswith((".test.ts", ".test.tsx")) for rel, _t in skipped), \
        (f"{len(skipped)} files are skipped: either below the 53 that ship, which means the walk "
         "stopped reaching them, or one of them is not a test file -- and a name in that set that is "
         "not a test file would be a subscriber hidden from the table by the pattern rather than by "
         "measurement")
    skipped_names = {rel.rsplit("/", 1)[-1] for rel, _t in skipped}
    imported = [spec for _rel, text in walked for spec in re.findall(r"""from\s+['"]([^'"]+)['"]""", text)
                if spec.rsplit("/", 1)[-1] in skipped_names]
    assert imported == [], \
        (f"{imported}: shipped code importing a skipped file would make the skip list a reach hole, which "
         "is the one thing a census may not do while claiming to have read the app")
    entry_calls = {rel: len(_entry_call_spans(text, entries)) + len(_jsx_entry_spans(text, entries))
                   for rel, text in skipped}
    assert {rel: n for rel, n in entry_calls.items() if n} == {"lib/api/client.test.ts": 7,
                                                               "lib/api/endpoints.test.ts": 1,
                                                               "lib/sse/use-sse.test.ts": 9}, \
        (f"{entry_calls}: the entry-point calls living in the skipped set. These tests are why the frames "
         "have a client-side witness at all; the pin is here so that a zero means the walk stopped seeing "
         "them, not that the app's stream tests were deleted")

    frames = published | {"artifact", "trace"}
    table = {}
    for frame in sorted(frames):
        handler = routing.get(frame) or set()
        sites = [(r, s) for r in subscribers for s in r["sites"] if s["handler"] in handler]
        read: set[str] = set()
        for _row, site in sites:
            read |= site["reads"]
        table[frame] = {
            "handlers": sorted(handler),
            "direct": sorted({r["file"] for r, _s in sites if _s["via"] in direct}),
            "forwarded": sorted({r["file"] for r, _s in sites if _s["via"] not in direct}),
            "reads": sorted(read)}
    assert table == {
        "artifact": {"handlers": ["onArtifact"], "direct": ["components/ai/task-stream.tsx"],
                     "forwarded": [], "reads": []},
        "done": {"handlers": ["onDone"], "direct": ["components/ai/task-stream.tsx"],
                 "forwarded": ["app/(app)/resumes/[id]/page.tsx", "components/resumes/upload-dropzone.tsx"],
                 "reads": []},
        "error": {"handlers": ["onError"], "direct": ["components/ai/task-stream.tsx"],
                  "forwarded": [], "reads": []},
        "message": {"handlers": ["onMessage", "onStatus", "onToken", "onTrace"],
                    "direct": ["components/ai/task-stream.tsx", "lib/hooks/actions.ts"],
                    "forwarded": ["app/(app)/copilot/page.tsx"],
                    "reads": ["agent", "durationMs", "id", "kind", "label", "name", "payload", "status",
                              "step", "type"]},
        "ping": {"handlers": [], "direct": [], "forwarded": [], "reads": []},
        "progress": {"handlers": ["onStatus"],
                     "direct": ["components/ai/task-stream.tsx", "lib/hooks/actions.ts"],
                     "forwarded": ["app/(app)/copilot/page.tsx"], "reads": ["agent", "step"]},
        "status": {"handlers": ["onStatus"],
                   "direct": ["components/ai/task-stream.tsx", "lib/hooks/actions.ts"],
                   "forwarded": ["app/(app)/copilot/page.tsx"], "reads": ["agent", "step"]},
        "token": {"handlers": ["onToken"],
                  "direct": ["components/ai/task-stream.tsx", "lib/hooks/actions.ts"],
                  "forwarded": ["app/(app)/copilot/page.tsx"], "reads": []},
        "trace": {"handlers": ["onTrace"], "direct": ["components/ai/task-stream.tsx"],
                  "forwarded": [],
                  "reads": ["durationMs", "id", "kind", "label", "name", "payload", "status", "type"]},
    }, (f"the run-stream table changed as a whole: {table}")

    assert set(routing) == published | {"artifact", "trace"}, \
        (f"{sorted(set(routing))} are the cases the client dispatches against the {sorted(published)} it "
         "can receive: `artifact` and `trace` are the #175 ledger, counted here from the routing table "
         "rather than the case list")
    assert table["progress"] == table["status"], \
        ("`status` and `progress` no longer land on one handler, which is the fold #176's panel and the "
         "step list both depend on -- either they were split apart or the fall-through reading broke")
    assert routing["ping"] == set() and table["ping"]["reads"] == [], \
        (f"ping now reaches {table['ping']}: the heartbeat was dropped on purpose (no step, no text), so a "
         "reader appearing means either the frame grew a payload or something started polling on it")
    assert emitted.get("ping", set()) == set(), \
        (f"the `ping` frame carries {sorted(emitted.get('ping', set()))} keys, where an empty list means it "
         "has no payload row at all: the heartbeat was dropped because nothing writes it, so either change "
         "is a change to what the client throws away")

    assert emitted["status"] - set(table["status"]["reads"]) == {"count", "intent", "state"}, \
        (f"{sorted(emitted['status'] - set(table['status']['reads']))} are published by a `status` payload "
         "and not touched inside any handler body: `state` reaches the second-hand panel (#176) while "
         "`count` and `intent` reach nothing in the app -- re-read from source if a row appears")
    assert set(routing["message"]) - {s["handler"] for r in subscribers for s in r["sites"]} == {"onMessage"}, \
        ("the client calls `onMessage` for every message frame and no file in the app subscribes to it: "
         "the answer a run reports lands in `done`, so this handler is a third unreachable case beside "
         "`artifact`/`trace` -- #173's dead re-dispatch has a reader-shaped twin")
    assert emitted.get("error", set()) == {"error", "result"}, \
        (f"the `error` frame carries {sorted(emitted.get('error', set()))} keys: `error` comes from the "
         "`yield {event: error, data: {error}}` spelling #179 added to the scan, and `result` from the "
         "`taskbus.finish` ternary #180 added -- an empty list here means one of the two publish forms "
         "stopped being read, not that the frame went payload-free")
    assert emitted.get("done", set()) == {"result"}, \
        (f"the terminal `done` frame carries {sorted(emitted.get('done', set()))}: the ternary at "
         "`core/taskbus.py:37` publishes `{result}` for a run that finished and `{result, error}` for one "
         "that failed, on one line the earlier payload walk could not pair, so `done` looked keyless in "
         "#179's own table")

    # #180's ledger: that `result` is published and read by nobody. Scoped to what was measured -- no
    # shipped file touches a `.result` member anywhere, and the handlers a terminal frame reaches read
    # nothing off their payload at all. The answer a run reports therefore lands on the JSON plane (the
    # screens refetch), not on the stream, which is why an `onDone` body looks like `resume.refetch()`.
    terminal = [s for r in subscribers for s in r["sites"] if s["handler"] in ("onDone", "onError")]
    assert len(terminal) == 4 and not any(s["reads"] for s in terminal), \
        (f"{[(s['handler'], sorted(s['reads'])) for s in terminal]}: the app's terminal-frame handlers, four "
         "of them across three files, and none reads a field off the payload. A read appearing here retires "
         "this ledger and makes the stream the source of the answer instead of the JSON refetch; a count "
         "shrinking means a screen stopped handling the run it renders")
    member_reads = {rel for rel, text in walked if re.search(r"\b\w+\??\.result\b", text)}
    assert member_reads == set(), \
        (f"{sorted(member_reads)} read a `.result` member somewhere in the shipped browser files: the "
         "terminal frame publishes that key and no browser code consumes it, so a new reader here either "
         "wires `done` up for real or reads a `result` that came from another plane -- the claim above has "
         "to be re-read either way. This population is the frontend only: the backend does read "
         "`done.result`, which #181 pins in `CopilotStreamService`")

    # #180's vocabulary is derived, and the derivation is cross-checked against its independent author: the
    # `Pick<UseSSEOptions, …>` that types the handlers argument of `postSSE`.
    sse_source = transport["lib/sse/use-sse.ts"]
    pick = re.search(r"\bexport\s+type\s+SSEHandlers\s*=\s*Pick<\s*UseSSEOptions\s*,([^>]*)>", sse_source, re.S)
    assert pick is not None, \
        ("`SSEHandlers` is no longer a `Pick` of `UseSSEOptions`: that type is the second, independent "
         "author of the frame-handler vocabulary, and without it the derived set below has one witness "
         "instead of two")
    picked = sorted(re.findall(r'"(\w+)"', pick.group(1)))
    assert picked == sorted(vocab) and len(vocab) == 7, \
        (f"the transport dispatches {sorted(vocab)} and `SSEHandlers` picks {picked}: two authors of one "
         "fact, the hook's own switch and the type that lets callers hand handlers to the relay. They may "
         "not drift, and a vocabulary that derived as the empty set would make every census below pass by "
         "reading nothing")
    declared: set[str] = set()
    for type_name in _frame_handler_types():
        for rel, text in walked:
            decl = re.search(rf"\b(?:export\s+)?(?:interface|type)\s+{re.escape(type_name)}[^;{{]*\{{", text)
            if decl:
                declared |= set(HANDLER_MEMBER.findall(_balanced(text, decl.end() - 1, "{", "}")))
    assert declared - set(vocab) == {"onTransportError"}, \
        (f"{sorted(declared - set(vocab))} are handler names some type declares that no frame can reach: "
         "`onTransportError` is live code -- see its two invocations below -- but it is not a frame "
         "handler, so it must not be admitted by name shape. A new name here is either a frame the client "
         "cannot route or a callback this gate is being asked to treat as a subscription")
    assert re.findall(r"\bhandlersRef\.current\.(on\w+)\s*\??\.\(", sse_source) == \
        ["onTransportError", "onTransportError"], \
        ("`onTransportError` is invoked exactly twice, outside the frame switch, where the EventSource "
         "itself fails: the vocabulary excludes it because it is a different kind of signal, not because "
         "it is dead -- the count is what separates those two readings")
    error_body = _function_body(transport["lib/sse/use-sse.ts"], "errorText")
    assert re.search(r"\)\s*\?\.\s*error\b", error_body), \
        ("`errorText` no longer reads the `error` key off its argument, so the pairing between the "
         "published error frame and the only function that turns it into a sentence is broken")
    token_body = _function_body(transport["lib/sse/use-sse.ts"], "tokenText")
    hook_token_reads = set(re.findall(r"\bd\??\.(\w+)", token_body))
    assert hook_token_reads == {"text", "token"}, \
        (f"{sorted(hook_token_reads)} are what the hook unwraps a token frame with: `text` is the only key "
         "a producer sends, so losing it means the streamed delta stops reaching the screen and growing "
         "means another invented fallback has joined `tokenText`")
    assert {"text", "token"} - emitted["token"] == {"token"}, \
        ("`tokenText` still falls back to a `token` key that no producer writes -- the same species of "
         "invented field #176 counted in the step panel, now on the client's own hot path")
    assert not set(table["token"]["reads"]), \
        ("a subscriber started reading fields off a token frame: the hook already collapsed it to a "
         "string, so dotted reads here would be reads of a `string`, not of a payload")

    ghost = set(table["trace"]["reads"]) | set(table["artifact"]["reads"])
    emitted_keys = set()
    for keys in emitted.values():
        emitted_keys |= keys
    assert ghost == {"durationMs", "id", "kind", "label", "name", "payload", "status", "type"}, \
        f"{sorted(ghost)}: the reads the timeline turns into rows"
    assert ghost & emitted_keys == set(), \
        (f"{sorted(ghost & emitted_keys)} would be trace fields a producer finally sends, which retires "
         "part of #175's ledger and means the affordance is wired up rather than decorative")
    timeline = next(r for r in second_hand if r["file"].endswith("agent-timeline.tsx"))
    assert set(timeline["reads"]) <= set(table["trace"]["reads"]), \
        (f"{sorted(timeline['reads'])} are what `{timeline['file']}` reads off its rows: they must stay a "
         "subset of what a trace frame is asked for, because that component's rows are built from those "
         "frames by `task-stream.tsx` -- if it starts reading a field nothing asks for, the hop is no "
         "longer what the docstring claims")


def test_the_three_new_scanners_refuse_the_shapes_that_would_have_invented_a_row():
    """#180: each new scanner is walked over a snippet whose shape the app does not contain yet.

    The pins in the table above measure the app as it is written, which means they cannot witness the
    branches that keep a *future* shape from being invented. Three rules are exactly that kind: a JSX tag
    that never closes, a ternary publish whose name-gate and payload-gate disagree, and an
    expression-bodied handler that is the last member of its object. None appears in the tree today --
    `task-stream.tsx` closes every handler with a block, `taskbus.finish` aligns its two gates by
    authorship rather than by construction, and the only unclosed-looking tag in the app is a multiline
    component that does close. So the guards are walked over snippets that carry those shapes, and each
    snippet is paired with the real spelling it imitates: the JSX entry from `resumes/[id]/page.tsx:155`,
    the fall-through-free `onArtifact: () => setReporting(true),` from `task-stream.tsx:125`, and the
    terminal publish from `core/taskbus.py:38`.
    """
    import pytest

    # 1. A JSX tag that runs past its attribute expressions must refuse, not silently swallow the file.
    closed = '<TaskProgress\n  taskId={id}\n  onDone={() => refetch()}\n/>\n'
    spans = _jsx_entry_spans(closed, {"TaskProgress"})
    assert len(spans) == 1 and _jsx_handler_sites(closed, spans)[0]["handler"] == "onDone", \
        (f"{spans}: the render spelling of an entry call, read across its newlines -- the rule that "
         "admits the two resume screens, so a scanner that only matched one-line tags finds no subscriber "
         "and the table loses rows it never had")
    unterminated = '<TaskProgress onDone={() => {\n  refetch();\n'
    with pytest.raises(AssertionError, match="never closes"):
        _jsx_entry_spans(unterminated, {"TaskProgress"})

    # 2. The ternary publish pairs name-gate and payload-gate; a disagreement is a refusal, not a guess.
    aligned = _ternary_publish_rows(
        'publish(task_id, "done" if ok else "error",\n'
        '        {"result": result, "error": error} if not ok else {"result": result})')
    assert dict(aligned) == {"done": {"result"}, "error": {"result", "error"}}, \
        (f"{dict(aligned)}: the negated payload gate puts its first branch with the *second* name; read it "
         "the other way round and the table would attribute an error's `error` key to a successful run")
    with pytest.raises(AssertionError, match="not a readable ternary"):
        _ternary_publish_rows('publish(task_id, "done" if ok else "error", {"result": result})')
    with pytest.raises(AssertionError, match="but the payload on"):
        _ternary_publish_rows('publish(task_id, "done" if ok else "error",\n'
                              '        {"a": 1} if failed else {"b": 2})')

    # 3. An expression-bodied handler is the *last* member: no comma ends it, the closing brace does.
    last_member = 'const h = {\n  onArtifact: () => setReporting(true)\n};\nconst x = 1;\n'
    sites = _handler_sites(last_member, vocabulary={"onArtifact"})
    assert len(sites) == 1 and sites[0]["body"] == "setReporting(true)", \
        (f"{[s['body'] for s in sites]}: the expression body stops at the object's own brace, so the next "
         "statement cannot be read as part of the handler -- #179's slice ran on and handed `onArtifact` "
         "someone else's statements")
    assert _expression_body("setReporting(true)") == "setReporting(true)", \
        "an expression with no terminator is still the whole body"
    swallowed = _expression_body("setReporting(true),\n onDone: (data) => { setText(data.text) }\n});")
    assert swallowed == "setReporting(true)", \
        (f"{swallowed!r}: the comma ends the member -- a body that reaches past it is how one handler "
         "acquires another's payload reads, and those reads would then be charged to the wrong frame")


def test_the_step_classifier_reads_three_fields_no_frame_ever_carries():
    """#176: what the run stream actually sends, and what the step panel pretends to receive.

    `use-sse.ts` folds `status` and `progress` into one handler, so
    `components/ai/processing-steps.tsx` sees both kinds. Paired off the publishing call sites, the
    payloads are: status = {step, state} from the ingestion and rag pipelines, plus {intent} (rag:31) and
    {count} (rag:70), and {agent, step} from the orchestrator's three sites -- which is why a copilot step
    can never read `state`; progress = {step, done, total} (`ingestion/pipeline.py:82`). The component
    reads `evt.state ?? evt.status`, then `evt.progress === 100`, then `evt.label ?? … ?? evt.step`:
    `status`, `progress` and `label` are written by no producer at all, and the middle one reads like a
    confusion between the frame's *name* and a field it would carry. Mirror image: `count` and `intent` are produced and read by nobody, while `agent` and `step`
    are produced and consumed by `lib/hooks/actions.ts` instead of by this panel -- the last three
    assertions pin exactly that split, so the ledger cannot be misread as "`agent` goes nowhere".

    Pinned as two ledgers rather than fixed. Making the classifiers honest (drop the dead fallbacks, or
    send `label`/`state` for copilot steps) changes what a user sees on a live run, and the check that
    would confirm the change is the owner-blocked R1 stream. A shrinking ledger means a field gained a
    producer or a reader; growing means new drift. Either way the expected sets are re-read from source,
    not re-numericled.
    """
    published = _published_payload_keys()
    assert published["status"] == {"step", "state", "intent", "count", "agent"}, \
        (f"{sorted(published['status'])} are the keys any `status` payload writes; the classifier's "
         "reads are measured against exactly this list")
    assert published["progress"] == {"step", "done", "total"}, \
        f"{sorted(published['progress'])} -- `progress` is a frame name, and its fields are these"
    assert published["token"] == {"text"} and published["message"] == {"<out.to_dict>"}, \
        (f"{published} the remaining published payloads: a token carries text, and the message frame's "
         "keys come from `Outcome.to_dict()`, which #173 pins elsewhere")

    steps = (ROOT_FRONTEND / "components" / "ai" / "processing-steps.tsx").read_text(encoding="utf-8")
    reads = set(re.findall(r"\bevt\.(\w+)", steps))
    assert reads == {"state", "status", "progress", "done", "total", "step", "label"}, \
        f"{sorted(reads)} are the fields the panel reads off a frame"
    produced = published["status"] | published["progress"]
    assert reads - produced == {"label", "progress", "status"}, \
        (f"{sorted(reads - produced)} are read with no producer: `evt.state ?? evt.status` falls back to "
         "a field no frame carries, `evt.progress === 100` tests for a field that exists only as an event "
         "name, and `evt.label` is invented before falling through to `evt.step`. This ledger expects "
         "exactly these three -- fix the producer or the reader, then re-read this from source")
    assert produced - reads == {"agent", "count", "intent"}, \
        (f"{sorted(produced - reads)} are published and dropped by the panel, which is the mirror image "
         "of the hole above and is recorded rather than silently ignored")

    # ... dropped by *this* panel, not by the app: the orchestrator's own status fields are consumed
    # elsewhere, so the sentence above is scoped to the file it measured. Naming the second reader keeps
    # the ledger from being read as "`agent` goes nowhere", which would be false.
    actions = (ROOT_FRONTEND / "lib" / "hooks" / "actions.ts").read_text(encoding="utf-8")
    forwarded = set(re.findall(r"\bdata\.(\w+)", actions))
    assert forwarded == {"agent", "step"}, \
        (f"{sorted(forwarded)} are what the copilot action hook reads off a status frame, which is where "
         "`agent` actually lands -- if this drifts, the panel's dropped-field ledger above has to be "
         "re-read, because the two together are what the app consumes")
    assert forwarded <= published["status"], \
        (f"{sorted(forwarded - published['status'])} would be read by the action hook with no producer")
    assert published["status"] - reads - forwarded == {"count", "intent"}, \
        (f"{sorted(published['status'] - reads - forwarded)} are the status fields no reader in the app "
         "touches -- rag extras published and then dropped everywhere, not just in the panel")


ERROR_BODY_CALL = re.compile(r'(?:sink\.send|onFrame)\(\s*"error"\s*,\s*([^;]*?)\)\s*;')
ERROR_BODY_SHAPES = (
    ("json-authored", lambda body: "writeValueAsString(" in body),
    ("json-literal", lambda body: body.startswith('"{')),
    ("string-concat", lambda body: re.search(r'"\s*\+|\+\s*"', body) is not None),
    ("verbatim", lambda body: re.fullmatch(r"\w+", body) is not None),
)
# How a Java body spelling reaches the browser's `data:` line once the sink writes it.
WIRE_FROM_SHAPE = {"json-authored": "object", "json-literal": "object", "string-concat": "string",
                   "verbatim": "object"}


def _error_frame_bodies() -> dict[str, dict[str, list[str]]]:
    """file -> shape -> the bodies written that way by a site that *names* the `error` frame.

    #181 counted the frame names the backend writes itself. This is the payload half of the same sites:
    what shape of body each of those `error` names carries. A body the classifier cannot name raises rather
    than being skipped, because an unnamed third shape reaching the browser is exactly the event the ledger
    below exists to make loud -- and the classifier is ordered, so `writeValueAsString` wins over the `+`
    test instead of competing with it.
    """
    sites: dict[str, dict[str, list[str]]] = {}
    unknown: list[str] = []
    for path in sorted(JAVA_ROOT.rglob("*.java")):
        for found in ERROR_BODY_CALL.finditer(path.read_text(encoding="utf-8")):
            body = " ".join(found.group(1).split())
            shape = next((label for label, test in ERROR_BODY_SHAPES if test(body)), None)
            if shape is None:
                unknown.append(f"{path.name}: {body!r}")
                continue
            sites.setdefault(path.name, {}).setdefault(shape, []).append(body)
    if unknown:
        raise AssertionError(f"{unknown} are `error`-named frame bodies this classifier has no name for. "
                             "Either that is a shape no browser branch handles -- open the ledger and pay "
                             "for it -- or the classifier needs the new spelling, which is a claim about "
                             "the wire, not a detail of this file")
    return sites


def _string_type_checks(body: str) -> list[str]:
    """The operands of every `typeof X === "string"` test in a body, in the order the reader tries them."""
    return [operand.strip() for operand in re.findall(r'typeof\s+([^=]+?)\s*===\s*"string"', body)]


METHOD_HEAD = re.compile(r"\b(?:private|public|protected)\s+(?:static\s+)?[\w<>[\], ?]+\s+(\w+)\s*\(([^)]*)\)"
                         r"\s*(?:throws [\w, ]+)?\{")


def _enclosing_method(text: str, at: int) -> tuple[str, str]:
    """(name, parameter list) of the last method header written before `at`.

    #182's first attempt at the type question searched the whole file for `String reason` and passed while
    the parameter was retyped to `Object`, because the same file declares a *method* named `reason` that
    returns `String`. A declaration search has to bind the declaration the site sits in, which is what the
    nearest preceding header gives -- and a site whose header cannot be found raises instead of reporting a
    silent None.
    """
    heads = [(start, name, params) for start, name, params in
             ((m.start(), m.group(1), m.group(2)) for m in METHOD_HEAD.finditer(text)) if start < at]
    if not heads:
        raise AssertionError(f"no method header before offset {at}: the site's declaring method cannot be "
                             "read, so its parameter types would be reported as missing rather than unknown")
    _, name, params = max(heads)
    return name, params


def _authored_error_types() -> list[dict]:
    """Per site that authors an `error` payload: the value written under the key and what declares it."""
    rows: list[dict] = []
    for path in sorted(JAVA_ROOT.rglob("*.java")):
        text = path.read_text(encoding="utf-8")
        for found in ERROR_BODY_CALL.finditer(text):
            body = " ".join(found.group(1).split())
            shape = next((label for label, test in ERROR_BODY_SHAPES if test(body)), None)
            if shape not in ("json-authored", "json-literal"):
                continue
            method, params = _enclosing_method(text, found.start())
            if shape == "json-authored":
                value = re.search(r'Map\.of\("error",\s*(\w+)\)', body)
                if value is None:
                    raise AssertionError(f"{path.name} authors an `error` frame without a readable "
                                         f"`Map.of(\"error\", …)`: {body!r}")
                declared = re.search(rf"\b(\w+)\s+{value.group(1)}\b", params)
                rows.append({"file": path.name, "method": method, "author": "parameter",
                             "value": value.group(1),
                             "declared": declared.group(1) if declared else None})
            else:
                rows.append({"file": path.name, "method": method, "author": "literal", "value": None,
                             "declared": "quoted" if re.search(r'\\"error\\":\\"', body) else "not-a-string"})
    return rows


def _error_text_sites() -> dict[str, dict[str, int]]:
    """file -> {definition, calls} for `errorText`, the one helper that turns an error frame into a sentence.

    Counted over the same frontend population #179 walks (tests excluded), and split by whether the
    occurrence follows the word `function`: a doc link (`{@link errorText}`) carries no paren and so costs
    nothing here, while a renamed or duplicated helper would show up as two definitions.
    """
    rows: dict[str, dict[str, int]] = {}
    for path in sorted(ROOT_FRONTEND.rglob("*.ts*")):
        if ".test." in path.name:
            continue
        text = path.read_text(encoding="utf-8")
        definition = calls = 0
        for found in re.finditer(r"\berrorText\(", text):
            if re.search(r"\bfunction\s*$", text[: found.start()]):
                definition += 1
            else:
                calls += 1
        if definition or calls:
            rows[str(path.relative_to(ROOT_FRONTEND)).replace("\\", "/")] = {"definition": definition,
                                                                            "calls": calls}
    return rows


def test_the_error_frame_reaches_the_browser_in_two_shapes_and_one_helper_names_both():
    """#182: the payload side of the `error` frame, from the Java site that writes it to the branch that reads it.

    #175 inventoried frame *names*, #179 tabulated per-name payloads and handler bodies, #181 proved the
    backend names `error` as a literal and that the relay invents one frame whose data is not JSON. This
    unit walks the remaining inch: one name carries two wire shapes, and the browser's answer to that is a
    single helper. Measured on the backend, four sites name `error` and build their bodies three different
    ways -- `CopilotStreamService.fail()` authors JSON, its own catch sends a JSON *literal*, and the
    listener's `case "error"` forwards the relay's string untouched -- while `SseRelayService.consume` puts
    `"upstream status " + statusCode()` on the frame it invents when the ai-service answers non-200. The
    verbatim forward is what makes the browser's shape undecidable from any one sender: the same Java line
    carries either our service's `{"result": …, "error": …}` dict or that bare string.

    On the browser side the whole of that reaches exactly one reader. `use-sse.ts`'s dispatch calls
    `h.onError?.(evt.data)` without naming a key; the only subscriber to `onError` in the app is
    `task-stream.tsx`, whose body reads nothing off the payload and hands it to `errorText`; and `errorText`
    tries two `typeof … === "string"` tests -- the payload itself, then `data.error` -- before returning
    null. So the two branches and the two wire shapes are the same pair, seen from either end, and the key
    the second branch names is a key the publisher really writes. Pinned as a reconciliation, not a fix:
    both shapes have a live producer (the string one fires when ai-service answers 500 or times out), so
    which of them a user has ever seen is R1's question, not this file's.
    """
    sites = _error_frame_bodies()
    assert sites == {"CopilotStreamService.java": {
                         "verbatim": ["data"],
                         "json-authored": ['json.writeValueAsString(Map.of("error", reason))'],
                         "json-literal": [r'"{\"error\":\"the turn failed\"}"'],
                     },
                     "SseRelayService.java": {"string-concat": [
                         '"upstream status " + response.statusCode()']}}, \
        (f"{sites}: every site that names the `error` frame, with the body it writes, per shape. The "
         "`verbatim` row is the load-bearing one -- it is why the browser cannot know a shape from the "
         "sender -- and a body this classifier cannot name raises instead of vanishing")
    assert sum(len(bodies) for shapes in sites.values() for bodies in shapes.values()) == 4, \
        ("four `error`-named sites: the floor is taken from the same walk above, so a narrowed classifier "
         "or a skipped file cannot pass the rest of this test quietly")

    wire = {WIRE_FROM_SHAPE[shape] for shapes in sites.values() for shape in shapes}
    assert wire == {"object", "string"}, \
        (f"{sorted(wire)} are the shapes the `error` name can reach the browser in. `object` because "
         "`fail()` writes JSON and the listener forwards our own service's dict; `string` because the "
         "relay's invented frame carries a concatenated status line, not JSON at all")

    stream_text = (JAVA_ROOT / "com" / "careeros" / "conversation" / "service"
                   / "CopilotStreamService.java").read_text(encoding="utf-8")
    listener_at = re.search(r"relay\.consume\([^;]*?,\s*\(([^)]*)\)\s*->", stream_text, re.S)
    assert listener_at is not None, \
        ("the listener is no longer written inline on the `relay.consume` call, so the parameter names "
         "below cannot be read off it -- re-derive where the forwarded body comes from rather than "
         "letting an empty parameter set pass a subset test")
    params = {name.strip() for name in listener_at.group(1).split(",")}
    forwarded = {body for shapes in sites.values() for body in shapes.get("verbatim", [])}
    assert forwarded and forwarded <= params, \
        (f"{sorted(forwarded)} are the bodies the backend forwards instead of authoring, and "
         f"{sorted(params)} are the listener's own parameters: a forwarded body must be the data the "
         "relay handed in, because `WIRE_FROM_SHAPE` maps `verbatim` to the object our service publishes. "
         "A locally built string at that call site would be a *third* shape wearing a known spelling")

    published = _published_payload_keys()
    assert published["error"] == {"result", "error"}, \
        (f"{sorted(published['error'])} are the keys `taskbus.finish` writes into an `error` payload "
         "(`core/taskbus.py:38`, through the ternary scanner #180 added): the body the `verbatim` site "
         "forwards, so the object half of `wire` is this dict, not a guess")

    authored = _authored_error_types()
    assert authored == [{"file": "CopilotStreamService.java", "method": "fail", "author": "parameter",
                         "value": "reason", "declared": "String"},
                        {"file": "CopilotStreamService.java", "method": "fail", "author": "literal",
                         "value": None, "declared": "quoted"}], \
        (f"{authored}: each site that authors an `error` payload, the method that declares it, and what "
         "type the value under `error` is written as. `declared` is read from that method's own parameter "
         "list, not from anywhere in the file -- a `String` elsewhere proves nothing about this call. "
         "`errorText`'s second branch is `typeof data.error === \"string\"`, so an author that retypes the "
         "value (or writes an object inside the literal) is a *third* wire shape that the census above "
         "would still count as two")
    counted = sum(1 for shapes in sites.values() for shape, bodies in shapes.items()
                  if shape in ("json-authored", "json-literal") for _ in bodies)
    assert len(authored) == counted, \
        (f"{len(authored)} authored rows against {counted} json-shaped bodies in the census above: the "
         "two walks must agree about which files hold an `error` site at all, or a payload type check "
         "silently covers a subset of the producers")

    sse = (ROOT_FRONTEND / "lib" / "sse" / "use-sse.ts").read_text(encoding="utf-8")
    helper = _function_body(sse, "errorText")
    checks = _string_type_checks(helper)
    assert checks == ["data", "(data as { error?: unknown } | null)?.error"], \
        (f"{checks}: the two `typeof … === \"string\"` tests the reader tries, in the order it tries them. "
         "The first names the payload itself (the relay's string), the second a key of it (every other "
         "producer) -- a third test here means a new wire shape, and this file requires it to be produced")
    handled = {"string" if operand == "data" else "object" for operand in checks}
    assert handled == wire, \
        (f"the reader names {sorted(handled)} and the wire carries {sorted(wire)}: unequal either way is "
         "a real disagreement -- a branch no producer reaches, or a shape that arrives and is dropped to "
         "null without anyone deciding that")
    keys = {match.group(1) for operand in checks for match in [re.search(r"\.(\w+)$", operand)] if match}
    assert keys <= published["error"], \
        (f"{sorted(keys)} are the payload keys `errorText` reads by name, checked against the keys the "
         "publisher writes: a branch on a key no `error` payload has is the #173 disease in the reader "
         "rather than the dispatcher")
    assert helper.count("return null") == 2, \
        (f"{helper.count('return null')} `return null` exits in errorText: one for a payload whose shape "
         "neither test names, one for a cause whose first line is blank. A shape that cannot be read is "
         "reported as no message, which is what keeps `task-stream.tsx`'s own fallback sentence honest")

    subscribers, _second, _transport = _frame_reader_population()
    error_sites = [(row["file"], site) for row in subscribers
                   for site in row["sites"] if site["handler"] == "onError"]
    assert [file for file, _ in error_sites] == ["components/ai/task-stream.tsx"], \
        (f"{[file for file, _ in error_sites]} are the admitted subscribers to the `error` frame -- one, "
         "and it is inside a `useSSE(…)` call, which is why the react-query `onError` options in "
         "`lib/hooks/actions.ts` and the three auth forms are not counted as stream readers (#179's "
         "admission rule)")
    assert all(site["reads"] == set() for _, site in error_sites), \
        (f"{[sorted(site['reads']) for _, site in error_sites]} are the fields the subscriber reads off "
         "the payload: none, because it hands the whole payload to `errorText` instead of naming a key -- "
         "that is the shape-agnosticism the reconciliation above depends on")
    assert all("errorText(" in site["body"] for _, site in error_sites), \
        "the one subscriber funnels through the helper rather than re-implementing its branches"

    rows = _error_text_sites()
    assert rows == {"components/ai/task-stream.tsx": {"definition": 0, "calls": 1},
                    "lib/api/client.ts": {"definition": 0, "calls": 1},
                    "lib/sse/use-sse.ts": {"definition": 1, "calls": 0}}, \
        (f"{rows}: one definition and exactly two calls app-wide. The pair is the whole readership of the "
         "`error` frame's payload -- a component that renders the cause and the transport that rejects with it")
    callers = {file for file, counts in rows.items() if counts["calls"]}
    assert callers <= {file for file, _ in error_sites} | set(TRANSPORT), \
        (f"{sorted(callers)} call the helper, and each is either an admitted `onError` subscriber or one of "
         "the two transport files: a new caller outside both is a new reader of a frame nobody declared it "
         "to")

    error_block = dict(_case_blocks(sse))["error"].split("break;")[0]
    assert re.findall(r"\bh\.(\w+)\?\.\((\w+\.\w+)\)", error_block) == [("onError", "evt.data")], \
        (f"{error_block.strip()}: the dispatch forwards the parsed payload untouched and names no key, so "
         "the two shapes survive routing intact -- `use-sse.ts` is a router here, and the only place a key "
         "of an `error` payload is read is the helper above")
    assert _client_case_routing()["error"] == {"onError"}, \
        ("the client routes the name to exactly one handler, which is the join #179's table already "
         "holds and this test re-reads rather than restates")


# ---------------------------------------------------------------------------- the heartbeat's one definer

TASKBUS_PATH = Path(__file__).resolve().parents[1] / "app" / "core" / "taskbus.py"
AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
KEEP_ALIVE_NOUN = re.compile(r"\b(ping|keep-?alive|heartbeat)\b", re.I)
SECONDS_CLAIM = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:s\b|seconds?\b|sec\b)")


def _comment_spans(text: str) -> list[tuple[int, str]]:
    """(first line number, joined body) for each comment span in a file -- one per span, not per line.

    The span, not the line, is the unit because the claim in `CopilotStreamService.java` is written
    across two `//` lines: "the task bus's 15s keep-alive" on one and "every 15 seconds" on the next.
    A line-scoped scan sees one number where the file states two, so it would also miss a comment
    that drops the interval from the line carrying the noun and keeps it on the continuation.
    """
    out: list[tuple[int, str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("/*"):
            start, buf = i + 1, []
            while i < len(lines):
                buf.append(lines[i].strip().strip("/*").strip(" *").strip())
                closed = "*/" in lines[i]
                i += 1
                if closed:
                    break
            out.append((start, "\n".join(buf)))
            continue
        marker = "//" if stripped.startswith("//") else "#" if stripped.startswith("#") else None
        if marker is None or (marker == "#" and stripped.startswith("#!")):
            i += 1
            continue
        start, buf = i + 1, []
        while i < len(lines):
            s = lines[i].strip()
            if not s.startswith(marker):
                break
            buf.append(s.lstrip(marker[0]).lstrip("/").strip())
            i += 1
        out.append((start, "\n".join(buf)))
    return out


def _walk_shipped_code():
    """Yield (label, path, text) for every shipped source file in the three code trees."""
    roots = (("ai-service/app", AI_SERVICE_ROOT / "app"),
             ("backend/src/main/java", JAVA_ROOT),
             ("frontend/src", ROOT_FRONTEND))
    for label, root in roots:
        for path in sorted(root.rglob("*")):
            if path.suffix not in (".py", ".java", ".ts", ".tsx"):
                continue
            yield label, path, path.read_text(encoding="utf-8", errors="replace")


def _keep_alive_prose() -> tuple[list[dict], list[dict]]:
    """(claims, vocabulary) in `docs/*.md`, where a paragraph -- not a comment -- is the unit.

    Prose has no comment marker, so each line is its own span here; that is the same shape as the
    claim this population exists to catch, and a multi-sentence claim in one line still reads.
    """
    claims, vocabulary = [], []
    for path in sorted(DOCS_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            if not KEEP_ALIVE_NOUN.search(line):
                continue
            row = {"file": path.name, "line": number, "seconds": SECONDS_CLAIM.findall(line),
                   "text": line.strip()[:160]}
            (claims if row["seconds"] else vocabulary).append(row)
    return claims, vocabulary


def _keep_alive_spans() -> dict[str, list[dict]]:
    """Every shipped comment that names the run stream's keep-alive, in the three shapes one can write it.

    A span that starts a line (`// ...`, `# ...`, `/* ... */`), and a trailing comment after code, are
    different spellings and the second one is invisible to a span scan -- `SseRelayService.java` and
    `use-sse.ts` both carry the word `keep-alive` that way. All three are censused, and each is split on
    whether it states an interval, because a claim that loses its number is the shape this ledger would
    otherwise stop seeing.
    """
    claims, vocabulary, in_tests, trailing = [], [], [], []
    for _label, path, text in _walk_shipped_code():
        rel = str(path.relative_to(AI_SERVICE_ROOT.parent)).replace("\\", "/")
        is_test = ".test." in path.name or path.name.startswith("test_")
        for start, body in _comment_spans(text):
            if not KEEP_ALIVE_NOUN.search(body):
                continue
            row = {"file": rel, "line": start, "seconds": SECONDS_CLAIM.findall(body),
                   "text": body.replace("\n", " ")[:200]}
            if is_test:
                in_tests.append(row)
            elif row["seconds"]:
                claims.append(row)
            else:
                vocabulary.append(row)
        for number, line in enumerate(text.splitlines(), 1):
            marker = re.search(r"(?://|#)\s*(\S.*)$", line)
            if marker is None or line.strip().startswith(("//", "#")):
                continue
            note = marker.group(1)
            if not KEEP_ALIVE_NOUN.search(note):
                continue
            row = {"file": rel, "line": number, "seconds": SECONDS_CLAIM.findall(note),
                   "text": note.strip()[:160]}
            if is_test:
                in_tests.append(row)
            elif row["seconds"]:
                claims.append(row)
            else:
                trailing.append(row)
    return {"claims": claims, "vocabulary": vocabulary, "in_tests": in_tests, "trailing": trailing}


def _heartbeat_declaration() -> dict:
    """What `subscribe` declares its heartbeat to be, read off the signature that carries the default.

    The number a reader can find is the number the browser's comments can be checked against, so a
    default that moves behind a name is reported as unreadable rather than guessed at.
    """
    tree = ast.parse(TASKBUS_PATH.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) or node.name != "subscribe":
            continue
        names = [a.arg for a in node.args.args]
        if "heartbeat_s" not in names:
            found.append({"file": TASKBUS_PATH.name, "function": node.name, "lineno": node.lineno,
                          "seconds": None, "note": "declares no heartbeat_s parameter"})
            continue
        at = names.index("heartbeat_s")
        defaults = node.args.defaults
        offset = at - (len(names) - len(defaults))
        if offset < 0:
            found.append({"file": TASKBUS_PATH.name, "function": node.name, "lineno": node.lineno,
                          "seconds": None, "note": "heartbeat_s has no default to read"})
            continue
        node_default = defaults[offset]
        found.append({"file": TASKBUS_PATH.name, "function": node.name, "lineno": node.lineno,
                      "seconds": node_default.value if isinstance(node_default, ast.Constant)
                      and isinstance(node_default.value, (int, float)) else None,
                      "note": type(node_default).__name__})
    assert len(found) == 1, \
        (f"{found}: exactly one `subscribe` in `app/core/taskbus.py` is the definer of the run stream's "
         "heartbeat -- two would mean the claims below have no single number to be checked against")
    return found[0]


def _heartbeat_arguments() -> dict[str, list[dict]]:
    """Where `heartbeat_s` appears in Python source, split by what the occurrence *is*.

    Declared / overridden / read are different facts and only the last two are calls: the ledger needs
    to say which file passes a non-default interval, because an override in shipped code would make
    every comment about the default true of a number that no longer runs.
    """
    kinds: dict[str, list[dict]] = {"declared": [], "overridden": [], "read": []}
    for path in sorted(AI_SERVICE_ROOT.rglob("*.py")):
        if any(part.startswith(".") or part == "__pycache__" for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(AI_SERVICE_ROOT)).replace("\\", "/")
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and \
                    any(a.arg == "heartbeat_s" for a in node.args.args):
                kinds["declared"].append({"file": rel, "line": node.lineno, "function": node.name})
            elif isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "heartbeat_s":
                        value = ast.get_source_segment(text, kw.value)
                        kinds["overridden"].append({"file": rel, "line": node.lineno, "value": value})
            elif isinstance(node, ast.Name) and node.id == "heartbeat_s" \
                    and isinstance(node.ctx, ast.Load):
                kinds["read"].append({"file": rel, "line": node.lineno})
    return kinds


def test_the_heartbeat_interval_has_one_definer_and_every_shipped_claim_names_it():
    """`heartbeat_s` is defined once, in one language, and stated in comments in two others.

    ai-service owns the number: `subscribe()` waits that long for the next event and answers a silent
    run with `{"event": "ping"}`. The backend's stream router and the browser's router each carry a
    comment saying "15s" -- one of them to justify *dropping* the frame, the other to explain why
    nothing renders it.
    Those comments are the only place a maintainer learns the interval without opening Python, and
    nothing tied them to the default: retune `heartbeat_s` to 5 and the relay still promises a browser
    a blank frame every fifteen seconds, which is the kind of sentence people quote.

    So the rule asks the definer first, and reads the claims as spans for the same reason a reader
    does -- the Java comment is two lines long and a line-scoped scan sees half of it.
    """
    declared = _heartbeat_declaration()
    assert declared["seconds"] == 15.0 and declared["file"] == "taskbus.py", \
        (f"{declared}: the heartbeat's definer, its number, and how it is spelled -- a default that is "
         "no longer a readable literal cannot be checked against prose, so this is the failure to fix "
         "first")

    spans = _keep_alive_spans()
    assert [(row["file"], row["line"]) for row in spans["claims"]] == [
        ("backend/src/main/java/com/careeros/conversation/service/CopilotStreamService.java", 96),
        ("frontend/src/lib/sse/use-sse.ts", 232),
    ], ("which shipped comments state the keep-alive's interval: a new claim is a new sentence to hold "
        "against the code and a vanished one is a reader losing the answer. The Java pair is one span "
        "across two lines, which is why this reads spans rather than lines; what each says is checked "
        "against the definer below, so an edit to a number lands there and an edit to the site list "
        "lands here")
    claimed = [float(s) for row in spans["claims"] for s in row["seconds"]]
    assert len(claimed) == 3, \
        (f"{claimed}: the floor comes from the same walk as the census above, so an empty or narrowed "
         "scan cannot satisfy this by reading nothing")
    assert all(s == declared["seconds"] for s in claimed), \
        (f"{claimed} against the declared {declared['seconds']}: a comment naming a different interval "
         "is the defect this test exists for -- the number the browser and the relay promise is the "
         "number taskbus.subscribe does not use")

    doc_claims, doc_vocabulary = _keep_alive_prose()
    assert doc_claims == [], \
        (f"{doc_claims}: `docs/` states the keep-alive without a number today, and a doc that quotes an "
         "interval is a claim this gate has to be able to check rather than a second opinion")
    assert [(row["file"], row["line"]) for row in doc_vocabulary] == [
        # SECURITY.md's keep-alive mention moved again (148 -> 150): the 10.2 bridge's `/growth`
        # joined the throttle list above it, the sentence itself unchanged. AGENTS.md's moved
        # 144 -> 150 for the same reason: the networking subagent's §2 whitelist row and the four
        # §4 tool rows joined the tables above it, and that sentence did not change either. It
        # moved once more to 159 when the deterministic-engines section (§7) and the
        # tool table's growth rows joined the file below it -- again the sentence
        # itself is untouched. Now 162: the tracker's `list_applications` row and the
        # interview surface's two read rows joined the §4 tool table above it, and the
        # sentence still says the same thing.
        ("AGENTS.md", 162), ("DEPLOYMENT.md", 8), ("SECURITY.md", 150),
    ], (f"{doc_vocabulary}: the docs' own vocabulary is censused, so this pass is not reporting on an "
        "empty set -- and a second file picking up the word is a signal the ledger has to grow")

    assert [(row["file"], row["line"]) for row in spans["vocabulary"]] == [
        ("frontend/src/components/ai/task-stream.tsx", 17),
        ("frontend/src/lib/sse/use-sse.ts", 9),
    ], ("spans that name the keep-alive and state no interval: the shape an edited claim leaves behind, "
        "listed so a claim cannot escape the census above by losing its number")
    assert [(row["file"], row["line"]) for row in spans["trailing"]] == [
        ("backend/src/main/java/com/careeros/ai/SseRelayService.java", 116),
        ("frontend/src/lib/sse/use-sse.ts", 253),
    ], ("the other spelling -- a comment after code, which a span scan cannot see -- and neither states "
        "an interval: both say a line beginning with `:` is a keep-alive the parser skips, so the "
        "population this gate reports on is every shipped mention of the word, in both shapes")
    assert all(not row["seconds"] for row in spans["vocabulary"] + spans["trailing"]) \
        and all(row["seconds"] for row in spans["claims"]), \
        ("the populations are disjoint by construction -- one walk per spelling, split on whether a "
         "number is present -- so nothing can be filed in two of them and reconciled in neither")
    assert spans["in_tests"] == [], \
        (f"{spans['in_tests']}: the exclusion that keeps test files out of the claim ledger is measured "
         "here rather than assumed -- a test that states an interval states a claim about production")

    args = _heartbeat_arguments()
    assert args["declared"] == [{"file": "app/core/taskbus.py", "line": 58, "function": "subscribe"}], \
        (f"{args['declared']}: exactly one Python signature declares the parameter, which is what makes "
         "it a definer rather than one caller among many")
    assert args["read"] == [{"file": "app/core/taskbus.py", "line": 72}], \
        (f"{args['read']}: the interval is consumed once, as the `wait_for` timeout that ends a quiet "
         "wait with a `ping` -- the sentence the comments above repeat")
    assert [row["file"] for row in args["overridden"]] == ["tests/test_core_modules.py"] * 3 \
        and all(float(row["value"]) < declared["seconds"] for row in args["overridden"]), \
        (f"{args['overridden']}: every override of the heartbeat lives in the offline tests and shortens "
         "it, which is why the tests can run fast without proving a different interval -- an override in "
         "shipped code would make every claim above true of a number nothing uses")


# ------------------------------------------------------------------- the nameless-frame default
REPO_ROOT = Path(__file__).resolve().parents[2]
RELAY_PATH = JAVA_ROOT / "com" / "careeros" / "ai" / "SseRelayService.java"
CLIENT_PATH = ROOT_FRONTEND / "lib" / "sse" / "use-sse.ts"
NAMELESS_TOKEN = re.compile(r'\?\s*"message"|=\s*"message"|\|\s*"message"|:\s*"message"')
PRUNED_DIRS = {"node_modules", "__pycache__", "dist", "build", ".next", ".venv"}
# The floor `python_files(REPO_ROOT)` read off `git archive HEAD` at the ref this census was widened.
# A floor and not an equality: the walk grows with the repository, and it only has to refuse the run
# when part of the tree stopped being walked.
MIN_PY_POPULATION = 260


def python_files(root: Path) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in PRUNED_DIRS and not d.startswith(".")]
        found += [Path(dirpath) / f for f in filenames if f.endswith(".py")]
    return sorted(found)


def rel_of(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def is_offline(rel: str) -> bool:
    """Whether the running service can never reach this file: it lives in the tree pytest loads.

    `tests` as a path segment, not `test_` as a name prefix -- thirteen helpers under `ai-service/tests/`
    carry no `test_` name, and a caller census that called them shipped would report a shipped caller for
    a file the service never imports.
    """
    return "tests" in rel.split("/")[:-1]


def _event_source_writers() -> list[str]:
    """Every shipped module that hands a stream to `sse-starlette`, named by path."""
    return [rel for rel in (rel_of(p) for p in python_files(REPO_ROOT))
            if not is_offline(rel)
            and re.search(r"EventSourceResponse\s*\(",
                          (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace"))]


def _sse_call_sites() -> list[tuple[str, str, bool]]:
    """(file, enclosing function, offline) for every call named `sse` in the repository's Python."""
    rows: list[tuple[str, str, bool]] = []
    for path in python_files(REPO_ROOT):
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            # A file the census could not parse is a file it cannot clear, and an empty caller list
            # reads as a statement about the whole population. Nothing shipped is unreadable today,
            # so this is a refusal rather than a skip.
            raise AssertionError(f"{rel_of(path)}: walked by the census but it does not parse")
        # Identify each call by the function that encloses it, not by its line number.
        # The claim worth pinning is *which* offline test calls `sse()`; a line number
        # also asserts "and nothing was inserted above it", which is not part of the
        # claim -- it broke the moment an unrelated test was added to the file, and the
        # failure message trains a reader to bump the number rather than re-read this.
        funcs = [(n.name, n.lineno, n.end_lineno or n.lineno) for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

        def enclosing(lineno: int) -> str:
            inner = [(name, start) for name, start, end in funcs if start <= lineno <= end]
            return max(inner, key=lambda t: t[1])[0] if inner else "<module>"

        rel = rel_of(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                if name == "sse":
                    rows.append((rel, enclosing(node.lineno), is_offline(rel)))
    return rows


def _parser_body(text: str, header: str, label: str) -> tuple[str, int]:
    """(body, offset of its opening brace) for the function or method whose header matches `header`.

    Containment is the point: `#184`'s first census was a token scan for `"message"` and it counted the
    browser's *trace step kind* list -- `"handoff" | "message" | "final"` -- as if it defaulted a frame
    name. Reading the parser's own body admits a site by where it sits, not by what the word looks like.
    """
    at = re.search(header, text)
    if at is None:
        raise AssertionError(f"{label} is no longer declared where the frame parsers are read from, so "
                             "the default taken out of its body would be missing rather than changed")
    paren = text.index("(", at.start())
    params = _balanced(text, paren, "(", ")")
    brace = text.index("{", paren + len(params))
    return _balanced(text, brace, "{", "}"), brace


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _nameless_frame_defaults() -> list[dict]:
    """What each shipped SSE parser calls a frame that arrives with data and no `event:` line.

    Two languages parse this stream: the Java relay between ai-service and the browser, and the
    browser's own `parseFrame`. Each has to invent a name when the wire omits one (the SSE spec's answer
    is `message`), and the two inventions have to agree -- a relay that re-sends a name the client's
    router does not default to is a frame that silently goes nowhere.
    """
    relay_text = RELAY_PATH.read_text(encoding="utf-8")
    client_text = CLIENT_PATH.read_text(encoding="utf-8")
    relay, relay_at = _parser_body(relay_text, r"\bvoid\s+readFrames\s*\(", "SseRelayService.readFrames")
    client, client_at = _parser_body(client_text, r"\bfunction\s+parseFrame\s*\(", "parseFrame")
    rows = []
    for m in re.finditer(r'(\w+)\s*==\s*null\s*\?\s*"(\w+)"', relay):
        rows.append({"file": "SseRelayService.java", "language": "java", "enclosing": "readFrames",
                     "line": _line_of(relay_text, relay_at + m.start()),
                     "guard": m.group(1), "default": m.group(2)})
    declared = re.findall(r'\blet\s+(\w+)\s*=\s*"(\w+)"', client)
    if len(declared) != 1:
        raise AssertionError(f"{len(declared)} defaulted event-name bindings in parseFrame, expected 1: "
                             "with none the client's default cannot be read, and with two the frame's "
                             "name would be decided twice in one parse")
    name, value = declared[0]
    at = client.index(f'{name} = "{value}"')
    rows.append({"file": "use-sse.ts", "language": "ts", "enclosing": "parseFrame",
                 "line": _line_of(client_text, client_at + at), "guard": None, "default": value})
    return rows


def _union_block(lines: list[str], index: int) -> tuple[str, set[str]]:
    """(head line, every quoted name in the union) for the union carrying `lines[index]`.

    Two spellings have to be read: `event: SSEEventName | "message" | …` is a union written on one line,
    while `kind:` and `export type TraceKind =` continue theirs on the following `|`-led lines. Walking
    out from the occurrence finds both, and the head names the declaration the union belongs to -- which
    is what separates a frame-name union from a trace step kind that happens to share the spelling.
    """
    top = index
    while top > 0 and lines[top - 1].strip().startswith("|"):
        top -= 1
    bottom = index
    while bottom + 1 < len(lines) and lines[bottom + 1].strip().startswith("|"):
        bottom += 1
    if top == index and not lines[index].strip().startswith("|"):
        head, body = lines[index].strip(), lines[index]
    else:
        head = lines[top - 1].strip() if top > 0 else ""
        body = "\n".join(lines[top:bottom + 1])
    return head, set(re.findall(r'"(\w+)"', body))


def _message_token_census() -> list[dict]:
    """Every shipped Java or browser-TS line where `"message"` sits in a value position, classified.

    The classification is the deliverable, not the count. A scan for the token sweeps in three different
    vocabularies -- a frame-name default, a frame-name type union, and a trace step kind that happens to
    be spelled `message` -- and a ledger that reads them as one population would report on the wrong
    system. Positions are found by matching against the whole file, so the parser-body containment below
    does not depend on how the file ends its lines.
    """
    rows = []
    defaults = {(row["file"], row["line"]) for row in _nameless_frame_defaults()}
    relay_text = RELAY_PATH.read_text(encoding="utf-8")
    client_text = CLIENT_PATH.read_text(encoding="utf-8")
    relay, relay_at = _parser_body(relay_text, r"\bvoid\s+readFrames\s*\(", "SseRelayService.readFrames")
    client, client_at = _parser_body(client_text, r"\bfunction\s+parseFrame\s*\(", "parseFrame")
    bodies = {RELAY_PATH: (relay_at, relay_at + len(relay)),
              CLIENT_PATH: (client_at, client_at + len(client))}
    sources = [(path, path.read_text(encoding="utf-8"))
               for path in sorted(list(JAVA_ROOT.rglob("*.java"))
                                  + list(ROOT_FRONTEND.rglob("*.ts"))
                                  + list(ROOT_FRONTEND.rglob("*.tsx")))]
    for path, text in sources:
        lines = text.splitlines()
        span = bodies.get(path)
        for match in NAMELESS_TOKEN.finditer(text):
            number = text.count("\n", 0, match.start()) + 1
            line = lines[number - 1]
            inside = span is not None and span[0] <= match.start() < span[1]
            if inside and (path.name, number) in defaults:
                role = "frame-default"
            elif inside and "return null" in line:
                role = "frame-exit"
            elif inside:
                role = "unclassified"
            elif ".test." in path.name:
                role = "test-assertion"
            elif line.strip().startswith("|") or re.search(r'\|\s*"message"', line):
                role = "type-union-member"
            else:
                role = "unclassified"
            head, names = _union_block(lines, number - 1) if role == "type-union-member" else ("", set())
            rows.append({"file": path.name, "line": number, "role": role,
                         "head": head, "union": sorted(names), "text": line.strip()[:150]})
    return rows


def _if_condition(line: str) -> str | None:
    """The condition text of an `if (…) {` written on one line, or None when the line is not one.

    Read by position rather than by searching the parser body for `data.length`: the claim is about the
    guard attached to a specific `onFrame` call, and the line above that call is where that guard is.
    """
    stripped = line.strip()
    match = re.match(r"(?:\} else )?if\s*\(", stripped)
    if match is None or not stripped.endswith("{"):
        return None
    return _balanced(stripped, match.end() - 1, "(", ")")[1:-1].strip()


def test_both_frame_parsers_default_a_nameless_frame_to_the_same_event_name():
    """The relay and the browser invent the same name for a frame the wire left unnamed -- and only the
    parsers' own bodies are allowed to say so.

    `SseRelayService.readFrames` re-sends `eventName == null ? "message"` twice (once for a frame ended
    by a blank line, once for the stream's tail), and the browser's `parseFrame` opens with
    `let event = "message"` before it ever sees an `event:` line. Those two defaults are the same
    decision made in two languages, and #181 pinned only the Java half.

    The rest of this test is the belt on that claim: `"message"` in a value position is not a frame name,
    so the census says what each of its 16 occurrences *is* -- 3 defaults, the parser's own empty-frame
    exit, 9 vitest fixtures, and 3 type-union members, two of which are the trace step kinds
    (`step_start … handoff | message | final`) that share the spelling and nothing else.
    """
    rows = _nameless_frame_defaults()
    assert sorted({row["default"] for row in rows}) == ["message"], \
        (f"{[(r['file'], r['default']) for r in rows]}: both parsers must hand a nameless frame the same "
         "name -- the relay forwards to the browser, so a default that differs on one side is a frame "
         "that reaches the client as an event its router has never heard of")
    assert [(row["file"], row["line"], row["language"], row["default"]) for row in rows] == [
        ("SseRelayService.java", 109, "java", "message"),
        ("SseRelayService.java", 129, "java", "message"),
        ("use-sse.ts", 250, "ts", "message"),
    ], ("where each parser invents the name: the Java pair is the in-stream frame and the stream's tail, "
        "and losing either half means one of the two exit paths stops defaulting")
    assert [row["guard"] for row in rows] == ["eventName", "eventName", None], \
        (f"{[row['guard'] for row in rows]}: the Java default is tested against the parsed `eventName` and "
         "the browser's is an unguarded initializer -- the shapes differ on purpose (the relay keeps "
         "`null` until the frame ends, the client keeps the spec's default) and an edit that makes them "
         "the same would hide which side stopped defaulting")
    assert all(row["enclosing"] in ("readFrames", "parseFrame") for row in rows), \
        "every default site is inside one of the two frame parsers, which is what keeps a `" \
        "kind: … | \"message\"` type union out of this census by position rather than by name"

    census = _message_token_census()
    by_role: dict[str, list[dict]] = {}
    for row in census:
        by_role.setdefault(row["role"], []).append(row)
    assert len(census) == 16, \
        (f"{sorted(by_role)} counts {[(r, len(v)) for r, v in by_role.items()]}: the floor comes from the "
         "same walk as the roles below, so a narrowed scan cannot make the ledger tidy by reading nothing")
    assert sorted(by_role) == ["frame-default", "frame-exit", "test-assertion", "type-union-member"], \
        (f"{sorted(by_role)}: every occurrence of the token is accounted for by one of these four roles -- "
         "an `unclassified` row is a new vocabulary that this gate has not been told about, and a census "
         "that silently files it under a default would report on the wrong system")
    assert [(row["file"], row["line"]) for row in by_role["frame-default"]] == \
        [(row["file"], row["line"]) for row in rows], \
        "the census's `frame-default` rows and the parser scan are the same sites, read two ways"
    assert [(row["file"], row["line"]) for row in by_role["frame-exit"]] == [("use-sse.ts", 257)], \
        (f"{[(r['file'], r['line'], r['text']) for r in by_role['frame-exit']]}: the one non-default use "
         "inside a parser is the exit that drops a frame with neither data nor an explicit name")
    assert sorted((row["file"], row["line"], row["head"]) for row in by_role["type-union-member"]) == [
        ("agent-timeline.tsx", 33, "export type TraceKind ="),
        # 1180 rather than 744 since concurrent types.ts additions above the trace-step union
        # moved its `kind:` head down. The forward bridges' own types (the growth
        # engines, the offers, the portability and ingestion payloads) joined the file
        # above it, and the union itself did not change.
        # 1212 rather than 1203 since the outreach draft's own type gained the
        # names the engine actually answers with (`subject`, `body`, the
        # evidence it cited) above the trace-step union, and the union itself
        # did not change. The `kind:` head is the union's last member, so it
        # moves by the whole length of what was added above it.
        # 1258 rather than 1212 since the growth engines' types were rewritten to
        # the engines' own key spellings (#252) -- the block above the trace-step
        # union grew by 46 lines and the union itself did not change.
        ("types.ts", 1259, "kind:"),
        ('use-sse.ts', 15, 'event: SSEEventName | "message" | "progress" | "ping";'),
    ], (f"{[(r['file'], r['line'], r['head']) for r in by_role['type-union-member']]}: three type unions "
        "spell `message`, and only one of them names a frame -- the other two are the trace step kind "
        "lists, so the head of each union is pinned with its position: the pair (`file`, `line`) says "
        "where the census found it and the head says which declaration it belongs to")
    assert [row["union"] for row in by_role["type-union-member"] if "handoff" in row["union"]] == [
        sorted(row["union"]) for row in by_role["type-union-member"] if "handoff" in row["union"]
    ] and len([row for row in by_role["type-union-member"] if "handoff" in row["union"]]) == 2, \
        ("exactly two of the three unions carry `handoff`, which is the trace-step marker: the third is "
         "the frame-name union, and the discriminator is the vocabulary around it, not the line")
    assert {row["file"] for row in by_role["test-assertion"]} == {"use-sse.test.ts"} \
        and len(by_role["test-assertion"]) == 9, \
        (f"{[(r['file'], r['line']) for r in by_role['test-assertion']]}: the fixtures that hand a parser "
         "a nameless frame are the only test-side uses -- they prove the branch runs, not that a "
         "producer sends it, which is the reachability question the next test answers")


def test_the_two_parsers_disagree_about_a_frame_that_carries_no_data():
    """Java drops a frame for having no data; the browser drops it only when it also has no name.

    The relay wraps both of its `onFrame` calls in `if (data.length() > 0)`, so a frame that ends with a
    name and no data line never reaches the browser at all. `parseFrame` exits on
    `dataLines.length === 0 && event === "message"` -- one clause, not two -- so the same frame, if it
    got there, would be delivered with an empty-string payload. The disagreement is real but idle: every
    frame the bus yields carries a `data` payload, `ping` included (`{}` is still a `data:` line), which
    is the half that keeps this a ledger instead of a defect report.
    """
    relay_text = RELAY_PATH.read_text(encoding="utf-8")
    client_text = CLIENT_PATH.read_text(encoding="utf-8")
    client, client_at = _parser_body(client_text, r"\bfunction\s+parseFrame\s*\(", "parseFrame")

    relay_lines = relay_text.splitlines()
    java_rows = [row for row in _nameless_frame_defaults() if row["language"] == "java"]
    emit_guards = [_if_condition(relay_lines[row["line"] - 2]) for row in java_rows]
    assert emit_guards == ["data.length() > 0", "data.length() > 0"], \
        (f"{emit_guards} above the relay's two `onFrame` calls "
         f"{[(r['file'], r['line']) for r in java_rows]}: both emit points are guarded on data alone -- a "
         "guard on the name as well would let an unnamed frame through, and a guard that disappeared "
         "would deliver a nameless frame the browser has to invent a name for")
    ts_exit = re.search(r"if\s*\(([^)]*)\)\s*return null;", client)
    assert ts_exit is not None, "parseFrame has no `return null` guard, so its empty-frame exit cannot be read"
    ts_clauses = [c.strip() for c in ts_exit.group(1).split("&&")]
    assert ts_clauses == ["dataLines.length === 0", 'event === "message"'], \
        (f"{ts_clauses}: the browser drops an empty frame only when the name is the one it synthesized, "
         "which is the clause the relay does not have -- and the clause compares against the default "
         "name, so this is the same `message` the first test pinned")
    assert _line_of(client_text, client_at + ts_exit.start()) == 257, \
        "the exit is the line the token census calls `frame-exit`, read the same way by both scans"
    assert len(emit_guards) == 2 and len(ts_clauses) == 2 and \
        all("==" not in g for g in emit_guards), \
        (f"{emit_guards} vs {ts_clauses}: the relay's condition is one clause about data and the "
         "browser's is two, one of them about the name -- that is the disagreement, stated as sets "
         "rather than as a sentence about the code")

    bus = TASKBUS_PATH.read_text(encoding="utf-8")
    yielded = re.findall(r'yield\s+\{([^}]*)\}', bus)
    assert all('"data"' in y for y in yielded) and len(yielded) == 2, \
        (f"{yielded}: the frames the bus emits itself are exactly two and both carry a `data` key, so "
         "today no producer can make the two guards disagree -- if a yield without data is ever added, "
         "the relay swallows it and the browser forwards it as `\"\"`")


def test_the_bus_ships_a_frame_formatter_that_the_wire_never_uses():
    """`taskbus.sse()` formats SSE text that no shipped code writes, and the real writer is a library.

    The bus carries its own `event:`/`data:` formatter, which looks like the thing the stream is made of
    -- so it reads as the place to change the wire format, and a change there would be invisible: the
    only caller in the entire Python population is an offline test, while `api/tasks.py` hands frames to
    `sse-starlette`'s `EventSourceResponse`. Both facts are measured here, along with the one that keeps
    the dead formatter harmless -- the prefixes it writes are prefixes both parsers read.

    "Entire Python population" is the part that has to be walked, not announced. `ai-service` stopped
    being the whole tree when the golden-journey wave shipped `scripts/journey_api.py` and
    `scripts/concurrency_smoke.py`; the census answered new Python outside its root with a refusal, which
    is a scope note -- it goes red when the repository grows and says nothing about whether the growth was
    read. This walk starts at the repository root, so a file added anywhere is a file the census has
    already looked at. Offline and shipped are told apart by where a file lives: thirteen helpers under
    `tests/` are not named `test_*`, and one of them calling the formatter would otherwise be charged as
    a shipped caller.
    """
    population = python_files(REPO_ROOT)
    homes = {rel_of(p).split("/")[0] for p in population}
    assert len(population) >= MIN_PY_POPULATION and homes >= {"ai-service", "scripts"}, (
        f"{len(population)} files, in {sorted(homes)}: the caller claim below is stated about the "
        "repository's Python, so the walk has to be the repository's. It reached fewer than "
        f"{MIN_PY_POPULATION} files or lost a tree the repository names, which is a pruned directory or a "
        "root resolved somewhere smaller -- either way the census would clear a population smaller than "
        "the one its own sentence describes")

    rows = _sse_call_sites()
    callers = [(rel, where) for rel, where, _ in rows]
    shipped = [(rel, where) for rel, where, offline in rows if not offline]
    assert callers == [("ai-service/tests/test_core_modules.py", "test_sse_formats_event")], \
        (f"{callers}: `sse()` is production code whose only caller is one offline test -- the wire is "
         "formatted elsewhere, so an edit here is tested but never shipped")
    assert shipped == [], \
        (f"{shipped}: a shipped caller would make the formatter real, and then its format has to be "
         "reconciled with what the parsers read instead of noted as dead")

    bus_text = TASKBUS_PATH.read_text(encoding="utf-8")
    # The return is no longer the first statement: `sse()` hardened against a
    # non-dict event (a default name and a guarded read sit above the return),
    # so the formatter is read off the function's whole body. The claim is
    # unchanged -- one return, one f-string, the two prefixes the parsers read.
    body = re.search(r"def sse\(event: dict\) -> str:\n(?:    .*\n)*", bus_text)
    formatter = re.search(r'return (f"[^"]*")', body.group(0)) if body else None
    assert formatter is not None, "`sse()` no longer returns a single f-string, so its wire prefixes " \
                                  "cannot be read and the comparison below would compare nothing"
    # The literal text between the interpolations is the format; the escape sequences are still written
    # as source (`\n`, two characters), so they are turned back into line breaks before counting fields.
    literal = "".join(re.split(r"\{[^{}]*\}", formatter.group(1))).replace("\\n", "\n")
    written = set(re.findall(r"\b(\w+):", literal))
    assert written == {"event", "data"}, \
        (f"{sorted(written)} from {literal!r}: the dead formatter writes exactly the two fields the "
         "parsers read; adding `id:` or `retry:` would make it a format the running stream does not have")
    relay_text = RELAY_PATH.read_text(encoding="utf-8")
    relay, _ = _parser_body(relay_text, r"\bvoid\s+readFrames\s*\(", "SseRelayService.readFrames")
    client, _ = _parser_body(CLIENT_PATH.read_text(encoding="utf-8"),
                             r"\bfunction\s+parseFrame\s*\(", "parseFrame")
    java_reads = set(re.findall(r'startsWith\("(\w+):"\)', relay))
    ts_reads = set(re.findall(r'startsWith\("(\w+):"\)', client))
    assert java_reads == ts_reads == {"event", "data"}, \
        (f"relay {sorted(java_reads)} / client {sorted(ts_reads)}: both parsers read the two prefixes "
         "the formatter writes -- `:` (the comment line the keep-alive uses) is skipped by name, not "
         "read as a field, so the formatter and the parsers still describe one wire")
    assert _event_source_writers() == ["ai-service/app/api/tasks.py"], \
        (f"{_event_source_writers()}: the live writer is sse-starlette's response, in exactly one shipped "
         "module of the whole Python population -- that is what formats the stream the relay parses, and "
         "it is why `sse()` can be dead without the stream being unformatted")


def test_the_offline_half_of_the_python_population_is_the_half_the_service_never_loads():
    """The line the caller census draws between suite and service is the deployment's own, measured.

    `is_offline()` keys on a `tests` path segment. Two facts make that a load-bearing rule instead of a
    style preference: thirteen files under `ai-service/tests/` carry no `test_` name, so the segment rule
    and the name rule are different sets and a call moved into one of them is charged differently by each
    -- and no shipped module imports out of the tests tree, so the segment rule is the reach rule. A
    census that drew the line by name would report a shipped caller for `_repo_walk.py`.
    """
    population = [rel_of(p) for p in python_files(REPO_ROOT)]
    offline = [rel for rel in population if is_offline(rel)]
    by_name = {rel for rel in population if rel.split("/")[-1].startswith("test_")}

    helpers = sorted(set(offline) - by_name)
    assert len(helpers) >= 1 and "ai-service/tests/_repo_walk.py" in helpers, (
        f"{len(helpers)} files sit under a `tests` directory without a `test_` name: the segment rule "
        "is only worth drawing if it covers ground the name rule does not, and `helpers` empty would "
        "mean this file is asserting about two spellings of the same set")
    assert set(offline) - by_name and by_name <= set(offline), (
        f"{len(offline)} files sit in a `tests` directory, {len(by_name)} carry a `test_` name and "
        f"{sorted(by_name - set(offline))[:3]} of those sit outside one: the two rules disagree in the "
        "direction this census needs (a suite helper the name rule does not excuse) and must agree in the "
        "other (nothing named like a test is shipped code)")
    assert {rel.split("/")[0] for rel in offline} == {"ai-service"}, (
        f"{sorted({rel.split('/')[0] for rel in offline})}: the offline half is supposed to be the tree "
        "the service does not load -- a `tests` directory in another tree is a directory this census "
        "would start excusing files in, and the reach of a suite directory outside `ai-service` is not "
        "a fact this file has ever measured")

    importers = []
    for rel in population:
        if is_offline(rel):
            continue
        text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        if re.search(r"^[ \t]*(?:from|import)[ \t]+\.?(?:\w+[.])?tests\b", text, re.M):
            importers.append(rel)
    assert importers == [], (
        f"{importers}: a shipped module reaches into the tests tree, so `is_offline()` no longer "
        "describes what the running service loads and the caller census would be excusing a file that "
        "can be executed in production")

# =====================================================================================
# #185 -- every stream request is armed with `Accept`; is the answer ever asked what it is?
# =====================================================================================

API_CLIENT_PATH = ROOT_FRONTEND / "lib" / "api" / "client.ts"
TASK_STREAM_PATH = ROOT_FRONTEND / "components" / "ai" / "task-stream.tsx"
TASKS_ENDPOINT_PATH = AI_SERVICE_ROOT / "app" / "api" / "tasks.py"
STREAM_MEDIA = "text/event-stream"
MEDIA_LITERAL = re.compile(r"text/event-stream")
JAVA_ANSWER_DECLARATION = re.compile(r"produces\s*=\s*MediaType\.(TEXT_EVENT_STREAM_VALUE)")
JAVA_REQUEST_SENDER = re.compile(r"\.contentType\(\s*MediaType\.(\w+)")
REQUEST_HEADER_READ = re.compile(r'getHeader\(\s*"([^"]+)"\s*\)')
ANSWER_STATUS = re.compile(r"statusCode\(\)\s*!=\s*\d+|!\s*res\.ok|!\s*(?:stream|res\.body)\b")
TERMINAL_CODE = re.compile(r'new ApiError\("([A-Z_]+)"')
STATUS_FALLBACK = re.compile(r'\(((?:res\.)?status === 404 \? "NOT_FOUND" : "HTTP_ERROR")\)')
DONE_BREAK = re.compile(r"\bif\s*\(\s*done\s*\)\s*break\s*;")
# Every way a reader could ask "what media type is this?", spelled as each language writes it.
ANSWER_READ = re.compile(
    r"\.getContentType\s*\("
    r"|\.headers\.get\(\s*[\"'][Cc]ontent-[Tt]ype"
    r"|\.headers\(\)\.firstValue\(\s*[\"'][Cc]ontent-[Tt]ype"
    r"|getHeader\(\s*[\"'][Cc]ontent-[Tt]ype"
    r"|MediaType\.(?:parseMediaType|valueOf|includes|isCompatibleWith)\s*\("
    r"|contentType\s*(?:===?|!==?)"
    r"|\bcontent_type\s*(?:==|!=|\bin\b|\.startswith)"
    r"|[\"'][Mm]ime_?type[\"']")
# Which bag the media type was taken out of: an HTTP answer's headers, or a value the code already holds.
HTTP_HEADER_BAG = re.compile(r"\bheaders\b")
STORED_VALUE_READ = re.compile(r"\.get(?:MediaType|ContentType|MimeType)\s*\(\)|\.mediaType\s*\(\)")
CONTENT_TYPE_TOKEN = re.compile(r'[\"\'][Cc]ontent-[Tt]ype[\"\']')
CONSUMERS = (
    ("SseRelayService.consume", "java", RELAY_PATH, r"\bvoid\s+consume\s*\("),
    ("postSSE", "ts", API_CLIENT_PATH, r"\basync function postSSE\s*(?:<[^<>]*>)?\("),
    ("useSSE", "ts", CLIENT_PATH, r"\bfunction useSSE\s*\("),
)
TASK_STREAM_FIELDS = ("connection", "running", "reporting", "finished")


def _media_rel(path: Path) -> str:
    return str(path.relative_to(AI_SERVICE_ROOT.parent)).replace("\\", "/")


def _stream_media_sites() -> list[dict]:
    """Every shipped line that writes the stream media type down, classified by the line's shape.

    Three planes arm a stream request and each spells the header its own way -- `finalHeaders.set(
    "Accept", ...)` in the browser client, a plain `{ Accept: ... }` object in the hook, `.header(
    "Accept", ...)` in the relay -- while Spring declares the answer with `MediaType.TEXT_EVENT_STREAM_VALUE`
    and ai-service declares it by returning sse-starlette's response class. Two of those spellings are
    invisible to a scan for the literal, which is why each gets its own walk below.
    """
    rows = []
    for label, path, text in _walk_shipped_code():
        for match in MEDIA_LITERAL.finditer(text):
            number = _line_of(text, match.start())
            line = text.splitlines()[number - 1]
            if ".test." in path.name or path.name.startswith("test_"):
                kind = "test-assertion"
            elif re.search(r'\.(?:set|header)\(\s*"Accept"|\bAccept\s*:', line):
                kind = "request-header"
            elif re.match(r"\s*(//|\*|#)", line):
                kind = "comment"
            else:
                kind = "unclassified"
            rows.append({"file": _media_rel(path), "plane": label, "line": number, "kind": kind,
                         "text": line.strip()[:150]})
    return rows


def _java_answer_declarations() -> list[dict]:
    rows = []
    for path in sorted(JAVA_ROOT.rglob("*.java")):
        text = path.read_text(encoding="utf-8")
        for match in JAVA_ANSWER_DECLARATION.finditer(text):
            number = _line_of(text, match.start())
            line = text.splitlines()[number - 1]
            verb = re.search(r'@(Get|Post)Mapping\(\s*value\s*=\s*"([^"]+)"', line)
            rows.append({"file": path.name, "line": number,
                         "verb": verb.group(1) if verb else None,
                         "route": verb.group(2) if verb else None})
    return rows


def _java_media_writers() -> list[dict]:
    """Every media type Java names on a wire it controls -- proof the answer check below is a choice."""
    rows = []
    for path in sorted(JAVA_ROOT.rglob("*.java")):
        text = path.read_text(encoding="utf-8")
        for match in JAVA_REQUEST_SENDER.finditer(text):
            rows.append({"file": path.name, "line": _line_of(text, match.start()),
                         "media": match.group(1)})
    return rows


def _answer_type_reads() -> dict[str, list[dict]]:
    """Media-type reads, split by where the value came from -- the answer's headers, or the code's own."""
    buckets: dict[str, list[dict]] = {}
    for _label, path, text in _walk_shipped_code():
        for match in ANSWER_READ.finditer(text):
            number = _line_of(text, match.start())
            line = text.splitlines()[number - 1]
            context = text[match.start():match.start() + 80]
            if ".test." in path.name or path.name.startswith("test_"):
                kind = "test-assertion"
            elif HTTP_HEADER_BAG.search(line):
                kind = "http-answer-headers"
            elif STORED_VALUE_READ.search(context):
                kind = "stored-value"
            else:
                kind = "unclassified"
            buckets.setdefault(kind, []).append(
                {"file": _media_rel(path), "line": number, "spelling": match.group(0).strip(),
                 "text": line.strip()[:150]})
    return buckets


def _content_type_tokens() -> list[dict]:
    """Every `"Content-Type"` written in shipped code, classified by what the line does with it."""
    rows = []
    for _label, path, text in _walk_shipped_code():
        for match in CONTENT_TYPE_TOKEN.finditer(text):
            number = _line_of(text, match.start())
            line = text.splitlines()[number - 1]
            if ".test." in path.name or path.name.startswith("test_"):
                kind = "test-assertion"
            elif "setAllowedHeaders" in line:
                kind = "cors-allowlist"
            elif re.search(r'\.(?:set|header|put)\(\s*[\"\'][Cc]ontent-[Tt]ype', line) \
                    or re.search(r'[\"\'][Cc]ontent-[Tt]ype[\"\']\s*:\s*[\"\']', line):
                kind = "request-sender"
            else:
                kind = "unclassified"
            rows.append({"file": _media_rel(path), "line": number, "kind": kind,
                         "text": line.strip()[:150]})
    return rows


def _request_header_reads() -> list[dict]:
    """Which header names Java reads off a request -- a second floor under the absence below."""
    rows = []
    for _label, path, text in _walk_shipped_code():
        for match in REQUEST_HEADER_READ.finditer(text):
            rows.append({"file": _media_rel(path), "line": _line_of(text, match.start()),
                         "header": match.group(1)})
    return rows


def _stream_consumers() -> dict[str, dict]:
    """Each reader of a stream answer: its body and the guard that accepts the answer.

    The frame-read loop exit (`if (done) break;`) is required of the two JavaScript readers and forbidden
    of the relay: Java's loop lives in `readFrames`, whose exit `while ((line = reader.readLine()) != null)`
    #184 already reads, so a `consume` that grew its own break would mean two loops deciding one stream.
    """
    out = {}
    for label, language, path, header in CONSUMERS:
        text = path.read_text(encoding="utf-8")
        body, at = _parser_body(text, header, label)
        breaks = [m.start() for m in DONE_BREAK.finditer(body)]
        expected = 0 if language == "java" else 1
        if len(breaks) != expected:
            raise AssertionError(f"{len(breaks)} `if (done) break;` exits in {label}, expected {expected}: "
                                 "the loop tail is where a stream that never got a terminal frame gets "
                                 "decided, so the gate cannot say which tail it is reading")
        lines = text.splitlines()
        guard = None
        for match in ANSWER_STATUS.finditer(body):
            number = _line_of(text, at + match.start())
            condition = _if_condition(lines[number - 1])
            if condition is not None:
                guard = {"file": _media_rel(path), "line": number, "condition": condition}
                break
        out[label] = {"language": language, "file": _media_rel(path), "text": text, "lines": lines,
                      "body": body, "at": at, "break": breaks[0] if breaks else None, "guard": guard}
    return out


def _masked_strings(text: str) -> str:
    """The source with every string literal's contents blanked out.

    A field name inside a string is not a read of that field: a translation
    key like `activity.detail.finished` is a word the browser shows, not the
    run panel's `finished` flag being consulted. The mask keeps every
    character offset and every newline, so a match's line number still points
    at the line it came from.
    """
    out = list(text)
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'`":
            quote = ch
            i += 1
            while i < n:
                if text[i] == "\\":
                    # The escape and the character it escapes are both content.
                    out[i] = " "
                    if i + 1 < n:
                        out[i + 1] = " "
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                if text[i] != "\n":
                    out[i] = " "
                i += 1
            continue
        i += 1
    return "".join(out)


def _task_stream_field_reads() -> dict[str, list[dict]]:
    """Where each field of the run panel's returned object is read, production and tests apart."""
    out = {field: [] for field in TASK_STREAM_FIELDS}
    for path in sorted(list(ROOT_FRONTEND.rglob("*.ts")) + list(ROOT_FRONTEND.rglob("*.tsx"))):
        text = path.read_text(encoding="utf-8", errors="replace")
        masked = _masked_strings(text)
        for field in TASK_STREAM_FIELDS:
            for match in re.finditer(rf"\.{field}\b", masked):
                number = _line_of(text, match.start())
                out[field].append({"file": _media_rel(path), "line": number,
                                   "test": ".test." in path.name,
                                   "text": text.splitlines()[number - 1].strip()[:140]})
    return out


def test_the_stream_media_type_is_written_in_four_spellings_and_read_in_none():
    sites = _stream_media_sites()
    by_kind: dict[str, list[dict]] = {}
    for row in sites:
        by_kind.setdefault(row["kind"], []).append(row)
    assert sorted(by_kind) == ["comment", "request-header", "test-assertion"], \
        (f"{sorted(by_kind)}: the literal `text/event-stream` is written by request senders, named by one "
         "doc comment, and asserted by one test; a row that is none of those is a fifth spelling this "
         "census would have no classification for")
    senders = by_kind["request-header"]
    # 322 rather than 237 since the XHR upload transport and the shared envelopeError helper
    # joined client.ts above postSSE, moving its Accept line down.
    assert [(row["file"], row["line"]) for row in senders] == [
        ("backend/src/main/java/com/careeros/ai/SseRelayService.java", 71),
        ("frontend/src/lib/api/client.ts", 322),
        ("frontend/src/lib/sse/use-sse.ts", 92)], \
        (f"{[(r['file'], r['line']) for r in senders]}: three senders arm the stream -- the relay, the "
         "one-shot copilot client and the run panel's hook -- each in its own language's shape, so a "
         "fourth sender or a vanished one changes who can receive a stream at all")
    assert all(STREAM_MEDIA in row["text"] and "Accept" in row["text"] for row in senders), \
        (f"{[r['text'] for r in senders]}: a row stays a sender only while its line puts that media type "
         "under `Accept`; otherwise the census is counting a mention")

    declared = _java_answer_declarations()
    assert [(row["verb"], row["route"]) for row in declared] == [
        ("Get", "/stream/{taskId}"), ("Post", "/chat/stream")], \
        (f"{[(r['verb'], r['route']) for r in declared]}: Spring declares exactly these two answers as "
         "streams, each on the annotation line that names its route -- a `produces` written somewhere else "
         "would be read here as a route it is not")
    assert [row for row in sites if row["plane"] == "ai-service/app"] == [], \
        ("ai-service writes no stream media type at all: it returns sse-starlette's response and the "
         "library spells the header. The service cannot be reconciled with these declarations by comparing "
         "text, only by naming its writer -- the count below is what makes that 0 a delegate, not a gap")
    assert len(re.findall(r"EventSourceResponse\s*\(",
                          TASKS_ENDPOINT_PATH.read_text(encoding="utf-8"))) == 1, \
        "the answer-side spelling in Python is that one writer call"

    buckets = _answer_type_reads()
    assert sorted(buckets) == ["stored-value", "test-assertion"], \
        (f"{ {k: len(v) for k, v in buckets.items()} }: a media type is read out of a value the code "
         "itself stores once, and out of an HTTP answer's headers only inside a test -- those are the two "
         "buckets this census can hold. An `unclassified` row would be a read it cannot say anything about")
    assert buckets.get("http-answer-headers", []) == [], \
        (f"{buckets.get('http-answer-headers', [])}: no shipped reader asks an answer what its media type "
         "is -- that is this unit's fact. A row here means the check exists and the status guards in the "
         "third case are no longer the whole story")
    stored = buckets["stored-value"]
    assert len(stored) == 2 and all("parseMediaType" in row["text"] for row in stored), \
        (f"{stored}: the codebase's non-test media-type reads take the type out of a stored record -- "
         "the document row behind the internal download, the answer record behind the resume download -- "
         "never out of an answer the platform is reading a stream from")
    assert len(buckets["test-assertion"]) == 1 and buckets["test-assertion"][0]["spelling"] == \
        '.headers.get("Content-Type', \
        (f"{buckets['test-assertion']}: the one test read asks a captured REQUEST what it sent, which is "
         "a sender check wearing reader syntax")

    kinds: dict[str, int] = {}
    for row in _content_type_tokens():
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
    # Six request-senders rather than five: the anthropic provider joined and names the
    # header lowercase (`"content-type"`), which is the same header in another spelling.
    assert kinds == {"request-sender": 6, "cors-allowlist": 1, "test-assertion": 1}, \
        (f"{kinds}: `Content-Type` is sent six times, allowed by CORS once, and asserted in a test once. "
         "This is the population the absence above is drawn from -- an `unclassified` row would be a use "
         "nobody has read")
    # Two rows in `HttpAiServiceClient.java` rather than one: the `post` helper and the `patch`
    # helper it gained with the memory-correction surface each name APPLICATION_JSON on the
    # JSON they send.
    assert [(row["file"], row["media"]) for row in _java_media_writers()] == [
        ("HttpAiServiceClient.java", "APPLICATION_JSON"),
        ("HttpAiServiceClient.java", "APPLICATION_JSON"),
        ("InternalFileController.java", "parseMediaType"),
        ("ResumeController.java", "parseMediaType"),
    ], (f"{_java_media_writers()}: Java names a media type on the JSON it sends and on the two files it "
        "serves (the internal download and the resume download), so the missing answer check is a choice "
        "at the read site, not a tool the language lacks")
    assert sorted({row["header"] for row in _request_header_reads()}) == \
        ["Authorization", "X-Forwarded-For", "X-Internal-Token"], \
        (f"{sorted({r['header'] for r in _request_header_reads()})}: Java does read request headers by "
         "name, and none of them is a media type -- a second floor proving the reader scan is not simply "
         "blind to header reads")


def test_the_two_browser_consumers_of_a_quietly_closed_stream_disagree():
    consumers = _stream_consumers()
    post, hook = consumers["postSSE"], consumers["useSSE"]

    codes = [(m.group(1), post["at"] + m.start()) for m in TERMINAL_CODE.finditer(post["body"])]
    assert [code for code, _ in codes] == ["UNAUTHORIZED", "STREAM_ERROR", "STREAM_ENDED"], \
        (f"{[c for c, _ in codes]}: postSSE puts three error codes on the wire, in the order the failures "
         "can be reached -- session, frame, tail. A fourth would be one no caller branches on yet")
    brk = post["at"] + post["break"]
    assert codes[0][1] < codes[1][1] < brk < codes[2][1], \
        (f"{[(c, _line_of(post['text'], o)) for c, o in codes]} against the loop exit at line "
         f"{_line_of(post['text'], brk)}: the error frame's code is wired before the read starts while "
         "STREAM_ENDED can only be decided after it ends -- if that order flips, the terminal a stream "
         "reaches by closing quietly comes from a different path than the one that reads it")
    assert re.search(r'new ApiError\("STREAM_ENDED",\s*"([^"]+)"', post["body"]) is not None, \
        "postSSE's quiet close has to name itself; the sentence is the only part of it a user can see"

    assert TERMINAL_CODE.findall(hook["body"]) == [], \
        (f"{TERMINAL_CODE.findall(hook['body'])}: the hook that feeds the run panel builds no ApiError, so "
         "it has no code for a stream that ends without a terminal frame -- the difference the two "
         "readers' tails make concrete")
    closed = re.search(r'setState\(\(s\)\s*=>\s*\(s === "open" \? "closed" : s\)\)', hook["body"])
    assert closed is not None, \
        "the hook's own tail must be the state change this case compares against STREAM_ENDED; without it " \
        "the disagreement would be my inference rather than the code's"
    assert hook["break"] < closed.start(), \
        (f"loop exit at {hook['break']}, closed-state at {closed.start()}: `closed` is what the hook "
         "reports for a stream that never said `done`, so it must sit after the read loop")
    transport = hook["body"].find("onTransportError?.(", hook["break"])
    assert transport > closed.start(), \
        (f"first `onTransportError?.(` after the loop at {transport}, closed-state at {closed.start()}: a "
         "clean close reaches the state change before any transport hook, which is why nothing is told "
         "that the stream stopped")

    panel = TASK_STREAM_PATH.read_text(encoding="utf-8")
    anchor = panel.index("connection: state")
    returned = _balanced(panel, panel.index("{", panel.rindex("return {", 0, anchor)), "{", "}")
    running = re.search(r"running: ([^,\n]+),", returned)
    assert running is not None and "state" not in running.group(1) \
        and "connection" not in running.group(1), \
        (f"{running.group(1) if running else None}: `running` is derived from the answer's own flags and "
         "not from the connection, which is why a closed stream can still look like a run in progress")

    fields = _task_stream_field_reads()
    reads = {field: [row for row in rows if not row["test"]] for field, rows in fields.items()}
    assert reads["connection"] == [], \
        (f"{reads['connection']}: `connection` is produced and never read, so the only signal that a "
         "stream stopped is seen by nothing; a row here would mean the panel does answer a closed "
         "connection")
    assert reads["running"] == [], f"{reads['running']}: `running` is likewise produced and never read"
    assert sorted({row["file"] for row in reads["reporting"]}) == \
        ["frontend/src/components/ai/task-stream.tsx"] \
        and len(reads["reporting"]) == 2 and len(reads["finished"]) == 1 \
        and all("!stream." in row["text"] for row in reads["reporting"] + reads["finished"]), \
        (f"{ {k: len(v) for k, v in reads.items()} }: the two fields the panel does read are exactly the "
         "negated pair that holds the promise line on screen -- this floor proves the scan can see this "
         "object's fields at all, so the 0 rows above are a finding rather than a blind scanner")
    assert re.search(r"The run stream hasn(?:&apos;|['’])t reported progress yet", panel) is not None, \
        ("that sentence is shown while `reporting` and `finished` are both false, which is the state a "
         "quietly closed stream leaves the panel in")


def test_a_stream_answer_is_judged_by_status_and_body_and_never_by_its_media_type():
    consumers = _stream_consumers()
    guards = {name: (row["guard"] or {}) for name, row in consumers.items()}
    assert [(name, guards[name].get("condition")) for name in sorted(guards)] == [
        ("SseRelayService.consume", "response.statusCode() != 200"),
        ("postSSE", "!res.ok || !stream"),
        ("useSSE", "!res.ok || !res.body")], \
        (f"{ {k: v.get('condition') for k, v in guards.items()} }: three readers, three spellings of the "
         "same question -- is the status fine, is there a body. A missing condition would be a consumer "
         "whose answer check this walk can no longer read")
    assert not [name for name, row in guards.items()
                if "content" in row.get("condition", "").lower()
                or STREAM_MEDIA in row.get("condition", "")], \
        (f"{sorted(guards)}: none of the three guards mentions a media type, which is the whole claim -- "
         "an answer is accepted as a stream on the strength of its status code alone")

    relay = consumers["SseRelayService.consume"]
    upstream = re.search(r'onFrame\(\s*"error"\s*,\s*"([^"]*)"\s*\+\s*\w+\.\w+\(\)\s*\)', relay["body"])
    assert upstream is not None and upstream.group(1) == "upstream status ", \
        (f"{upstream.group(1) if upstream else None}: the relay turns a non-200 answer into an `error` "
         "frame that quotes the status number only, so a browser reading that frame cannot tell a refused "
         "connection from a wrong-shaped answer")
    pump_text = RELAY_PATH.read_text(encoding="utf-8")
    pump, _ = _parser_body(pump_text, r"\bprivate void pump\s*\(", "SseRelayService.pump")
    assert re.search(r"\bemitter\.complete\(\);", pump) is not None \
        and TERMINAL_CODE.findall(pump) == [] and '"error"' not in pump[pump.index("emitter.complete"):], \
        (f"{pump.strip()[:200]}: after `consume` returns -- which is what happens when the upstream closes "
         "without a terminal frame -- the relay completes the emitter normally and synthesizes no error "
         "frame, so the browser's `closed` is what a truncated run looks like from the server side too")

    post, hook = consumers["postSSE"], consumers["useSSE"]
    client_text = API_CLIENT_PATH.read_text(encoding="utf-8")
    helper_body = _function_body(client_text, "envelopeError")
    request_body = _function_body(client_text, "request")
    # One written decision, not a copy per path: the fallback lives in `envelopeError`, and both
    # the envelope path and the stream path call it. A second written copy would report the same
    # 404 differently the day one of the two is edited -- which is the drift this census exists
    # to catch; routing both paths through one helper removes it, so the census now checks that
    # no written copy survives anywhere but the helper.
    written = len(STATUS_FALLBACK.findall(helper_body))
    still_written = len(STATUS_FALLBACK.findall(request_body)) + len(STATUS_FALLBACK.findall(post["body"]))
    assert written == 1 and still_written == 0, \
        (f"{written} written in envelopeError, {still_written} still written in request or postSSE: the "
         "404-or-HTTP_ERROR fallback is ONE written decision in the helper every transport calls")
    consults = {name: len(re.findall(r"\benvelopeError\s*\(", body))
                for name, body in (("request", request_body), ("postSSE", post["body"]),
                                   ("useSSE", hook["text"]))}
    assert consults == {"request": 1, "postSSE": 1, "useSSE": 0}, \
        (f"{consults}: the envelope path and the stream path each consult the one helper exactly once, "
         "and the hook -- which answers a refused stream with a plain Error -- consults it not at all")
    post_json = len(re.findall(r"await res\.json\(\)", post["body"]))
    hook_json = len(re.findall(r"await res\.json\(\)", hook["body"]))
    assert (post_json, hook_json) == (1, 0), \
        (f"{post_json} envelope decode inside postSSE's guard branch, {hook_json} in the hook: only "
         "postSSE tries to read an error envelope out of a failed stream, and it does that after having "
         "already decided the answer is a stream -- the hook reports the status number and stops there")
