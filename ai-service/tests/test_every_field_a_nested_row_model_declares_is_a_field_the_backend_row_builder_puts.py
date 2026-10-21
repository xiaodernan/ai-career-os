"""Every key a nested row model declares is a key a backend row builder puts, and back.

#249 found the analysis surface answering with half its own contract. ``analytics.py`` times
each pipeline stage from ``oa_at`` / ``interview_at`` / ``final_round_at`` / ``offer_at``, and
the digest ranks stalled applications by the most recent of ``applied_at`` / ``created_at`` /
``last_seen``. ``ApplicationInput`` declared all eleven of those keys, so nothing looked broken
at the boundary -- but ``AnalysisService.toInput`` put six of them. The four stage keys sat at
``None`` forever, so ``timeInStage`` came back ``{avgDays: null, n: 0}`` on every account while
four callers (the engine, ``ResponseRateReq``, the controller's javadoc and the frontend's own
``types.ts``) promised per-stage durations. ``last_seen`` was the mirror image: the sender put
it, the model never declared it, and Pydantic drops an undeclared key silently -- so the
digest called a one-day-old application stalled for forty days.

Both halves are one sentence, and it points the same way from either side:

* a key the model **declares and no builder puts** is read as ``None`` forever -- the claim
  survives, the number is a lie;
* a key a builder **puts and the model omits** never arrives -- the sender's work is deleted
  at the boundary, with no error to notice.

The population is every field in ``app/api`` typed ``list[<Model>]`` where ``<Model>`` is a
``BaseModel`` in the same module: those are the request bodies that carry rows whose keys are
*spelled out* on the reading side. On the writing side the same keys are string literals --
``Map.put("…")`` in a service that builds the rows, or in the client that maps a typed DTO onto
them. Every one of those fields is graded here; the file keeps no exemption list, and case 1
refuses a field whose rows it cannot trace, because an ungraded pair is exactly how #249 hid.

The engine unit tests stayed green through all of this because their fixtures hand-built rows
with the keys the endpoint never receives: a fixture may not be asked what the wire carries.
This file walks the wire instead, and case 4 goes through the real parser, so "dropped at the
boundary" is a measurement rather than a belief about Pydantic.
"""

import ast
import functools
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
API = ROOT / "ai-service" / "app" / "api"
FEATURES = ROOT / "ai-service" / "app" / "features"
JAVA = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros"
CLIENT = JAVA / "ai" / "AiServiceClient.java"
HTTP_CLIENT = JAVA / "ai" / "HttpAiServiceClient.java"

# Seven nested row fields are on the surface today (the analysis trio shares one row model, so
# one builder carries three contracts; turns and memories carry two and one). A walk that
# silently lost its way back to three would still be able to pass cases 2-4, so the floor is
# here to make collapse a failure rather than a smaller gate.
MIN_GRADED_FIELDS = 6

# The row-list grammar, spelled the way the backend spells it.
ROW_LIST = "List<Map<String, Object>>"
ROW_MAP = "Map<String, Object>"

# A method declaration: modifiers, the return type on its own, then the name. The return type
# is its own group because that is what says a method produces rows (see `_methods`).
METHOD_RE = re.compile(
    r"^[ \t]*(?:(?:public|private|protected|static|final|synchronized)\s+)*"
    r"([\w<>,\[\]\.]+(?:<[\w<>,\[\]\.\s]*>)?)\s+(\w+)\(", re.M)


@functools.lru_cache(maxsize=None)
def _row_fields():
    """(module, model, field, inner model, declared keys) for every ``list[Model]`` request field."""
    out = []
    for module, table, _tree in _api_tables():
        for model, fields in table.items():
            for name, annotation in fields:
                inner = _nested_model(annotation, table)
                if inner is None:
                    continue
                out.append((module, model, name, inner, [f for f, _a in table[inner]]))
    return sorted(out)


def _nested_model(annotation: str, table: dict) -> str | None:
    """The row model behind ``list[Model]`` / ``list[Model] | None``, or None for a bare dict."""
    match = re.fullmatch(r"list\[(\w+)\](?: \| None)?", annotation)
    if match and match.group(1) in table:
        return match.group(1)
    return None


