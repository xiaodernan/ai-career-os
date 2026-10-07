"""Mutation arms for the auth-controller request-contract gate (#212).

Each arm mutates one clause of the contract and predicts which tests should go red.
All predictions are frozen before running, so a mismatch is itself evidence.

Read/write are byte-faithful (``newline=""``): the working tree is shared with other
sessions, so an arm must be undone by re-writing the captured bytes, never by
``git checkout``. Needles are single-line: the working copies are CRLF, so a multiline
``str.replace`` needle carrying ``\\n`` would match nothing and no-op the arm.

Test-name shorthand used in the predictions (gate order):
  T1  six routes each to one validated record
  T2  five records bind exactly their declared fields
  T3  each record's guards spell their bounds
  T4  password bounds are one policy across the three records
  T5  payload types carry exactly the record fields
  T6  credential screens mutate exactly the payload keys
  T7  recovery screens send the records' own keys
  T8  every literal body names only its record's fields
  T9  token record written at two sites sharing one store reader
  T10 public wrappers opt out of the bearer, session one does not
  T11 credential screens guard through the shared password function
  T12 screens mutate through the hooks that reach the records
  T13 remaining ceilings mirror between records and module
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/auth/web/AuthController.java"
REGISTER_DTO = "backend/src/main/java/com/careeros/auth/dto/RegisterRequest.java"
LOGIN_DTO = "backend/src/main/java/com/careeros/auth/dto/LoginRequest.java"
TOKEN_DTO = "backend/src/main/java/com/careeros/auth/dto/RefreshTokenRequest.java"
FORGOT_DTO = "backend/src/main/java/com/careeros/auth/dto/ForgotPasswordRequest.java"
RESET_DTO = "backend/src/main/java/com/careeros/auth/dto/ResetPasswordRequest.java"
CLIENT = "frontend/src/lib/api/client.ts"
HOOKS = "frontend/src/lib/hooks/auth.ts"
CREDENTIALS_FORM = "frontend/src/components/auth/credentials-form.tsx"
FORGOT_FORM = "frontend/src/components/auth/forgot-password-form.tsx"
RESET_FORM = "frontend/src/components/auth/reset-password-form.tsx"
RECOVERY = "frontend/src/lib/auth-recovery.ts"

T1 = "test_the_controller_binds_six_routes_each_to_one_validated_record"
T2 = "test_the_five_records_bind_exactly_their_declared_fields"
T3 = "test_each_records_guards_spell_their_bounds"
T4 = "test_the_password_bounds_are_one_policy_across_the_three_records"
T5 = "test_the_payload_types_carry_exactly_the_record_fields"
T6 = "test_the_credential_screens_mutate_exactly_the_payload_keys"
T7 = "test_the_recovery_screens_send_the_records_own_keys"
T8 = "test_every_literal_body_names_only_its_records_fields"
T9 = "test_the_token_record_is_written_at_two_sites_that_share_one_reader"
T10 = "test_the_public_wrappers_opt_out_of_the_bearer_and_the_session_ones_do_not"
T11 = "test_the_credential_screens_guard_through_the_shared_password_function"
T12 = "test_the_screens_mutate_through_the_auth_hooks_that_reach_the_records"
T13 = "test_the_remaining_ceilings_are_one_policy_across_records_and_screens"


def read(rel: str) -> str:
    with open(ROOT / rel, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(rel: str, text: str) -> None:
    with open(ROOT / rel, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def _replace_once(rel: str, needle: str, replacement: str) -> None:
    old = read(rel)
    assert old.count(needle) == 1, "%r appears %d times in %s" % (needle, old.count(needle), rel)
    write(rel, old.replace(needle, replacement))


def _replace_in_blob(rel: str, marker: str, old_needle: str, replacement: str) -> None:
    """Replace the first ``old_needle`` after ``marker`` -- a scope pin for repeated text."""
    text = read(rel)
    i = text.index(marker)
    j = text.index(old_needle, i)
    write(rel, text[:j] + replacement + text[j + len(old_needle):])


# --------------------------------------------------------------------------- controller arms

def arm_drop_valid_from_login() -> dict:
    """Remove @Valid from login's body -- the route loses its validating record."""
    _replace_once(CONTROLLER, "@RequestBody @Valid LoginRequest request", "@RequestBody LoginRequest request")
    return {
        "name": "drop @Valid from the login body",
        "predicted_red": [T1],
        "description": (
            "route_body_table needs `@RequestBody @Valid <Record>` per segment, so /login maps "
            "to None; the @Valid census is also short by one, same test"
        ),
    }


