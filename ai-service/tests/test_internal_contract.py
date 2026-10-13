"""The backend -> ai-service boundary is typed twice, in two languages, by hand.

`HttpAiServiceClient` builds each internal request as a `Map` of string keys, and the
endpoint declares the same body once more as a Pydantic model. Nothing connects the two
declarations, and the failure that matters is the quiet one: Pydantic ignores a property
its model never declared, so a key renamed on either side stops arriving instead of
failing -- `/internal/features/match` with a drifted `resume_version_id` answers with the
*current* version's match, which is a number, not an error.

So the client source is read as data and reconciled against the live route table: the path
has to be one ai-service actually registered, and the body keys have to be fields the
model declares.
"""

import inspect
import re
from collections import namedtuple
from pathlib import Path

from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.main import app

AI_PACKAGE = (Path(__file__).resolve().parents[2] / "backend" / "src" / "main" / "java"
              / "com" / "careeros" / "ai")
CLIENT = AI_PACKAGE / "HttpAiServiceClient.java"
RELAY = AI_PACKAGE / "SseRelayService.java"

Method = namedtuple("Method", "name params body start end")


# ------------------------------------------------------------------ reading the routes

def _routes() -> dict[tuple[str, str], APIRoute]:
    """(VERB, path with each `{param}` folded to `{}`) -> route, for /internal only."""
    out = {}
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/internal/"):
            continue
        folded = re.sub(r"\{[^}]*}", "{}", route.path)
        for verb in route.methods:
            out[(verb, folded)] = route
    return out


def _model(route: APIRoute):
    """The endpoint's request model, or None when it takes a bare dict / a non-object body."""
    for parameter in inspect.signature(route.endpoint).parameters.values():
        if isinstance(parameter.annotation, type) and issubclass(parameter.annotation, BaseModel):
            return parameter.annotation
    return None


def _fields(route: APIRoute):
    model = _model(route)
    return None if model is None else set(model.model_fields)


def _required(route: APIRoute):
    model = _model(route)
    return None if model is None else {n for n, f in model.model_fields.items()
                                       if f.is_required()}


# ------------------------------------------------------------- reading the Java client

def _top_level(text: str, separator: str, angles: bool = False) -> list[str]:
    """Split on `separator` outside strings, parens, brackets and braces.

    `angles` also nests on `<`/`>`; a Java parameter list needs it for `List<Map<String,
    Object>> turns`, and only there -- elsewhere these characters are comparisons.
    """
    parts, depth, quote, current = [], 0, False, ""
    for ch in text:
        if ch == '"':
            quote = not quote
        elif not quote:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif angles and ch == "<":
                depth += 1
            elif angles and ch == ">" and depth > 0:
                depth -= 1
            elif ch == separator and depth == 0:
                parts.append(current)
                current = ""
                continue
        current += ch
    parts.append(current)
    return [p.strip() for p in parts]


def _argument_list(text: str, open_at: int) -> tuple[str, int]:
    """What sits between the parenthesis pair opening at `open_at`, and the index after it."""
    assert text[open_at] == "(", f"no parenthesis at index {open_at} of {text[open_at-20:open_at+20]}"
    depth, quote, current = 1, False, ""
    for i in range(open_at + 1, len(text)):
        ch = text[i]
        if ch == '"':
            quote = not quote
        elif quote:
            if ch == "\\":
                current += text[i + 1]
                continue
        else:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return current, i + 1
        current += ch
    raise AssertionError(f"unclosed parenthesis in {text[open_at:open_at + 60]}")


def _body(src: str, open_at: int) -> tuple[str, int]:
    depth, quote, current = 0, False, ""
    for i in range(open_at, len(src)):
        ch = src[i]
        if ch == '"':
            quote = not quote
        elif quote:
            pass
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return current, i + 1
        current += ch
    raise AssertionError("unclosed method body")