@functools.lru_cache(maxsize=None)
def _api_tables():
    """(module name, {class: [(field, annotation)]}, parsed tree) for every app/api module."""
    out = []
    for path in sorted(API.glob("*.py")):
        tree = ast.parse(read(path))
        table = {}
        for node in tree.body:
            if not (isinstance(node, ast.ClassDef)
                    and any(isinstance(b, ast.Name) and b.id == "BaseModel" for b in node.bases)):
                continue
            table[node.name] = [(st.target.id, ast.unparse(st.annotation)) for st in node.body
                                if isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name)]
        out.append((path.stem, table, tree))
    return out


@functools.lru_cache(maxsize=None)
def _routes():
    """``/internal/...`` -> the request models FastAPI will parse for that path."""
    out: dict[str, list[tuple[str, str]]] = {}
    for module, table, tree in _api_tables():
        prefixes = _router_prefixes(tree)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                path = _route_path(deco, prefixes)
                if path is None:
                    continue
                for arg in node.args.args:
                    if arg.annotation is None:
                        continue
                    name = ast.unparse(arg.annotation)
                    if name in table:
                        out.setdefault(path, []).append((module, name))
    return out


def _router_prefixes(tree: ast.Module) -> dict[str, str]:
    """router variable name -> the prefix its ``APIRouter(...)`` declares."""
    out = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name) and node.value.func.id == "APIRouter"):
            keyword = next((k for k in node.value.keywords if k.arg == "prefix"), None)
            if keyword is None or not isinstance(keyword.value, ast.Constant):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out[target.id] = keyword.value.value
    return out


def _route_path(deco: ast.expr, prefixes: dict[str, str]) -> str | None:
    """The full path a ``@<router>.post("…")`` decorator serves, or None if it is not one."""
    if not (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)
            and deco.func.attr in ("post", "put", "patch")):
        return None
    owner = deco.func.value
    if not (isinstance(owner, ast.Name) and owner.id in prefixes):
        return None
    if not (deco.args and isinstance(deco.args[0], ast.Constant)
            and isinstance(deco.args[0].value, str)):
        return None
    return prefixes[owner.id] + deco.args[0].value


# --------------------------------------------------------------------------- backend side


@functools.lru_cache(maxsize=None)
def _methods(text: str) -> dict[str, list[tuple[str, str, str | None]]]:
    """method name -> [(return type, parameter list, body or None for a declaration)].

    The return type is captured apart from the modifiers because it is the only thing that
    says a method produces rows: ``Map<String, Object>`` is one row, ``List<Map<String,
    Object>>`` is a batch, and anything else -- ``Map<UUID, Map<String, String>>``, a
    ``List<InterviewTurn>`` -- is not a row map however many keys it puts.
    """
    out: dict[str, list[tuple[str, str, str | None]]] = {}
    for match in METHOD_RE.finditer(text):
        returns, name = collapse(match.group(1)), match.group(2)
        open_at = match.end() - 1
        close = balanced(text, open_at, "(", ")")
        rest = text[close + 1:]
        if re.match(r"\s*(?:throws [\w, <>.\s]+)?\s*;", rest):
            out.setdefault(name, []).append((returns, collapse(text[open_at + 1:close]), None))
            continue
        brace = rest.find("{")
        if brace == -1:
            continue
        end = balanced(rest, brace, "{", "}")
        out.setdefault(name, []).append(
            (returns, collapse(text[open_at + 1:close]), rest[brace + 1:end]))
    return out


def _declares(text: str, kind: str, var: str) -> bool:
    """Whether `text` declares `var` with the (space-insensitive) type `kind`."""
    return re.search(re.escape(kind).replace(r"\ ", r"\s*") + r"\s+" + re.escape(var) + r"\b",
                     text) is not None


def _puts_of(text: str, var: str) -> list[str]:
    """The literal keys put on `var`, which is a map the code says is a row."""
    return re.findall(r"\b" + re.escape(var) + r"\.put\(\"(\w+)\"", text)