def arm_rename_the_logout_path() -> dict:
    """Rename /logout to /sign-out -- the route table drifts."""
    _replace_once(CONTROLLER, '@PostMapping("/logout")', '@PostMapping("/sign-out")')
    return {
        "name": "rename the logout path to /sign-out",
        "predicted_red": [T1],
        "description": "the table gains /sign-out and loses /logout; no other test reads paths",
    }


def arm_plant_a_seventh_post_route() -> dict:
    """Stack a seventh @PostMapping with no body above /register."""
    _replace_once(
        CONTROLLER,
        '@PostMapping("/register")',
        '@PostMapping("/remember")\n    @PostMapping("/register")',
    )
    return {
        "name": "plant a seventh @PostMapping with no body",
        "predicted_red": [T1],
        "description": (
            "the /remember segment binds no @RequestBody @Valid, so it enters the table as "
            "None and the table equality fails; the @PostMapping count is 7 too"
        ),
    }


def arm_bind_login_to_the_register_record() -> dict:
    """Point login's body at RegisterRequest -- the route maps to the wrong record."""
    _replace_once(CONTROLLER, "@RequestBody @Valid LoginRequest request", "@RequestBody @Valid RegisterRequest request")
    return {
        "name": "bind login's body to RegisterRequest",
        "predicted_red": [T1],
        "description": (
            "the table still has six routes and six @Valid, but /login maps to RegisterRequest; "
            "only the table equality sees the swap"
        ),
    }


# --------------------------------------------------------------------------- record arms

def arm_rename_register_password_field() -> dict:
    """Rename RegisterRequest.password -> passcode."""
    _replace_once(REGISTER_DTO, "String password", "String passcode")
    return {
        "name": "rename RegisterRequest.password to passcode",
        "predicted_red": [T2, T3, T4],
        "description": (
            "T2 reads the field list; T3 loses the guard line; T4 calls "
            "password_bounds(REGISTER_DTO, 'password') whose regex now finds no @Size line. "
            "T11 no longer reads the record, so it stays green"
        ),
    }


def arm_add_a_field_to_register_record() -> dict:
    """Add an unbound-for-fourth field to RegisterRequest -- the wire widens silently."""
    _replace_once(
        REGISTER_DTO,
        "String displayName",
        "String displayName,\n        @Size(max = 4) String probe",
    )
    return {
        "name": "add a fourth field to RegisterRequest",
        "predicted_red": [T2],
        "description": (
            "the three guard lines survive (T3 green); only the field-list equality sees the "
            "new name"
        ),
    }


def arm_widen_login_password_ceiling() -> dict:
    """Widen LoginRequest.password's @Size max 72 -> 120."""
    _replace_once(LOGIN_DTO, "@Size(max = 72) String password", "@Size(max = 120) String password")
    return {
        "name": "widen login's password ceiling to 120",
        "predicted_red": [T3, T4],
        "description": "T3 loses the guard line; T4 reads login == (None, 120) != (None, 72)",
    }


def arm_widen_refresh_token_ceiling() -> dict:
    """Widen RefreshTokenRequest.refreshToken's @Size max 512 -> 256."""
    _replace_once(TOKEN_DTO, "@Size(max = 512) String refreshToken", "@Size(max = 256) String refreshToken")
    return {
        "name": "widen the refresh token ceiling to 256",
        "predicted_red": [T3],
        "description": "only the refresh record's guard line is pinned; no bounds policy reads it",
    }