def _java_methods(src: str) -> list[Method]:
    """Each `    <mods> <type> name(...) {` header, with its body spliced out by brace depth."""
    out = []
    for match in re.finditer(r"\n    (?:@\w+\n    )?(?:public |private |protected )"
                             r"(?:static )?[\w<>,.\[\]? ]+? (\w+)\(([^)]*)\) \{", src):
        body, end = _body(src, match.end() - 1)
        params = [tuple(p.rsplit(maxsplit=1)[::-1]) for p in _top_level(match.group(2), ",",
                                                                        angles=True) if p]
        out.append(Method(match.group(1), params, body, match.start(), end))
    return out


def _path_of(expr: str) -> str:
    """A Java concatenation of literals and values becomes a path with `{}` per value."""
    parts = []
    for token in _top_level(expr, "+"):
        parts.append(token[1:token.rindex('"')] if token.startswith('"') else "{}")
    path = "".join(parts)
    return path[path.index("/internal/"):] if "/internal/" in path else path


def _keys_in(body: str, methods: list[Method], bindings: dict | None = None,
             depth: int = 0) -> tuple[set[str], list[str]]:
    """Body keys one method can send: literal `put("k", ..)` / `Map.of("k", v, ..)`, plus what
    a helper it calls contributes -- `put(idKey, ..)` is answered from the caller's literal."""
    bindings = bindings or {}
    keys, unresolved = set(), []

    def classify(label: str, token: str) -> set[str]:
        """A key position is a literal, or a parameter the caller bound to a literal."""
        token = bindings.get(token, token)
        if len(token) > 1 and token.startswith('"') and token.endswith('"'):
            return {token[1:-1]}
        unresolved.append(label)
        return set()

    for match in re.finditer(r"\.put\(([^,]*),", body):
        keys |= classify(f"put({match.group(1).strip()}, ...)", match.group(1).strip())
    for match in re.finditer(r"Map\.of\(", body):
        inner, _ = _argument_list(body, match.end() - 1)
        args = _top_level(inner, ",") if inner.strip() else []
        for index, arg in enumerate(args):
            if index % 2 == 0:
                keys |= classify(f"Map.of key {arg}", arg)
    if depth == 2:
        return keys, unresolved + ["nested deeper than this reader follows"]
    for helper, helper_bindings in _helper_calls(body, methods):
        sub, sub_bad = _keys_in(helper.body, methods, helper_bindings, depth + 1)
        keys |= sub
        unresolved.extend(f"{helper.name}() {b}" for b in sub_bad)
    return keys, unresolved


TRANSPORT = ("post", "get", "exchange")


def _helper_calls(body: str, methods: list[Method]) -> list[tuple[Method, dict]]:
    """Calls in `body` to another method of this class, each paired with the literals the
    caller passed for its parameters -- that is how `withOptionalRv("job_id", ..)` names a key."""
    out = []
    for method in methods:
        if method.name in TRANSPORT:
            continue
        names = [name for name, _type in method.params]
        for match in re.finditer(r"(?<![\w.])" + re.escape(method.name) + r"\(", body):
            inner, _ = _argument_list(body, match.end() - 1)
            args = _top_level(inner, ",") if inner.strip() else []
            out.append((method, {names[i]: args[i] for i in range(min(len(names), len(args)))
                                 if args[i].startswith('"')}))
    return out


def _calls() -> list[dict]:
    """Every internal request the client can make: verb, path pattern, keys, and the method."""
    src = CLIENT.read_text(encoding="utf-8")
    methods = _java_methods(src)
    out: list[dict] = []
    unresolved: list[str] = []
    for match in re.finditer(r"return (post|get|patch)\(", src):
        method = next(m for m in methods if m.start <= match.start() < m.end)
        inner, _ = _argument_list(src, match.end() - 1)
        args = _top_level(inner, ",")
        keys, bad = _keys_in(method.body, methods)
        unresolved.extend(f"{method.name}: {b}" for b in bad)
        out.append({"verb": match.group(1).upper(), "path": _path_of(args[0]),
                    "keys": keys, "via": method.name})
    assert not unresolved, f"body shapes this reader cannot classify: {unresolved}"
    return out