def _builders_for(text: str) -> dict[str, list[str]]:
    """method -> the row keys it produces, for every method this file declares.

    A method is a row builder only by its declared return type. ``List<Map<String, Object>>``
    methods delegate: their keys are the union of the builders they call or reference, plus
    the row maps they ``add`` inline. Without that rule the walk would read a counter map or
    a request body as a row and pass the contract on the wrong map.
    """
    methods = _methods(text)
    cache: dict[str, list[str]] = {}

    def keys_of(name: str, seen: frozenset) -> list[str]:
        if name in cache:
            return cache[name]
        found: list[str] = []
        for returns, _params, body in methods.get(name, []):
            if body is None or name in seen:
                continue
            one_row = ROW_MAP in returns and ROW_LIST not in returns
            for var in re.findall(r"return\s+(\w+)\s*;", body):
                if one_row and _declares(text, ROW_MAP, var):
                    found += _puts_of(body, var)
                elif ROW_LIST in returns and _declares(text, ROW_LIST, var):
                    for row_var in re.findall(
                            r"\b" + re.escape(var) + r"\.add\((\w+)\)", body):
                        if _declares(text, ROW_MAP, row_var):
                            found += _puts_of(body, row_var)
            if ROW_LIST in returns:
                referenced = (set(re.findall(r"(?<![\w.])(\w+)\s*\(", body))
                              | set(re.findall(r"::(\w+)", body)))
                for other in sorted(referenced & set(methods) - {name}):
                    found += keys_of(other, seen | {name})
        cache[name] = sorted(set(found))
        return cache[name]

    for name in methods:
        keys_of(name, frozenset())
    return cache


def _builders(text: str) -> dict[str, list[str]]:
    """`_builders_for`, memoised: the same file is walked by several carriers."""
    return _builders_cached(text)


@functools.lru_cache(maxsize=256)
def _builders_cached(text: str) -> dict[str, list[str]]:
    return _builders_for(text)


@functools.lru_cache(maxsize=None)
def _interface_rows() -> dict[str, tuple[list[str], list[str]]]:
    """client method -> (its parameter names, the names that carry a row list)."""
    out = {}
    for name, entries in _methods(read(CLIENT)).items():
        for _returns, params, body in entries:
            if body is not None:
                continue
            declared = split_top(params)
            names = [p.rsplit(" ", 1)[-1] for p in declared]
            rows = [names[i] for i, p in enumerate(declared) if ROW_LIST in p]
            if rows:
                out[name] = (names, rows)
    return out


@functools.lru_cache(maxsize=None)
def _sends() -> list[dict]:
    """One entry per ``post(path, …)`` in the client: the path, and how each body key is filled.

    Rows travel under a body key in two shapes, and both have to be read or the walk grades
    half the surface: the caller hands the client a ``List<Map<String, Object>>`` (the analysis
    trio, the interview turns, the memory import), or the client builds the row list itself out
    of a typed DTO (``compareOffers`` maps each ``OfferItem`` through ``offerBody``). A body key
    whose value is a scalar is not rows, and collecting its literal would grade a request
    field as a row.
    """
    text = read(HTTP_CLIENT)
    builders = _builders(text)
    rows_params = _interface_rows()
    out = []
    for name, entries in _methods(text).items():
        row_params = rows_params.get(name, ([], []))[1]
        for _returns, _params, body in entries:
            if body is None or not re.search(r"\bpost\(", body):
                continue
            path = re.search(r'"(/internal/[^"]+)"', body)
            if not path:
                continue
            local_lists = set(re.findall(
                r"List<\s*Map<\s*String,\s*Object\s*>\s*>\s+(\w+)", body))
            keys = {}
            for key, value in re.findall(r'"(\w+)",\s*(\w+)', body):
                if value in local_lists:
                    keys[key] = {"kind": f"the client builds {value}",
                                 "keys": _local_row_keys(text, body, value, builders),
                                 "param": None}
                elif value in row_params:
                    keys[key] = {"kind": "rows arrive from the caller", "keys": None,
                                 "param": value}
            if keys:
                out.append({"method": name, "path": path.group(1), "keys": keys})
    return out


def _local_row_keys(text: str, body: str, list_var: str, builders: dict[str, list[str]]) -> list[str]:
    """The literal keys filling a row list the client itself builds."""
    found = [k for var in re.findall(r"\b" + re.escape(list_var) + r"\.add\((\w+)\)", body)
             if _declares(text, ROW_MAP, var) for k in _puts_of(body, var)]
    for ref in set(re.findall(r"::(\w+)", body)):
        found += builders.get(ref, [])
    return sorted(set(found))