def arm_rename_reset_new_password_field() -> dict:
    """Rename ResetPasswordRequest.newPassword -> password."""
    _replace_once(RESET_DTO, "String newPassword", "String password")
    return {
        "name": "rename ResetPasswordRequest.newPassword to password",
        "predicted_red": [T2, T3, T4, T8],
        "description": (
            "T2 field list; T3 guard line; T4 password_bounds(RESET_DTO,'newPassword') raises; "
            "T8's equality pairs the still-sending {token,newPassword} body with a record that "
            "now binds {token,password}"
        ),
    }


def arm_strip_email_guard_from_forgot() -> dict:
    """Drop @Email from ForgotPasswordRequest -- shape checks stop at @NotBlank."""
    _replace_once(
        FORGOT_DTO,
        "@NotBlank @Email @Size(max = 255) String email",
        "@NotBlank @Size(max = 255) String email",
    )
    return {
        "name": "strip @Email from the forgot-password record",
        "predicted_red": [T3],
        "description": "field list unchanged; only the exact guard line is pinned",
    }


def arm_lower_register_minimum() -> dict:
    """Lower RegisterRequest.password's minimum 8 -> 6."""
    _replace_once(REGISTER_DTO, "@Size(min = 8, max = 72) String password", "@Size(min = 6, max = 72) String password")
    return {
        "name": "lower the register minimum to 6",
        "predicted_red": [T3, T4],
        "description": (
            "T3 guard line; T4 register (6,72) fails the (8,72) pin and reset==register. "
            "T11 reads only the form, so the record drifting stays green there"
        ),
    }


# --------------------------------------------------------------------------- payload-type arms

def arm_rename_login_payload_password() -> dict:
    """Rename LoginPayload.password -> passcode -- the parked register/login pair drifts."""
    _replace_once(CLIENT, "password: string;", "passcode: string;")
    return {
        "name": "rename LoginPayload.password to passcode",
        "predicted_red": [T5],
        "description": (
            "body: payload is verbatim, so no literal body changes; only the interface key "
            "list (T5) sees it -- this is the pair the vitest gate parks"
        ),
    }


def arm_drop_display_name_from_register_payload() -> dict:
    """Drop RegisterPayload's own member -- the interface stops covering displayName."""
    _replace_once(CLIENT, "  displayName: string;", "")
    return {
        "name": "drop RegisterPayload's displayName member",
        "predicted_red": [T5],
        "description": (
            "RegisterPayload's own members go empty; the union check loses displayName while "
            "the screens still send it (T6 reads the screens, which are untouched)"
        ),
    }


def arm_retype_the_register_signature() -> dict:
    """Take register()'s typed argument back to LoginPayload."""
    _replace_once(
        CLIENT,
        "async register(payload: RegisterPayload): Promise<User> {",
        "async register(payload: LoginPayload): Promise<User> {",
    )
    return {
        "name": "retype authApi.register's parameter to LoginPayload",
        "predicted_red": [T5],
        "description": (
            "the interface blocks stay intact, so the first three T5 asserts pass; the "
            "signature pin is what fails"
        ),
    }


# --------------------------------------------------------------------------- screen arms

def arm_rename_the_register_screen_name_key() -> dict:
    """Rename the register screen's displayName key -> name."""
    _replace_once(CREDENTIALS_FORM, "displayName: values.displayName", "name: values.displayName")
    return {
        "name": "rename the register screen's displayName key to name",
        "predicted_red": [T6],
        "description": (
            "login.mutate is untouched (T6's first assert passes); the register key set loses "
            "displayName and gains name"
        ),
    }


def arm_rename_the_forgot_screen_key() -> dict:
    """Rename the forgot screen's email key -> mail."""
    _replace_once(FORGOT_FORM, "{ email: address }", "{ mail: address }")
    return {
        "name": "rename the forgot screen's email key to mail",
        "predicted_red": [T7],
        "description": "the reset screen is untouched; only the forgot key list fails",
    }