def _relay_calls() -> list[dict]:
    """The one URL the relay builds, from the same kind of expression."""
    src = RELAY.read_text(encoding="utf-8")
    out = []
    for match in re.finditer(r"URI\.create\(", src):
        inner, _ = _argument_list(src, match.end() - 1)
        out.append({"verb": "GET", "path": _path_of(inner), "keys": set(),
                    "via": "SseRelayService"})
    return out


# ---------------------------------------------------------------- the reconciliations

def test_every_internal_url_the_backend_builds_is_one_ai_service_has():
    routes = _routes()
    built = _calls()
    assert len(built) >= 13, f"the reader lost client calls: {[c['via'] for c in built]}"
    for call in built + _relay_calls():
        assert (call["verb"], call["path"]) in routes, \
            f"{call['via']} calls {call['verb']} {call['path']}, which ai-service never maps"


def test_the_reader_covers_every_file_in_the_backend_that_reaches_ai_service():
    """A new caller outside these two files must widen the corpus, not go unmeasured."""
    reaching = sorted(p.name for p in AI_PACKAGE.glob("*.java")
                      if "/internal/" in p.read_text(encoding="utf-8"))
    assert reaching == [CLIENT.name, RELAY.name], reaching


def _mapped_calls() -> list[tuple[APIRoute, dict]]:
    """Calls whose path ai-service does register, paired with that route.

    A call to an unmapped path is excluded on purpose: comparing its keys would only raise a
    KeyError, and the drift is already reported -- by the test that owns path existence.
    """
    routes = _routes()
    return [(routes[(c["verb"], c["path"])], c) for c in _calls()
            if (c["verb"], c["path"]) in routes]


def test_no_body_key_the_backend_sends_is_one_the_endpoint_model_drops():
    problems = []
    for route, call in _mapped_calls():
        fields = _fields(route)
        if fields is None:
            continue  # a schema-less dict payload has no field set to be wrong about
        phantom = sorted(call["keys"] - fields)
        if phantom:
            problems.append(f"{call['verb']} {call['path']} <- {call['via']} sends "
                            f"{phantom}, which the model ignores")
    assert problems == [], "\n".join(problems)


def test_every_field_the_endpoint_requires_is_sent():
    problems = []
    for route, call in _mapped_calls():
        required = _required(route)
        if required is None:
            continue
        missing = sorted(required - call["keys"])
        if missing:
            problems.append(f"{call['verb']} {call['path']} <- {call['via']} never sends "
                            f"{missing}, so every call 422s")
    assert problems == [], "\n".join(problems)


def test_the_extractor_reads_both_sides_for_real():
    """Positive control: without it, a reader that found no calls and no keys would leave
    every assertion above green while comparing nothing."""
    by_path = {c["path"]: c for c in _calls()}
    assert by_path["/internal/features/match"]["keys"] == {"job_id", "resume_version_id"}, \
        "a key the caller hands to a helper by name must still be read as a body key"
    assert "raw_text" in by_path["/internal/features/jd/analyze"]["keys"]
    assert by_path["/internal/interview/answer"]["keys"] == {
        "session_id", "answer", "question", "turns"}
    assert by_path["/internal/ingest/document/{}"]["keys"] == set()
    assert _relay_calls()[0]["path"] == "/internal/stream/{}"
    assert _fields(_routes()[("POST", "/internal/features/match")]) == {
        "job_id", "resume_version_id"}
    assert _required(_routes()[("POST", "/internal/features/match")]) == {"job_id"}


def test_only_the_legacy_text_ingest_still_sends_keys_to_an_untyped_body():
    """The gate can only check keys against a model, so a call that sends keys to a schema-less
    body is a hole -- and the set of holes stays declared rather than silently growing."""
    untyped = sorted({c["path"] for route, c in _mapped_calls()
                      if c["keys"] and _model(route) is None})
    assert untyped == ["/internal/ingest/text"], \
        f"a backend call now sends keys nobody checks: {untyped}"
