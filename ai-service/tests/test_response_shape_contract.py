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
    assert len(re.findall(TS_OPENER.format(name=r"(\w+)"), source)) == 47, \
        "43 exported mappers and 4 module-private ones, all through one opener"
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
    assert len(declared) == 101, \
        f"{len(declared)} records carry a declaration the shared opener reads, not the 101 measured"
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
    `?.data` unwrap, all of them in `lib/api/client.ts`, plus 23 `toast.success` lines the exclusion has
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
    assert kinds.count("success") == 2 and kinds.count("unwrap") == 1, \
        f"{[(row['kind'], row['text']) for row in rows]}: two success checks and one unwrap is the pair"
    assert [row["text"] for row in rows if row["kind"] == "success"] == [
        'if (!res.ok || !json.success || !json.data) return null;',
        'if (!res.ok || (json && json.success === false)) {',
    ], f"{[row['text'] for row in rows if row['kind'] == 'success']}: the envelope's own guards, measured"
    assert len(toasts) == 23, (f"{len(toasts)} `toast.success` lines came out of the same walk: that is "
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
    literal call sites ARE the inventory), and `{"event": "<name>", …}` yields. Java only ever forwards
    the name it received, which the second half of the rule checks by requiring zero hard-coded names.
    """
    names: set[str] = set()
    for path in _app_root().rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        names.update(re.findall(r'publish\(\s*task_id\s*,\s*"(\w+)"', text))
        names.update(re.findall(r'_emit\(\s*task_id\s*,\s*"(\w+)"', text))
        names.update(re.findall(r'\{\s*"event":\s*"(\w+)"', text))
    return names


def _java_frame_names() -> set[str]:
    """Frame names the backend invents rather than relays -- measured zero, and that is the claim."""
    names: set[str] = set()
    for path in JAVA_ROOT.rglob("*.java"):
        names.update(re.findall(r'\.name\(\s*"(\w+)"', path.read_text(encoding="utf-8")))
    return names


def test_the_client_dispatches_two_frame_kinds_no_service_can_send():
    """#175: the frame inventory across three services, and the ledger of two cases that cannot fire.

    `use-sse.ts` routes nine event names; the services publish seven of them -- status, progress, done,
    error, token, message, ping. `artifact` and `trace` appear in no publishing call site anywhere: the
    string `"artifact"` does not occur in `ai-service/app` at all, `trace` frames are never published
    because `observability.trace()` writes to the database instead of the task bus, and the backend only
    relays (`SseRelayService.java:109`, `CopilotStreamService.java:163` forward the name they read). Yet
    `components/ai/task-stream.tsx:98` turns trace frames into timeline rows and :125 flips a reporting
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
    assert _java_frame_names() == set(), \
        ("the backend now hard-codes a frame name, so the inventory above is no longer the whole story "
         "and a name could reach the browser without appearing in it")

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


PUBLISH_CALL = re.compile(r'(?:taskbus\.)?(?:publish|_emit)\(\s*task_id\s*,\s*"(\w+)"\s*,\s*')


def _published_payload_keys() -> dict[str, set[str]]:
    """event name -> the literal payload keys published with it, braces paired, not line-grabbed.

    The payload is often written across several lines (`ingestion/pipeline.py:69`), so a `[^\n]*` grab
    would silently lose the later keys -- the mistake #171 found in the TypeScript mirror of this rule.
    A payload that is a call rather than a literal is kept as a marker, because the census must not
    report "no keys" where the truth is "keys come from elsewhere".
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
    return out


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