# --------------------------------------------------------------------------- writer arms

def arm_drop_new_password_from_reset_wrapper() -> dict:
    """Drop newPassword from resetPassword's body -- equality side only."""
    _replace_once(CLIENT, ", newPassword: payload.newPassword", "")
    return {
        "name": "drop newPassword from the reset wrapper's body",
        "predicted_red": [T8],
        "description": (
            "the sent keys {token} stay a subset of the record's {token,newPassword}, so the "
            "vitest subset rule is blind; the equality pair here reds"
        ),
    }


def arm_rename_logout_body_key() -> dict:
    """Send refresh_token instead of refreshToken from logout."""
    _replace_once(CLIENT, "body: { refreshToken },", "body: { refresh_token: refreshToken },")
    return {
        "name": "rename the logout body key to refresh_token",
        "predicted_red": [T8],
        "description": (
            "the store read and runRefresh are untouched, so T9 stays green; only the "
            "logout-vs-record equality reds"
        ),
    }


def arm_rename_run_refresh_body_key() -> dict:
    """Send token instead of refreshToken from runRefresh's raw fetch."""
    _replace_once(CLIENT, "body: JSON.stringify({ refreshToken }),", "body: JSON.stringify({ token }),")
    return {
        "name": "rename runRefresh's body key to token",
        "predicted_red": [T8, T9],
        "description": "T8 parses the stringified body; T9 pins the same line inside runRefresh",
    }


def arm_flip_forgot_password_bearer_optout() -> dict:
    """Turn forgotPassword's auth: false into auth: true."""
    _replace_in_blob(CLIENT, "endpoints.auth.forgotPassword, ", "auth: false", "auth: true")
    return {
        "name": "attach the bearer to forgotPassword (auth: false -> true)",
        "predicted_red": [T10],
        "description": (
            "the authApi object's opt-out count drops to 3 and the per-member check fails on "
            "forgotPassword; nothing else reads this flag"
        ),
    }


def arm_append_a_second_refresh_reference() -> dict:
    """Append a probe reference to endpoints.auth.refresh -- the census saturates."""
    write(CLIENT, read(CLIENT) + "\nexport const _witnessProbeRefresh = endpoints.auth.refresh;\n")
    return {
        "name": "append a second endpoints.auth.refresh reference",
        "predicted_red": [T9],
        "description": "the app-wide census now counts two hits; everything else reads other text",
    }


# --------------------------------------------------------------------------- hook / constants arms

def arm_crosswire_the_reset_hook() -> dict:
    """Point useResetPassword's mutationFn at forgotPassword."""
    _replace_once(HOOKS, "mutationFn: authApi.resetPassword,", "mutationFn: authApi.forgotPassword,")
    return {
        "name": "cross-wire the reset hook to forgotPassword",
        "predicted_red": [T12],
        "description": (
            "the five exact hook lines are each present-checked; resetPassword's line is gone"
        ),
    }


def arm_change_the_recovery_ceiling_constant() -> dict:
    """Change PASSWORD_MAX_LENGTH 72 -> 64 in the recovery module."""
    _replace_once(RECOVERY, "export const PASSWORD_MAX_LENGTH = 72;", "export const PASSWORD_MAX_LENGTH = 64;")
    return {
        "name": "change the recovery ceiling constant to 64",
        "predicted_red": [T4],
        "description": (
            "passwordIssue's branch text (.length > PASSWORD_MAX_LENGTH) is a variable read "
            "and survives; only the declared value is pinned"
        ),
    }


def arm_revert_the_shared_password_guard() -> dict:
    """Revert baseFields' password to the old inline minimum -- the #214 undo."""
    _replace_once(
        CREDENTIALS_FORM,
        "validate: passwordIssue,",
        'validate: (v) => (!v ? "Password is required" : v.length < 8 ? "At least 8 characters" : undefined),',
    )
    return {
        "name": "revert the shared password guard to an inline threshold",
        "predicted_red": [T11],
        "description": (
            "baseFields' entry leaves passwordIssue and register inherits the change, so the "
            "screens' guard test fails on the inline v.length check and on the shared-validator "
            "count; the mutate keys are untouched (T6 green)"
        ),
    }


