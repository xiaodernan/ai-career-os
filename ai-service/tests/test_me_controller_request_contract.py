"""MeController: the canonical /me surface, and its frontend-facing alias in UserController.

``backend/src/main/java/com/careeros/auth/web/MeController.java`` serves ``/api/v1/me``
(GET + PATCH) and is the only other place in the backend that binds ``UpdateMeRequest``:
the browser's calls go through its alias ``UserController`` (``/api/v1/users/me``), which
vitest's ``endpoints.test.ts`` lists in ``NEVER_REFERENCED`` as "MeController's alias of
/users/me". Nothing else in the suite reads this file -- a dropped ``@Valid``, a retyped
answer, or a PATCH forwarding to the read path would leave every other gate green.

This gate pins, on the canonical side and across the pair:

- The class binds exactly one base prefix with a bare ``@GetMapping`` and a bare
  ``@PatchMapping`` -- two routes, no other verb.
- GET asks for no body (``@CurrentUser`` only) and answers ``MeResponse``.
- PATCH binds ``@RequestBody @Valid UpdateMeRequest`` and answers ``MeResponse``.
- Both spellings forward to the same ``UserService`` methods with the same argument
  shapes: ``userService.get(user.id())`` / ``userService.update(user.id(), request)``.
- ``UpdateMeRequest`` is validated at exactly two sites in the whole backend, one per
  spelling -- the alias pair is the record's entire audience.
- The alias story agrees across four carriers: the registry's reason names this
  controller and the alias path it derives from UserController's own prefix; the
  client's ``auth.me``/``auth.profile`` values equal the alias's derived routes, not
  the canonical one; UserController's docstring spells the same two alias routes.

Boundaries (held elsewhere, deliberately not re-pinned here): ``UpdateMeRequest``'s ten
fields, its guards, and the settings-page mirrors are #210's gate
(``test_user_controller_request_contract.py``); the ``["me"]`` cache write/refetch
ownership is ``test_cache_writes_ship_what_the_key_owner_produces.py``; the route census
and the ``NEVER_REFERENCED`` membership rule are vitest's ``endpoints.test.ts``.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ME_CTRL = "backend/src/main/java/com/careeros/auth/web/MeController.java"
USER_CTRL = "backend/src/main/java/com/careeros/user/web/UserController.java"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"
VITEST = "frontend/src/lib/api/endpoints.test.ts"
BACKEND = ROOT / "backend" / "src" / "main" / "java"

API_PREFIX = "/api/v1"

ME_GET_SIG = "public MeResponse me(@CurrentUser AuthUser user) {"
ME_PATCH_SIG = (
    "public MeResponse update(@CurrentUser AuthUser user, "
    "@RequestBody @Valid UpdateMeRequest request) {"
)
USER_GET_SIG = "public MeResponse me(@CurrentUser AuthUser user) {"
USER_PATCH_SIG = (
    "public MeResponse updateMe(@CurrentUser AuthUser user, "
    "@RequestBody @Valid UpdateMeRequest request) {"
)

FORWARD_CALLS = [
    "return userService.get(user.id());",
    "return userService.update(user.id(), request);",
]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


@lru_cache(maxsize=1)
def me_source() -> str:
    return read(ME_CTRL)


@lru_cache(maxsize=1)
def user_source() -> str:
    return read(USER_CTRL)


@lru_cache(maxsize=1)
def endpoints_source() -> str:
    return read(ENDPOINTS)


@lru_cache(maxsize=1)
def vitest_source() -> str:
    return read(VITEST)


# --------------------------------------------------------------------------- helpers

MAPPING = re.compile(r'@(Get|Post|Put|Patch|Delete)Mapping\b(?:\("([^"]*)")?')


def mapping_verbs(source: str) -> list:
    """The `@…Mapping` annotations of one controller, in file order: ``(verb, raw path)``."""
    return [(m.group(1), m.group(2) or "") for m in MAPPING.finditer(source)]


def base_prefix(source: str) -> str:
    """The class-level ``@RequestMapping`` value, read before the class body starts."""
    head = source[: source.index("public class")]
    m = re.search(r'@RequestMapping\(\s*(?:value\s*=\s*|path\s*=\s*)?"([^"]*)"', head)
    assert m, "no class-level @RequestMapping found"
    return m.group(1)


def client_path(java_pattern: str) -> str:
    """A full backend pattern without the ``/api/v1`` prefix, as ``endpoints.*`` spells it."""
    assert java_pattern.startswith(API_PREFIX), java_pattern
    return java_pattern[len(API_PREFIX):]


def method_block(source: str, signature: str) -> str:
    """The ``{...}`` body of the one method declared with exactly ``signature``."""
    assert source.count(signature) == 1, (
        "signature %r appears %d times" % (signature, source.count(signature))
    )
    start = source.index(signature) + len(signature) - 1
    depth = 0
    for i in range(start, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
    raise AssertionError("unbalanced braces after %r" % signature)


def imports(source: str) -> set:
    return set(re.findall(r"^import\s+([\w.]+);", source, re.M))


def forward_statements(source: str) -> list:
    """Every ``return userService.<method>(...)`` statement, whitespace-normalized."""
    out = []
    for m in re.finditer(r"return\s+userService\.\w+\(", source):
        open_paren = source.index("(", m.end() - 1)
        depth = 0
        close = -1
        for i in range(open_paren, len(source)):
            ch = source[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    close = i
                    break
        end = source.index(";", close)
        out.append(re.sub(r"\s+", " ", source[m.start() : end + 1]))
    return out


def braced_after(source: str, marker: str) -> str:
    """The balanced ``{...}`` block starting at the first ``{`` after ``marker``."""
    i = source.find(marker)
    assert i != -1, "marker not found: %s" % marker
    start = source.index("{", i)
    depth = 0
    for j in range(start, len(source)):
        ch = source[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start : j + 1]
    raise AssertionError("unbalanced braces after %s" % marker)


# ----------------------------------------------------------- the canonical surface

def test_the_canonical_route_is_one_base_prefix_with_exactly_a_get_and_a_patch():
    src = me_source()
    assert base_prefix(src) == "/api/v1/me", (
        "MeController's base prefix moved to %r" % base_prefix(src)
    )
    mapping = mapping_verbs(src)
    assert mapping == [("Get", ""), ("Patch", "")], (
        "the canonical surface now binds %s -- exactly a bare GET and a bare PATCH live here"
        % mapping
    )
    for verb in ("Post", "Put", "Delete"):
        assert "@%sMapping" % verb not in src, "%s route appeared on the canonical surface" % verb
    assert client_path(base_prefix(src)) == "/me"


def test_the_get_handler_asks_for_no_body_and_answers_the_me_record():
    src = me_source()
    block = method_block(src, ME_GET_SIG)
    assert "@RequestBody" not in block and "@Valid" not in block, (
        "the GET now binds a request body:\n%s" % block
    )
    assert "return userService.get(user.id());" in block, (
        "the GET no longer reads the user through userService.get:\n%s" % block
    )
    assert "com.careeros.auth.dto.MeResponse" in imports(src), (
        "the GET's answer is no longer imported from the record this pair shares"
    )


def test_the_patch_handler_binds_the_update_record_for_validation():
    src = me_source()
    assert src.count("@RequestBody @Valid UpdateMeRequest") == 1, (
        "expected one @Valid UpdateMeRequest binding in MeController, found %d"
        % src.count("@RequestBody @Valid UpdateMeRequest")
    )
    block = method_block(src, ME_PATCH_SIG)
    assert "return userService.update(user.id(), request);" in block, (
        "the PATCH no longer writes the request through userService.update:\n%s" % block
    )
    needed = {
        "jakarta.validation.Valid",
        "org.springframework.web.bind.annotation.RequestBody",
        "com.careeros.auth.dto.UpdateMeRequest",
    }
    missing = needed - imports(src)
    assert not missing, "MeController no longer imports %s" % sorted(missing)


# ----------------------------------------------------------- the pair as one surface

def test_the_two_spellings_forward_identically_to_one_service():
    me = me_source()
    user = user_source()
    me_calls = forward_statements(me)
    user_calls = forward_statements(user)
    assert me_calls == FORWARD_CALLS, (
        "the canonical controller now forwards %s, expected %s" % (me_calls, FORWARD_CALLS)
    )
    assert user_calls == FORWARD_CALLS, (
        "the alias controller now forwards %s, expected %s" % (user_calls, FORWARD_CALLS)
    )
    for name, src in (("MeController", me), ("UserController", user)):
        assert "com.careeros.auth.service.UserService" in imports(src), (
            "%s no longer injects the shared UserService" % name
        )
        assert "private final UserService userService;" in src, (
            "%s's userService field changed type" % name
        )
        for fqn in ("com.careeros.auth.dto.MeResponse", "com.careeros.auth.dto.UpdateMeRequest"):
            assert fqn in imports(src), "%s no longer imports %s" % (name, fqn)
    assert USER_GET_SIG in user, "the alias GET signature changed"
    assert USER_PATCH_SIG in user, "the alias PATCH signature changed"


def test_the_update_record_is_bound_at_exactly_two_sites_one_per_spelling():
    files = sorted(BACKEND.rglob("*Controller.java"))
    assert len(files) >= 15, "controller walk found only %d files" % len(files)
    rels = [f.relative_to(ROOT).as_posix() for f in files]
    assert ME_CTRL in rels and USER_CTRL in rels, "one of the two /me controllers left the walk"
    counts = {}
    for f in files:
        n = f.read_text(encoding="utf-8").replace("\r\n", "\n").count(
            "@RequestBody @Valid UpdateMeRequest"
        )
        if n:
            counts[f.relative_to(ROOT).as_posix()] = n
    assert counts == {ME_CTRL: 1, USER_CTRL: 1}, (
        "UpdateMeRequest's validated binding sites changed: %s" % counts
    )
    dto = read("backend/src/main/java/com/careeros/auth/dto/UpdateMeRequest.java")
    assert "package com.careeros.auth.dto;" in dto, "the DTO's package no longer matches its import"
    assert "public record UpdateMeRequest(" in dto, (
        "the file both controllers import no longer declares the record they bind"
    )


def test_the_alias_story_agrees_across_registry_docstring_and_client_map():
    me_v, profile_v = auth_client_values()
    canonical = client_path(base_prefix(me_source()))
    assert canonical == "/me"
    user_prefix = base_prefix(user_source())
    alias_me = client_path(user_prefix + "/me")
    alias_profile = client_path(user_prefix + "/me/profile")
    assert (me_v, profile_v) == (alias_me, alias_profile), (
        "the client spells %r/%r while the alias controller serves %r/%r"
        % (me_v, profile_v, alias_me, alias_profile)
    )
    assert me_v != canonical, (
        "the client now spells the canonical route %r directly; the alias pair's story below "
        "would need rewriting" % canonical
    )
    vitest = vitest_source()
    key = '"%s":' % canonical
    assert vitest.count(key) == 1, (
        "the never-referenced registry no longer lists %s exactly once" % key
    )
    reason = re.search(re.escape(key) + r'\s*"([^"]*)"', vitest).group(1)
    assert "MeController" in reason, (
        "the registry's reason for %s no longer names the controller that binds it: %r"
        % (canonical, reason)
    )
    assert alias_me in reason, (
        "the registry's reason for %s no longer names the alias spelling %s: %r"
        % (canonical, alias_me, reason)
    )
    user = user_source()
    head = user[: user.index("public class")]
    assert "alias" in head, "UserController stopped saying it is an alias"
    for route in (alias_me, alias_profile):
        assert (API_PREFIX + route) in head, (
            "the alias docstring no longer names %s as one of its routes" % (API_PREFIX + route)
        )
    assert (API_PREFIX + canonical) not in user, (
        "UserController now spells %s itself; the alias story says the client routes through "
        "the alias, not the canonical surface" % (API_PREFIX + canonical)
    )


@lru_cache(maxsize=1)
def auth_client_values() -> tuple:
    """The `auth.me`/`auth.profile` values, read inside the auth block of the endpoint map."""
    block = braced_after(endpoints_source(), "auth: {")
    me_v = re.search(r"\bme:\s*\"([^\"]+)\"", block)
    profile_v = re.search(r"\bprofile:\s*\"([^\"]+)\"", block)
    assert me_v and profile_v, "the auth block no longer spells me/profile"
    return me_v.group(1), profile_v.group(1)