class Carrier:
    """One production call site: the file, the method, and the row keys it hands over."""

    def __init__(self, path: Path, method: str, client_method: str, param: str,
                 kind: str, keys: list[str]):
        self.file = path.name
        self.method = method
        self.client_method = client_method
        self.param = param
        self.kind = kind
        self.keys = sorted(set(keys))

    def __repr__(self):
        return f"{self.file}#{self.method} -> {self.client_method}({self.param}) [{self.kind}]"


def _receivers(text: str) -> set[str]:
    """Variable names in this file whose declared type is the ai-service client."""
    return set(re.findall(r"\bAiServiceClient\s+(\w+)", text))


def _call_sites(text: str) -> list[tuple[str, str]]:
    """(client method, enclosing method, offset) for each production call in this file."""
    rows = _interface_rows()
    receivers = _receivers(text)
    out = []
    for call in re.finditer(r"\b(\w+)\.(\w+)\s*\(", text):
        if call.group(1) not in receivers or call.group(2) not in rows:
            continue
        out.append((call.group(2), _method_around(text, call.start())))
    return out


def _rows_at(text: str, client_method: str, enclosing: str, param: str) -> tuple[str, list[str]]:
    """(how the rows were built, their literal keys) for one row argument of one call site."""
    builders = _builders(text)
    param_names = _interface_rows()[client_method][0]
    entry = next((m for m in _methods(text).get(enclosing, []) if m[2] is not None), None)
    if entry is None:
        return "no method body found here", []
    _returns, _params, body = entry
    at = body.find(f"{client_method}(")
    if at == -1:
        return "call not found in that method", []
    open_at = body.index("(", at)
    args = split_top(body[open_at + 1:balanced(body, open_at, "(", ")")])
    if len(args) != len(param_names) or param not in param_names:
        return "argument list does not line up with the interface", []
    expr = args[param_names.index(param)]
    referenced = (set(re.findall(r"(?<![\w.])(\w+)\s*\(", expr))
                  | set(re.findall(r"::(\w+)", expr))) & set(builders)
    if referenced:
        return ("row builder " + "/".join(sorted(referenced)),
                [k for b in sorted(referenced) for k in builders[b]])
    if re.fullmatch(r"\w+", expr) and _declares(text, ROW_LIST, expr):
        added = [k for var in re.findall(r"\b" + re.escape(expr) + r"\.add\((\w+)\)", body)
                 if _declares(text, ROW_MAP, var) for k in _puts_of(body, var)]
        refs = [k for r in set(re.findall(r"::(\w+)", body)) for k in builders.get(r, [])]
        if added or refs:
            return (f"row list {expr} fed by "
                    + ("adds" if added else "") + ("+" if added and refs else "")
                    + ("method references" if refs else ""), sorted(set(added + refs)))
    return "rows arrive from the caller", []


@functools.lru_cache(maxsize=None)
def _carriers() -> dict[str, list[Carrier]]:
    """client method -> every production call site that sends it rows."""
    out: dict[str, list[Carrier]] = {}
    for path in sorted(JAVA.rglob("*.java")):
        if path in (CLIENT, HTTP_CLIENT):
            continue
        text = read(path)
        if not _receivers(text):
            continue
        for client_method, enclosing in _call_sites(text):
            for param in _interface_rows()[client_method][1]:
                kind, keys = _rows_at(text, client_method, enclosing, param)
                out.setdefault(client_method, []).append(
                    Carrier(path, enclosing, client_method, param, kind, keys))
    return out


def _method_around(text: str, offset: int) -> str:
    """The declared method enclosing `offset`, so a carrier names where its rows were built."""
    best, best_at = "<top level>", -1
    for match in METHOD_RE.finditer(text):
        if match.start() <= offset and match.start() > best_at and offset - match.start() < 6000:
            best, best_at = match.group(2), match.start()
    return best


@functools.lru_cache(maxsize=None)
def graded() -> list[tuple[tuple, list[Carrier]]]:
    """Every nested row field, the route that serves it, and the carriers that fill its rows."""
    routes = _routes()
    carriers = _carriers()
    out = []
    for module, model, field, inner, declared in _row_fields():
        path = next((p for p, owners in routes.items() if (module, model) in owners), None)
        found: list[Carrier] = []
        for send in _sends():
            entry = send["keys"].get(field) if send["path"] == path else None
            if entry is None:
                continue
            if entry["keys"] is not None:
                found.append(Carrier(HTTP_CLIENT, send["method"], send["method"], field,
                                     entry["kind"], entry["keys"]))
            else:
                found += [c for c in carriers.get(send["method"], []) if c.param == entry["param"]]
        out.append(((module, model, field, inner, declared, path), found))
    return out


