"""The auth controller's request contract: six public POSTs, five records, four screens.

``AuthController`` carries the session lifecycle -- register, login, refresh, logout, and the
two password-recovery routes. Six JSON bodies, each bound with ``@Valid``:

- ``POST /register`` -> ``RegisterRequest(email, password, displayName)``, answered 201
- ``POST /login`` -> ``LoginRequest(email, password)``
- ``POST /refresh`` -> ``RefreshTokenRequest(refreshToken)``, written by ``runRefresh``'s raw
  fetch (the only /auth/refresh caller in the app)
- ``POST /logout`` -> ``RefreshTokenRequest``, written by ``authApi.logout`` -- one record,
  two binding routes, two writers
- ``POST /password/forgot`` -> ``ForgotPasswordRequest(email)``
- ``POST /password/reset`` -> ``ResetPasswordRequest(token, newPassword)``

The browser reaches them through ``authApi`` in ``lib/api/client.ts``. Its register/login
bodies are verbatim pass-throughs (``body: payload``) typed by the exported interfaces
``RegisterPayload``/``LoginPayload`` -- exactly the two call sites that
``frontend/src/lib/api/endpoints.test.ts`` parks in its UNREADABLE_BODIES registry with the
reason "its fields are typed by client.ts, which this reader stops at". This gate is the
reader that does not stop: it joins the interfaces, the screens' ``mutate`` literals, and
the five records, so the register/login payload keys are held name-by-name after all.

Cross-plane split (measured, not assumed): the vitest gate already holds the route/verb
parity of all six routes, and checks the four *literal* bodies (logout, forgot, reset and
runRefresh's ``JSON.stringify``) as a subset rule -- every key sent must be accepted by the
record. This gate holds the complementary equality (a record field no writer sends reddens
here only), the parked register/login pair, and what a name-oriented rule cannot see:
``@Valid`` on every body, the per-record guard lines, the shared recovery module's bounds
constants against the records, the ``auth: false`` opt-out of the bearer, the token
record's two writers and their shared store reader, and the screens' own payloads.

Measured divergence (pinned, not fixed): the register screen mirrors the record's minimum
with a literal ``v.length < 8`` but checks no ceiling, while both password records carry
``@Size(max = 72)`` (BCrypt reads no further). A longer passphrase therefore reaches the
generic ``"Request validation failed"`` 400 -- with the per-field details dead (#201) the
screen has nothing to act on. The recovery module already documents why the ceiling
matters, and the reset form is the one screen that enforces it (via ``passwordIssue``).
Adopting ``passwordIssue`` in credentials-form is the queued fix; this file pins today's
shape so that fix reddens a statement instead of drifting.

What this gate deliberately does NOT re-pin: the hooks' optimistic cache writes (#198), the
``["me"]`` query ownership, the envelope's success flag (#202), or any response record.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/auth/web/AuthController.java"
DTO_DIR = "backend/src/main/java/com/careeros/auth/dto/"
REGISTER_DTO = DTO_DIR + "RegisterRequest.java"
LOGIN_DTO = DTO_DIR + "LoginRequest.java"
TOKEN_DTO = DTO_DIR + "RefreshTokenRequest.java"
FORGOT_DTO = DTO_DIR + "ForgotPasswordRequest.java"
RESET_DTO = DTO_DIR + "ResetPasswordRequest.java"
CLIENT = "frontend/src/lib/api/client.ts"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"
HOOKS = "frontend/src/lib/hooks/auth.ts"
CREDENTIALS_FORM = "frontend/src/components/auth/credentials-form.tsx"
FORGOT_FORM = "frontend/src/components/auth/forgot-password-form.tsx"
RESET_FORM = "frontend/src/components/auth/reset-password-form.tsx"
RECOVERY = "frontend/src/lib/auth-recovery.ts"

ROUTE_BODIES = {
    "/register": "RegisterRequest",
    "/login": "LoginRequest",
    "/refresh": "RefreshTokenRequest",
    "/logout": "RefreshTokenRequest",
    "/password/forgot": "ForgotPasswordRequest",
    "/password/reset": "ResetPasswordRequest",
}

RECORD_FILES = {
    "RegisterRequest": (REGISTER_DTO, ["email", "password", "displayName"]),
    "LoginRequest": (LOGIN_DTO, ["email", "password"]),
    "RefreshTokenRequest": (TOKEN_DTO, ["refreshToken"]),
    "ForgotPasswordRequest": (FORGOT_DTO, ["email"]),
    "ResetPasswordRequest": (RESET_DTO, ["token", "newPassword"]),
}

GUARD_LINES = {
    "RegisterRequest": [
        "@NotBlank @Email @Size(max = 255) String email",
        "@NotBlank @Size(min = 8, max = 72) String password",
        "@NotBlank @Size(max = 120) String displayName",
    ],
    "LoginRequest": [
        "@NotBlank @Email @Size(max = 255) String email",
        "@NotBlank @Size(max = 72) String password",
    ],
    "RefreshTokenRequest": ["@NotBlank @Size(max = 512) String refreshToken"],
    "ForgotPasswordRequest": ["@NotBlank @Email @Size(max = 255) String email"],
    "ResetPasswordRequest": [
        "@NotBlank @Size(max = 512) String token",
        "@NotBlank @Size(min = 8, max = 72) String newPassword",
    ],
}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


# --------------------------------------------------------------------------- helpers

@lru_cache(maxsize=1)
def controller_source() -> str:
    return read(CONTROLLER)


@lru_cache(maxsize=1)
def client_source() -> str:
    return read(CLIENT)


def record_body(record_name: str, source: str) -> str:
    """Return the raw text between ``record Name(`` and ``) {``, or "" if absent."""
    m = re.search(r"record\s+" + record_name + r"\s*\((.*?)\)\s*\{", source, re.DOTALL)
    return m.group(1) if m else ""


def java_record_fields(record_name: str, source: str) -> list[str]:
    """Field names declared inside ``record RecordName(...)``, annotations stripped."""
    body = record_body(record_name, source)
    if not body:
        return []
    cleaned = re.sub(r"@[\w.]+\s*(?:\{[^}]*\}|\([^)]*\))?\s*", "", body)
    cleaned = re.sub(r"<[^>]*>", "", cleaned)
    cleaned = cleaned.replace("\n", " ")
    fields = []
    for part in cleaned.split(","):
        part = part.strip()
        if not part or part.startswith("//"):
            continue
        tokens = part.split()
        if tokens:
            fields.append(tokens[-1])
    return fields


def braced_arg_after(source: str, marker: str) -> str:
    """Return the balanced ``{...}`` block starting at the first ``{`` after ``marker``."""
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


def object_literal_keys(block: str) -> list[str]:
    """Property names of an object literal, including shorthand entries.

    The lookahead accepts end-of-block so a lone shorthand ``{ key }`` -- no ``:``, no
    trailing comma -- still reads as one key.
    """
    inner = block[1:-1]
    return re.findall(r"(?:^|,)\s*([A-Za-z_$][\w$]*)\s*(?=:|,|$)", inner)


def type_literal_keys(block: str) -> list[str]:
    """Member names of a TypeScript type literal, whose members separate with ``;``."""
    inner = block[1:-1]
    return re.findall(r"([A-Za-z_$][\w$]*)\s*:", inner)


def ts_call_bodies(fn_name: str, source: str) -> list[str]:
    """Return the text of every ``[export] [async] function fn_name(...) {...}`` block.

    ``export`` is optional because the token record's second writer, ``runRefresh``, is
    module-private -- the census that finds it counts references, not exports.
    """
    blocks = []
    pattern = (
        r"(?:export\s+)?(?:async\s+)?function\s+" + fn_name + r"\s*\([^)]*\)\s*(?::\s*[^{;]+)?\s*\{"
    )
    for m in re.finditer(pattern, source):
        start = m.end() - 1
        depth = 0
        i = start
        while i < len(source):
            ch = source[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(source[start : i + 1])
                    break
            i += 1
    return blocks


def route_body_table(source: str) -> dict:
    """Map every ``@PostMapping("path")`` to the record its ``@RequestBody @Valid`` binds."""
    matches = list(re.finditer(r'@PostMapping\("([^"]+)"\)', source))
    table: dict = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        segment = source[m.end():end]
        body = re.search(r"@RequestBody @Valid (\w+)", segment)
        table[m.group(1)] = body.group(1) if body else None
    return table


def options_blob(member: str) -> str:
    """The options object of ``request(..., endpoints.auth.<member>, { ... })``."""
    return braced_arg_after(client_source(), "endpoints.auth.%s, " % member)


def password_bounds(rel: str, field: str) -> tuple:
    """``(min, max)`` parsed from the ``@Size(...)`` guard on a password-like field."""
    m = re.search(r"@Size\(([^)]*)\)\s+String\s+" + field + r"\b", read(rel))
    assert m, "no @Size guard on `String %s` in %s" % (field, rel)
    args = m.group(1)
    lo = re.search(r"min\s*=\s*(\d+)", args)
    hi = re.search(r"max\s*=\s*(\d+)", args)
    return (int(lo.group(1)) if lo else None, int(hi.group(1)) if hi else None)


# --------------------------------------------------------------------------- case 1: the route table

def test_the_controller_binds_six_routes_each_to_one_validated_record():
    src = controller_source()
    assert '@RequestMapping("/api/v1/auth")' in src, (
        "AuthController's base path moved; every endpoint below resolves against it"
    )
    table = route_body_table(src)
    assert table == ROUTE_BODIES, (
        "the route->record table drifted: %s\n@PostMapping and @RequestBody @Valid are both "
        "required for a route to appear here with its record" % table
    )
    assert src.count("@PostMapping") == 6, (
        "expected six POST routes, found %d" % src.count("@PostMapping")
    )
    assert src.count("@RequestBody") == 6, (
        "expected one @RequestBody per route, found %d" % src.count("@RequestBody")
    )
    assert src.count("@Valid") == 6, (
        "expected every body to be @Valid, found %d -- without it the record's guards stop "
        "being enforced and bad payloads reach the service" % src.count("@Valid")
    )
    assert src.count("@RequestParam") == 0 and src.count("@PathVariable") == 0, (
        "AuthController grew a query or path binding; the six-POST shape is the whole request "
        "surface of this gate"
    )


# --------------------------------------------------------------------------- case 2: the five records

def test_the_five_records_bind_exactly_their_declared_fields():
    for record, (rel, expected) in RECORD_FILES.items():
        fields = java_record_fields(record, read(rel))
        assert fields == expected, (
            "%s binds %s; the writers type against %s (a renamed or added field silently "
            "changes which keys the wire accepts)" % (record, fields, expected)
        )


def test_each_records_guards_spell_their_bounds():
    for record, (rel, _fields) in RECORD_FILES.items():
        src = read(rel)
        for line in GUARD_LINES[record]:
            assert line in src, (
                "%s's guard line changed: %r is gone -- the bound it carried is no longer "
                "enforced:\n%s" % (record, line, src)
            )


# --------------------------------------------------------------------------- case 3: bounds agreement

def test_the_password_bounds_are_one_policy_across_the_three_records():
    register = password_bounds(REGISTER_DTO, "password")
    reset = password_bounds(RESET_DTO, "newPassword")
    login = password_bounds(LOGIN_DTO, "password")
    module = read(RECOVERY)
    assert "export const PASSWORD_MIN_LENGTH = 8;" in module, (
        "PASSWORD_MIN_LENGTH is no longer declared as 8; it mirrors the two records below"
    )
    assert "export const PASSWORD_MAX_LENGTH = 72;" in module, (
        "PASSWORD_MAX_LENGTH is no longer declared as 72; it mirrors the three records below"
    )
    assert register == (8, 72), (
        "RegisterRequest.password is @Size(8, 72); now %s" % (register,)
    )
    assert reset == register, (
        "the two password-setting records disagree: RegisterRequest %s vs ResetPasswordRequest "
        "%s -- one bcrypt policy, two declarations" % (register, reset)
    )
    assert login == (None, 72), (
        "LoginRequest.password bounds are now %s; the shipped shape is max 72 with no minimum "
        "(a legacy short password may still sign in; the screen keeps its own floor)" % (login,)
    )
    assert "if (value.length < PASSWORD_MIN_LENGTH) {" in module, (
        "passwordIssue no longer refuses below the minimum"
    )
    assert "if (value.length > PASSWORD_MAX_LENGTH) {" in module, (
        "passwordIssue no longer refuses above the ceiling the records carry"
    )
    assert "passwordIssue(password)" in read(RESET_FORM), (
        "the reset form no longer guards its password field with the shared bounds check"
    )


# --------------------------------------------------------------------------- case 4: payload types

def test_the_payload_types_carry_exactly_the_record_fields():
    src = client_source()
    login_iface = type_literal_keys(braced_arg_after(src, "export interface LoginPayload "))
    register_iface = type_literal_keys(
        braced_arg_after(src, "export interface RegisterPayload extends LoginPayload ")
    )
    assert "extends LoginPayload" in src, (
        "RegisterPayload no longer extends LoginPayload; the key union below assumes it does"
    )
    assert login_iface == ["email", "password"], (
        "LoginPayload carries %s but LoginRequest binds ['email', 'password'] -- register and "
        "login post `payload` verbatim, so this interface IS the wire" % login_iface
    )
    assert sorted(register_iface + login_iface) == ["displayName", "email", "password"], (
        "RegisterPayload's own members are %s; with LoginPayload that must be exactly "
        "RegisterRequest's three fields" % register_iface
    )
    assert "async register(payload: RegisterPayload): Promise<User> {" in src, (
        "authApi.register no longer takes the typed RegisterPayload"
    )
    assert "async login(payload: LoginPayload): Promise<User> {" in src, (
        "authApi.login no longer takes the typed LoginPayload"
    )
    forgot_type = type_literal_keys(braced_arg_after(src, "async forgotPassword(payload: "))
    reset_type = type_literal_keys(braced_arg_after(src, "async resetPassword(payload: "))
    assert forgot_type == ["email"], (
        "forgotPassword's inline payload type is %s; ForgotPasswordRequest binds ['email']"
        % forgot_type
    )
    assert reset_type == ["token", "newPassword"], (
        "resetPassword's inline payload type is %s; ResetPasswordRequest binds "
        "['token', 'newPassword']" % reset_type
    )


# --------------------------------------------------------------------------- case 5: the screens

def test_the_credential_screens_mutate_exactly_the_payload_keys():
    form = read(CREDENTIALS_FORM)
    login_keys = object_literal_keys(braced_arg_after(form, "login.mutate("))
    register_keys = object_literal_keys(braced_arg_after(form, "register.mutate("))
    assert login_keys == ["email", "password"], (
        "the sign-in screen mutates %s; LoginRequest binds ['email', 'password']" % login_keys
    )
    assert sorted(register_keys) == ["displayName", "email", "password"], (
        "the register screen mutates %s; RegisterRequest binds ['email', 'password', "
        "'displayName']" % register_keys
    )


def test_the_recovery_screens_send_the_records_own_keys():
    forgot_keys = object_literal_keys(braced_arg_after(read(FORGOT_FORM), "forgot.mutate("))
    reset_keys = object_literal_keys(braced_arg_after(read(RESET_FORM), "reset.mutate("))
    assert forgot_keys == ["email"], (
        "the forgot screen mutates %s; ForgotPasswordRequest binds ['email']" % forgot_keys
    )
    assert reset_keys == ["token", "newPassword"], (
        "the reset screen mutates %s (token may be shorthand); ResetPasswordRequest binds "
        "['token', 'newPassword']" % reset_keys
    )


# --------------------------------------------------------------------------- case 6: the writers

def test_every_literal_body_names_only_its_records_fields():
    src = client_source()
    assert src.count("body: payload,") == 2, (
        "register and login must both post `payload` verbatim; found %d" % src.count("body: payload,")
    )
    for member, record in (
        ("forgotPassword", "ForgotPasswordRequest"),
        ("resetPassword", "ResetPasswordRequest"),
        ("logout", "RefreshTokenRequest"),
    ):
        blob = options_blob(member)
        body = braced_arg_after(blob, "body: ")
        keys = object_literal_keys(body)
        fields = java_record_fields(record, read(RECORD_FILES[record][0]))
        assert keys == fields, (
            "authApi.%s posts %s; %s binds %s -- equality, where the vitest subset rule only "
            "catches keys the record does not accept" % (member, keys, record, fields)
        )
    bodies = ts_call_bodies("runRefresh", src)
    assert len(bodies) == 1, "expected exactly one runRefresh, found %d" % len(bodies)
    refresh_body = braced_arg_after(bodies[0], "JSON.stringify(")
    assert object_literal_keys(refresh_body) == ["refreshToken"], (
        "runRefresh's raw fetch posts %s; RefreshTokenRequest binds ['refreshToken']"
        % object_literal_keys(refresh_body)
    )


# --------------------------------------------------------------------------- case 7: one record, two writers

def test_the_token_record_is_written_at_two_sites_that_share_one_reader():
    src = client_source()
    assert src.count("const refreshToken = tokenStore.getRefresh();") == 2, (
        "both writers of RefreshTokenRequest must read the stored token; found %d store reads"
        % src.count("const refreshToken = tokenStore.getRefresh();")
    )
    bodies = ts_call_bodies("runRefresh", src)
    assert len(bodies) == 1, "expected exactly one runRefresh, found %d" % len(bodies)
    for line in (
        "const refreshToken = tokenStore.getRefresh();",
        "if (!refreshToken) return null;",
        'method: "POST",',
        "body: JSON.stringify({ refreshToken }),",
    ):
        assert line in bodies[0], (
            "runRefresh lost %r; a missing token must not post an empty body" % line
        )
    root = ROOT / "frontend" / "src"
    files = sorted(list(root.rglob("*.ts")) + list(root.rglob("*.tsx")))
    assert len(files) >= 100, (
        "the census walked %d files; the floor is 100, so this is a walk bug, not an "
        "absence" % len(files)
    )
    hits = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(r"auth\.refresh\b", text):
            hits.append((p.relative_to(ROOT).as_posix(), text.count("\n", 0, m.start()) + 1))
    assert len(hits) == 1, (
        "endpoints.auth.refresh has %d references; the raw single-flight fetch is the only "
        "caller, so a second one has to be re-homed into this gate:\n%s" % (len(hits), hits)
    )
    where, line = hits[0]
    assert where == "frontend/src/lib/api/client.ts", (
        "the only auth.refresh reference moved to %s:%d" % (where, line)
    )
    assert "fetch(buildUrl(endpoints.auth.refresh), {" in src, (
        "the refresh call no longer goes through buildUrl(endpoints.auth.refresh)"
    )


# --------------------------------------------------------------------------- case 8: the bearer opt-out

def test_the_public_wrappers_opt_out_of_the_bearer_and_the_session_ones_do_not():
    block = braced_arg_after(client_source(), "export const authApi = ")
    assert block.count("auth: false") == 4, (
        "expected register/login/forgot/reset to run without a bearer token, found %d "
        "opt-outs" % block.count("auth: false")
    )
    for member in ("register", "login", "forgotPassword", "resetPassword"):
        blob = options_blob(member)
        assert "auth: false" in blob, (
            "authApi.%s lost its auth: false -- it now attaches a stale token to the one "
            "call that must work before a session exists" % member
        )
    logout_blob = options_blob("logout")
    assert "auth: false" not in logout_blob, (
        "authApi.logout gained auth: false; revoking the refresh token is a session call"
    )


# --------------------------------------------------------------------------- case 9: the screens' guard mirror

def test_the_credential_screens_mirror_the_minimum_but_not_the_ceiling():
    form = read(CREDENTIALS_FORM)
    thresholds = re.findall(r"v\.length < (\d+)", form)
    register_min = password_bounds(REGISTER_DTO, "password")[0]
    assert thresholds == ["8", "8"], (
        "sign-in and register keep their own inline thresholds (%s); this test measures them, "
        "so the shape has to be restated" % thresholds
    )
    assert all(int(t) == register_min for t in thresholds), (
        "an inline threshold (%s) no longer equals RegisterRequest.password's minimum (%s)"
        % (thresholds, register_min)
    )
    assert "passwordIssue" not in form, (
        "credentials-form adopted passwordIssue -- the divergence below just closed; re-home "
        "this characterization into a mirror assertion instead of deleting it"
    )
    assert "PASSWORD_MAX_LENGTH" not in form, (
        "credentials-form now knows the ceiling constant; re-measure the paragraph below"
    )


# --------------------------------------------------------------------------- case 10: the hooks

def test_the_screens_mutate_through_the_auth_hooks_that_reach_the_records():
    hooks = read(HOOKS)
    for line in (
        "mutationFn: authApi.register,",
        "mutationFn: authApi.login,",
        "mutationFn: () => authApi.logout().catch(() => undefined),",
        "return useMutation({ mutationFn: authApi.forgotPassword });",
        "mutationFn: authApi.resetPassword,",
    ):
        assert line in hooks, (
            "auth.ts lost %r; a screen's mutate keys only reach the records through these "
            "links" % line
        )
    form = read(CREDENTIALS_FORM)
    assert "const login = useLogin();" in form and "const register = useRegister();" in form, (
        "the credentials form no longer mutates through useLogin/useRegister"
    )
    assert "const forgot = useForgotPassword();" in read(FORGOT_FORM), (
        "the forgot screen no longer mutates through useForgotPassword"
    )
    assert "const reset = useResetPassword();" in read(RESET_FORM), (
        "the reset screen no longer mutates through useResetPassword"
    )