# --------------------------------------------------------------------------- ceiling-mirror arms (#215)

def arm_widen_register_display_name_ceiling() -> dict:
    """Widen RegisterRequest.displayName's @Size max 120 -> 240."""
    _replace_once(
        REGISTER_DTO,
        "@NotBlank @Size(max = 120) String displayName",
        "@NotBlank @Size(max = 240) String displayName",
    )
    return {
        "name": "widen the register displayName ceiling to 240",
        "predicted_red": [T3, T13],
        "description": (
            "T3 loses the exact guard line; T13 reads displayName's bounds and compares them "
            "to DISPLAY_NAME_MAX_LENGTH = 120"
        ),
    }


def arm_drop_the_display_name_mirror_from_the_form() -> dict:
    """Swap the register name field back to its old inline non-empty check."""
    _replace_once(
        CREDENTIALS_FORM,
        "validate: displayNameIssue,",
        'validate: (v) => (!v.trim() ? "Name is required" : undefined),',
    )
    return {
        "name": "revert the register name field to an inline non-empty check",
        "predicted_red": [T13],
        "description": (
            "T13 counts `validate: displayNameIssue,` (now 0); T11's pins survive: the revert "
            "carries no `v.length`, and the password entry, import and override are untouched"
        ),
    }


def arm_widen_the_email_ceiling_constant() -> dict:
    """Widen EMAIL_MAX_LENGTH 255 -> 300 in the recovery module."""
    _replace_once(RECOVERY, "export const EMAIL_MAX_LENGTH = 255;", "export const EMAIL_MAX_LENGTH = 300;")
    return {
        "name": "widen the shared email ceiling to 300",
        "predicted_red": [T13],
        "description": "only T13 pins the declared value against the three records' 255",
    }


def arm_widen_the_token_ceiling_constant() -> dict:
    """Widen RESET_TOKEN_MAX_LENGTH 512 -> 1024 in the recovery module."""
    _replace_once(
        RECOVERY,
        "export const RESET_TOKEN_MAX_LENGTH = 512;",
        "export const RESET_TOKEN_MAX_LENGTH = 1024;",
    )
    return {
        "name": "widen the shared token ceiling to 1024",
        "predicted_red": [T13],
        "description": (
            "only T13 reads it; the enforcing branch is a variable read (EMAIL pattern) and "
            "survives"
        ),
    }


ARMS = [
    arm_drop_valid_from_login,
    arm_rename_the_logout_path,
    arm_plant_a_seventh_post_route,
    arm_bind_login_to_the_register_record,
    arm_rename_register_password_field,
    arm_add_a_field_to_register_record,
    arm_widen_login_password_ceiling,
    arm_widen_refresh_token_ceiling,
    arm_rename_reset_new_password_field,
    arm_strip_email_guard_from_forgot,
    arm_lower_register_minimum,
    arm_rename_login_payload_password,
    arm_drop_display_name_from_register_payload,
    arm_retype_the_register_signature,
    arm_rename_the_register_screen_name_key,
    arm_rename_the_forgot_screen_key,
    arm_drop_new_password_from_reset_wrapper,
    arm_rename_logout_body_key,
    arm_rename_run_refresh_body_key,
    arm_flip_forgot_password_bearer_optout,
    arm_append_a_second_refresh_reference,
    arm_crosswire_the_reset_hook,
    arm_change_the_recovery_ceiling_constant,
    arm_revert_the_shared_password_guard,
    arm_widen_register_display_name_ceiling,
    arm_drop_the_display_name_mirror_from_the_form,
    arm_widen_the_email_ceiling_constant,
    arm_widen_the_token_ceiling_constant,
]