def unreadable() -> list[tuple]:
    """Graded rows whose builders produced no key at all, so no case below can read them.

    The gate has no exemption list. A field lands here when a client method really does send
    it rows under its own name but nothing on either side spells those rows out as literals --
    which is what happens if a builder becomes untraceable, or if a new endpoint takes rows
    straight from a browser and no backend literal describes them. Either way the answer is
    to say so in this file, in writing, with the reason; not to let the pair vanish.
    """
    return [row for row, carriers in graded()
            if not any(c.keys for c in carriers)]


def read(path: Path) -> str:
    """Shipped text with LF endings; ``git archive`` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def balanced(text: str, open_at: int, opener: str, closer: str) -> int:
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"no matching {closer!r} after offset {open_at}")


def split_top(inner: str) -> list[str]:
    parts, depth, current = [], 0, ""
    for ch in inner:
        if ch in "<([{":
            depth += 1
        elif ch in ">)]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
    parts.append(current.strip())
    return [p for p in parts if p]


# --------------------------------------------------------------------------- the engine side


def timed_stage_keys() -> dict[str, str]:
    """stage -> the row key the backend derives for it, read out of ``AnalysisService``.

    The map is a literal ``Map.of("oa", "oa_at", …)`` precisely so this can read it: a
    computed key (``stage + "_at"``) would make the pin below compare a table with itself.
    """
    text = read(JAVA / "report" / "service" / "AnalysisService.java")
    table = re.search(r"TIMED_STAGES\s*=\s*Map\.of\(([^;]*)\);", collapse(text))
    assert table, "AnalysisService no longer declares TIMED_STAGES as a Map.of literal"
    pairs = re.findall(r'"(\w+)",\s*"(\w+)"', table.group(1))
    assert pairs, f"TIMED_STAGES reads empty: {table.group(1)!r}"
    return dict(pairs)


def engine_row_keys() -> set[str]:
    """Every timestamp key ``analytics.py`` reads off a row, from its string literals.

    Docstrings are excluded: a sentence about a key is not a read of one. The suffix
    grammar (``*_at`` / ``*_seen``) is how the row spells a moment.
    """
    tree = ast.parse(read(FEATURES / "analytics.py"))
    literals: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                body = body[1:]
            for statement in body:
                for inner in ast.walk(statement):
                    if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                        literals.add(inner.value)
    return {k for k in literals if re.fullmatch(r"[a-z][a-z0-9_]*_(at|seen)", k)}


def engine_timed_stages() -> dict[str, str]:
    """stage -> the row key it is timed from, read out of the loop that times durations.

    The engine spells its stage table as a literal tuple of pairs. Reading it off the syntax
    tree is what makes case 6 a pin rather than a restatement: a stage that entered
    ``PIPELINE`` without entering this tuple is counted by the funnel and timed by nobody, and
    the two lists would still be the same length on any suffix scan.
    """
    tree = ast.parse(read(FEATURES / "analytics.py"))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Tuple)
                and len(node.target.elts) == 2):
            continue
        pairs = {}
        for element in getattr(node.iter, "elts", []):
            if (isinstance(element, ast.Tuple) and len(element.elts) == 2
                    and all(isinstance(e, ast.Constant) and isinstance(e.value, str)
                            for e in element.elts)):
                pairs[element.elts[0].value] = element.elts[1].value
        if pairs:
            return pairs
    raise AssertionError(
        "analytics.py no longer times stages from a literal (stage, key) tuple, so the "
        "spelling this case pins has moved -- re-aim it at whatever the durations loop reads")


def engine_pipeline() -> list[str]:
    """The stage order ``analytics.py`` declares, read off its own module-level list."""
    tree = ast.parse(read(FEATURES / "analytics.py"))
    for node in tree.body:
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.List)
                and any(isinstance(t, ast.Name) and t.id == "PIPELINE" for t in node.targets)):
            return [ast.unparse(element) for element in node.value.elts]
    raise AssertionError("analytics.py no longer declares PIPELINE as a list literal")


def _table(module: str) -> dict[str, list[tuple[str, str]]]:
    """{model: [(field, annotation)]} for one app/api module."""
    for name, table, _tree in _api_tables():
        if name == module:
            return table
    raise AssertionError(f"app/api/{module}.py is not part of the request surface")


def field_annotations(module: str, model: str) -> dict[str, str]:
    """field name -> its annotation as written, for one request model."""
    return dict(_table(module)[model])


def declared_fields(module: str, model: str) -> list[str]:
    """The field names a request model in `module` declares, in the order it declares them."""
    return list(field_annotations(module, model))


def model_class(module: str, name: str):
    """The live Pydantic class, so case 4 measures the boundary instead of describing it."""
    import importlib

    return getattr(importlib.import_module(f"app.api.{module}"), name)


# --------------------------------------------------------------------------- the cases


def test_the_nested_row_fields_are_a_known_population():
    """Case 1: the walk sees the whole rows-by-name surface, and reads a builder behind each field."""
    fields = _row_fields()
    assert fields, "no request model declares a list[<row model>] any more -- the walk is broken"
    labelled = {(module, model, field) for module, model, field, _i, _d in fields}
    assert len(labelled) == len(fields), f"one field counted twice: {sorted(labelled)}"

    pairs = graded()
    assert len(pairs) == len(fields), (
        f"{len(pairs)} fields walked against {len(fields)} nested row fields on the surface: "
        "a request model started or stopped declaring list[<row model>], and the two lists "
        f"disagree -- {sorted(labelled ^ {(m, mo, f) for (m, mo, f, *_r), _c in pairs})}")
    assert len(pairs) >= MIN_GRADED_FIELDS, (
        f"only {len(pairs)} nested row fields reached the client, pinned at least "
        f"{MIN_GRADED_FIELDS}: the walk collapsed rather than the contract changing")

    routes = _routes()
    for (module, model, field, inner, _declared, path), carriers in pairs:
        assert path, f"{module}.{model}.{field} is served by no route this walk can find"
        assert (module, model) in routes[path], f"{path} is not served by {model}"
        assert carriers, (
            f"nothing sends rows to {path} under the key {field!r}: the client puts them under "
            "another name, or the model renamed the field, and FastAPI then reads the rows as "
            "absent -- an empty pipeline, not an error")

    silent = unreadable()
    assert not silent, (
        f"{[(m, mo, f) for m, mo, f, *_r in silent]} are sent rows that no literal builder "
        "describes, so cases 2-4 would grade an empty key set and call it agreement: either the "
        "rows really do arrive from a browser (say so here, with the reason) or the walk lost "
        "the builder and has to be widened")


def test_every_key_a_row_model_declares_is_a_key_a_carrier_puts():
    """Case 2: nothing the reader names is a key the sender never sends."""
    for (module, model, field, inner, declared, path), carriers in graded():
        put = sorted({k for carrier in carriers for k in carrier.keys})
        missing = sorted(set(declared) - set(put))
        assert not missing, (
            f"{inner} declares {missing} for {module}.{model}.{field} ({path}) but no backend "
            f"row builder puts them ({[repr(c) for c in carriers]}): the reader sees None for "
            "those keys forever, which is how timeInStage came back empty on every account "
            "while four callers promised per-stage durations (#249)")


def test_every_key_a_carrier_puts_is_a_field_the_row_model_declares():
    """Case 3: nothing the sender puts is a key the model silently drops."""
    for (module, model, field, inner, declared, path), carriers in graded():
        for carrier in carriers:
            extra = sorted(set(carrier.keys) - set(declared))
            assert not extra, (
                f"{carrier} puts {extra} into the rows sent to {path}, which {inner} does not "
                "declare: Pydantic ignores an undeclared key without a word, so the sender's "
                "work is deleted at the boundary -- the ``last_seen`` half of #249")


def test_the_shape_a_carrier_puts_parses_into_the_model_that_reads_it():
    """Case 4: the sender's own key set is what the parser ends up holding, measured for real.

    Cases 2 and 3 compare two derivations. This one runs the boundary: it builds a row from
    the keys the carrier puts, parses it, and asks what survived. An undeclared key must be
    dropped here too, or the story this file tells about Pydantic is folklore.
    """
    import importlib
    importlib.import_module("app.api.features")  # the models import the app package as pytest runs it

    for (module, model, field, inner, declared, path), carriers in graded():
        klass = model_class(module, inner)
        put = sorted({k for carrier in carriers for k in carrier.keys})
        row = {key: _sample(module, inner, key) for key in put}
        parsed = klass(**row)
        assert sorted(parsed.model_dump()) == sorted(put), (
            f"a row built from {path}'s sender keys parsed into "
            f"{sorted(parsed.model_dump())} for {inner}: the model that reads it does not match "
            "the map that writes it")

        ghost = "a_key_nobody_declares"
        assert ghost not in declared
        dropped = klass(**{**row, ghost: 1})
        assert not hasattr(dropped, ghost), (
            f"{inner} kept an undeclared key, so case 3 no longer describes a real risk")


def _sample(module: str, inner: str, key: str):
    """A value of the type the model declares for `key`, so the parser is not tripped by kind."""
    return _for_annotation(module, field_annotations(module, inner)[key])


def _for_annotation(module: str, annotation: str):
    """A stand-in for one declared annotation, walked through nested models as the sender walks it.

    ``OfferItem.equity`` is an ``EquityGrant``, and the backend puts a nested map under it, so a
    sample that is merely "a string" would fail the parse for the wrong reason -- the case must
    trip on a key that does not line up, not on a value that does not fit.
    """
    base = annotation.split("|")[0].strip()
    if base.startswith("int"):
        return 1
    if base.startswith("float"):
        return 0.5
    if base.startswith("bool"):
        return True
    if base.startswith("dict"):
        return {}
    nested = re.fullmatch(r"list\[(\w+)\]", base)
    if nested:
        return [] if nested.group(1) == "dict" else [_for_annotation(module, nested.group(1))]
    if base in _table(module):
        return {field: _for_annotation(module, field_annotation)
                for field, field_annotation in _table(module)[base]}
    return "x"


def test_the_timestamp_keys_the_engine_reads_are_fields_the_row_model_declares():
    """Case 5: the reader's side of the same contract, walked from the engine's own literals.

    #249 was invisible from the sender because the model declared the stage keys: the drift
    was between the *reader's* literals and the *sender's*. This case reads the reader.
    """
    read_keys = engine_row_keys()
    assert read_keys, "analytics.py reads no *_at / *_seen key: the walk is broken"
    declared = set(declared_fields("features", "ApplicationInput"))
    missing = sorted(read_keys - declared)
    assert not missing, (
        f"analytics.py reads {missing} off a row that ApplicationInput does not declare, so the "
        "engine can never be handed those keys through /internal/features/* -- the sender may "
        "put them and Pydantic will drop them (#249's last_seen)")


def test_the_stages_the_backend_times_are_the_stages_the_engine_reports_durations_for():
    """Case 6: one stage table, three spellings, no fourth place to put a stage."""
    backend = timed_stage_keys()
    engine = engine_timed_stages()
    pipeline = [s.strip("'\"") for s in engine_pipeline()]
    declared = declared_fields("features", "ApplicationInput")

    assert set(engine) == set(pipeline) - {"applied"}, (
        f"the engine times {sorted(engine)} while its own pipeline is {pipeline}: a stage the "
        "funnel counts is a stage no duration ever measures")
    assert set(backend) == set(engine), (
        f"AnalysisService derives timestamps for {sorted(backend)} and the engine reads "
        f"{sorted(engine)}: whichever side is missing a stage reports the other's stage as "
        "untimed history")
    for stage, key in backend.items():
        assert key == engine[stage], (
            f"stage {stage!r}: the backend sends {key!r} where the engine reads "
            f"{engine[stage]!r}")
        assert key == f"{stage}_at", (
            f"the backend maps stage {stage!r} to {key!r}, which is not the "
            '"<stage>_at" spelling the request model declares')
    unannounced = sorted((set(backend.values()) | set(engine.values())) - set(declared))
    assert not unannounced, (
        f"the stage keys {unannounced} are sent and read but ApplicationInput does not declare "
        "them, so Pydantic drops them and timeInStage stays empty (#249)")
