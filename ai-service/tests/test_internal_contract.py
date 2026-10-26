"""The backend -> ai-service boundary is typed twice, in two languages, by hand.

`HttpAiServiceClient` builds each internal request as a `Map` of string keys, and the
endpoint declares the same body once more as a Pydantic model. Nothing connects the two
declarations, and the failure that matters is the quiet one: Pydantic ignores a property
its model never declared, so a key renamed on either side stops arriving instead of
failing -- `/internal/features/match` with a drifted `resume_version_id` answers with the
*current* version's match, which is a number, not an error.

So the client source is read as data and reconciled against the live route table: the path
has to be one ai-service actually registered, and the body keys have to be fields the
model declares. The reading has to be of *every* request site, which is a stronger claim
than it sounds: the client spells its calls three ways -- `return post("/internal/...", ..)`,
a `get(path, userId)` whose path was built on the line above, and a
`restClient.delete().uri(..)` chain that never goes through the helpers at all. The first
walk keyed on `return` saw 17 of the 19 sites, and the two it missed are live dependencies:
`GET /internal/memories` (the memory panel's list) and `DELETE /internal/memories/{id}`
(the route behind "forget this"). A call that is not walked is a call nobody checks, so the
census of `/internal/` literals in the client is reconciled against the walk, not trusted.
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

def _flat_routes() -> list:
    """Every APIRoute the app serves, flat, across fastapi generations.

    fastapi <=0.1xx flattens included routers into `app.routes` directly. 0.161+
    mounts them as `_IncludedRouter` proxies whose `original_router.routes` hold
    the real routes (prefixes applied). Two traps measured on 0.161: the included
    router's route list contains the proxy itself (self-reference -> recursion),
    and `include_in_schema=False` routers still serve. Expand with a seen-set.
    """
    out, seen = [], set()
    stack = list(app.routes)
    while stack:
        route = stack.pop(0)
        if id(route) in seen:
            continue
        seen.add(id(route))
        inner = getattr(route, "original_router", None)
        if inner is not None and inner is not route:
            stack.extend(inner.routes)
        else:
            out.append(route)
    return out


def _routes() -> dict[tuple[str, str], APIRoute]:
    """(VERB, path with each `{param}` folded to `{}`) -> route, for /internal only."""
    out = {}
    for route in _flat_routes():
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
    """A Java concatenation of literals and values becomes a path with `{}` per value.

    A conditional that opens a `?` is a query string appended to the path, not a segment of
    it: `listMemories` adds `?kinds=` only when the caller has kinds to filter by, and a
    reader that folds that into the path invents a `/internal/memories{}` no router serves.
    """
    parts = []
    for token in _top_level(expr, "+"):
        if token.startswith('"'):
            parts.append(token[1:token.rindex('"')])
        elif '"?' in token:
            break
        else:
            parts.append("{}")
    path = "".join(parts)
    return path[path.index("/internal/"):] if "/internal/" in path else path


def _statement_end(text: str, start: int) -> int:
    """Index just past the next top-level `;`, ignoring strings and brackets."""
    depth, quote = 0, False
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '"':
            quote = not quote
        elif not quote:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == ";" and depth == 0:
                return i
    raise AssertionError(f"unclosed statement from {text[start:start + 40]!r}")


def _path_expression(body: str, arg: str) -> str | None:
    """What a transport's first argument is built from, following one local binding.

    `get(path, userId)` names a variable assigned on the line above; the request is still a
    dependency on that literal path, so the binding is resolved rather than folded to `{}`.
    An identifier with no `String <name> =` in the same body answers None, which the caller
    records as unparsed -- guessing `{}` there would invent a path and check it against nothing.
    """
    arg = arg.strip()
    if not re.fullmatch(r"\w+", arg):
        return arg
    for match in re.finditer(rf"\bString {re.escape(arg)} = ", body):
        return body[match.end():_statement_end(body, match.end())]
    return None


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


TRANSPORT_VERBS = {"post": "POST", "get": "GET", "patch": "PATCH"}
# `exchange` and `translateStatus` are the machinery that carries a request, not a dependency
# on a path: a site inside them would be every site at once. `_helper_calls` skips all of them
# so a transport's own body is never mined for the caller's body keys.
TRANSPORT = tuple(TRANSPORT_VERBS) + ("exchange", "translateStatus")


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


def _call_sites(src: str, methods: list[Method]) -> tuple[list, list]:
    """(sites, unparsed) -- every request a caller makes, plus every one the reader could not type.

    Three spellings reach ai-service and a reader that follows one of them silently drops the
    others -- which is how a `get` that is not on a `return` line and a `restClient.delete()`
    chain that bypasses the helpers both went unseen while their endpoints were live.

    An unreadable chain is *recorded* rather than raised, because `_calls()` is also evaluated at
    import time for another gate's table: a raise here would take the collection of every file
    that imports this walk down with it, turning fourteen named checks into one error message.
    The census gate below is charged with refusing the list, so recording is not dropping.
    """
    sites: list[tuple[str, str, Method, str]] = []
    unparsed: list[tuple[str, str]] = []
    for method in methods:
        if method.name in TRANSPORT:
            continue
        for match in re.finditer(r"(?<![\w.])(" + "|".join(TRANSPORT_VERBS) + r")\(", method.body):
            inner, _ = _argument_list(method.body, match.end() - 1)
            expr = _path_expression(method.body, _top_level(inner, ",")[0])
            if expr is None:
                unparsed.append((method.name, "a path this reader cannot resolve to a literal"))
                continue
            sites.append((TRANSPORT_VERBS[match.group(1)], expr, method, "helper"))
        for match in re.finditer(r"restClient\.(get|post|put|patch|delete)\(\)", method.body):
            after = method.body[match.end():]
            uri = re.search(r"\.uri\(", after)
            if not uri:
                unparsed.append((method.name, f"{match.group(1)}() chain with no .uri() in reach"))
                continue
            inner, _ = _argument_list(after, uri.end() - 1)
            sites.append((match.group(1).upper(), inner, method, "chain"))
    return sites, unparsed


def _calls() -> list[dict]:
    """Every internal request the client can make: verb, path pattern, keys, and the method."""
    src = CLIENT.read_text(encoding="utf-8")
    methods = _java_methods(src)
    out: list[dict] = []
    unresolved: list[str] = []
    for verb, expr, method, _spelling in _call_sites(src, methods)[0]:
        keys, bad = _keys_in(method.body, methods)
        unresolved.extend(f"{method.name}: {b}" for b in bad)
        out.append({"verb": verb, "path": _path_of(expr), "keys": keys, "via": method.name})
    assert not unresolved, f"body shapes this reader cannot classify: {unresolved}"
    return out


def _client_url_literals() -> list[tuple[str, str]]:
    """(method, `/internal/...` literal) for every one held by a caller.

    This is the reading the walk is checked against, and it is deliberately not built from the
    walk: it asks what URLs the client knows about, not what the walker noticed about them.
    """
    src = CLIENT.read_text(encoding="utf-8")
    return [(method.name, literal)
            for method in _java_methods(src) if method.name not in TRANSPORT
            for literal in re.findall(r'"(/internal/[^"]*)"', method.body)]


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
    assert len(built) >= 19, f"the reader lost client calls: {[c['via'] for c in built]}"
    for call in built + _relay_calls():
        assert (call["verb"], call["path"]) in routes, \
            f"{call['via']} calls {call['verb']} {call['path']}, which ai-service never maps"


def test_the_walk_claims_every_internal_url_the_client_holds():
    """A literal path the client knows about must be claimed by a walked request site.

    The floor is what makes this more than the assertion above re-read: a walker that found
    nothing would claim nothing, and an empty census would agree with it. A site the reader
    could not type lands in `unparsed`, which is refused here rather than raised in the walk --
    a raise takes the collection of every importer down with it. `unparsed` is a claim of its
    own: a method that makes two requests from one literal would leave the census satisfied by
    the site that was read, while the second one is still lost.
    """
    census = _client_url_literals()
    assert len(census) >= 19, f"the client stopped holding urls: {census}"
    src = CLIENT.read_text(encoding="utf-8")
    sites, unparsed = _call_sites(src, _java_methods(src))
    assert unparsed == [], f"request sites this reader lost: {unparsed}"
    claimed = set()
    for verb, expr, method, _spelling in sites:
        literal = re.search(r'"(/internal/[^"]*)"', expr)
        assert literal, f"{method.name} {verb}: a call site whose path has no url literal in it"
        claimed.add((method.name, literal.group(1)))
    unclaimed = sorted(set(census) - claimed)
    assert unclaimed == [], (f"the client builds requests from {unclaimed} that no walk site "
                             f"reads -- an endpoint nobody checks")


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
    # The two sites a reader keyed on `return` lost, named rather than counted: a walk that
    # finds nineteen calls but not these two is not reading the client's three spellings.
    by_method = {c["via"]: c for c in _calls()}
    assert by_method["listMemories"]["verb"] == "GET"
    assert by_method["listMemories"]["path"] == "/internal/memories", \
        "the local binding was not followed, or the `?kinds=` conditional folded into the path"
    assert by_method["deleteMemory"]["verb"] == "DELETE"
    assert by_method["deleteMemory"]["path"] == "/internal/memories/{}"
    assert {c["via"] for c in _calls()} <= {m.name for m in _java_methods(
        CLIENT.read_text(encoding="utf-8"))}, "a call attributed to no method of the client"


def test_only_the_legacy_text_ingest_still_sends_keys_to_an_untyped_body():
    """The gate can only check keys against a model, so a call that sends keys to a schema-less
    body is a hole -- and the set of holes stays declared rather than silently growing."""
    untyped = sorted({c["path"] for route, c in _mapped_calls()
                      if c["keys"] and _model(route) is None})
    assert untyped == ["/internal/ingest/text"], \
        f"a backend call now sends keys nobody checks: {untyped}"
