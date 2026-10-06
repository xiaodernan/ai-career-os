"""Mutation arms for the MeController request-contract gate (#213).

Each arm mutates one clause of the contract and predicts which tests should go red.
All predictions are frozen before running, so a mismatch is itself evidence.

Read/write are byte-faithful (``newline=""``): the working tree is shared with other
sessions, so an arm must be undone by re-writing the captured bytes, never by
``git checkout``. Needles are single-line except where ``_delete_lines`` derives the
file's own EOL, so a CRLF working copy cannot silently no-op an arm.

Test-name shorthand used in the predictions (gate order):
  T1  canonical route: one base prefix, bare GET + bare PATCH, no other verb
  T2  GET asks for no body and answers MeResponse
  T3  PATCH binds @RequestBody @Valid UpdateMeRequest and answers MeResponse
  T4  both spellings forward identically to one UserService
  T5  UpdateMeRequest validated at exactly two sites, one per spelling
  T6  alias story: registry reason + docstring + client map + both prefixes agree
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ME_CTRL = "backend/src/main/java/com/careeros/auth/web/MeController.java"
USER_CTRL = "backend/src/main/java/com/careeros/user/web/UserController.java"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"
VITEST = "frontend/src/lib/api/endpoints.test.ts"

T1 = "test_the_canonical_route_is_one_base_prefix_with_exactly_a_get_and_a_patch"
T2 = "test_the_get_handler_asks_for_no_body_and_answers_the_me_record"
T3 = "test_the_patch_handler_binds_the_update_record_for_validation"
T4 = "test_the_two_spellings_forward_identically_to_one_service"
T5 = "test_the_update_record_is_bound_at_exactly_two_sites_one_per_spelling"
T6 = "test_the_alias_story_agrees_across_registry_docstring_and_client_map"


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


def _delete_lines(rel: str, lines: list) -> None:
    """Remove a contiguous block of whole lines, joined with the file's own EOL."""
    text = read(rel)
    nl = "\r\n" if "\r\n" in text else "\n"
    needle = nl.join(lines)
    assert text.count(needle) == 1, (
        "%d-line block appears %d times in %s" % (len(lines), text.count(needle), rel)
    )
    write(rel, text.replace(needle, ""))


# --------------------------------------------------------------------------- canonical-side arms

def arm_flip_the_canonical_patch_to_put() -> dict:
    """Retarget the canonical PATCH as a PUT -- vitest's route table keys patterns, not verbs."""
    _replace_once(ME_CTRL, "@PatchMapping", "@PutMapping")
    return {
        "name": "flip the canonical @PatchMapping to @PutMapping",
        "predicted_red": [T1],
        "description": "the mapping list becomes [(Get,''),(Put,'')] against the pinned two; "
        "the registry entry and every other clause are pattern-level and stay green",
    }


def arm_delete_the_canonical_get_handler() -> dict:
    """Delete the whole GET handler -- the PATCH still keeps the /me pattern alive."""
    _delete_lines(
        ME_CTRL,
        [
            "    @GetMapping",
            "    public MeResponse me(@CurrentUser AuthUser user) {",
            "        return userService.get(user.id());",
            "    }",
        ],
    )
    return {
        "name": "delete the canonical GET handler",
        "predicted_red": [T1, T2, T4],
        "description": "T1 loses the GET mapping; T2's signature pin finds nothing; T4's "
        "forwarded-call list drops the read; T5's census and T6's carriers are untouched",
    }


def arm_drop_valid_from_the_canonical_patch() -> dict:
    """Remove @Valid from the canonical PATCH -- the second binding site loses validation."""
    _replace_once(
        ME_CTRL,
        "@RequestBody @Valid UpdateMeRequest request",
        "@RequestBody UpdateMeRequest request",
    )
    return {
        "name": "drop @Valid from the canonical PATCH binding",
        "predicted_red": [T3, T5],
        "description": "T3's signature string and its one-binding count both miss; T5's census "
        "loses the canonical site; the alias side is untouched",
    }


def arm_repoint_the_canonical_answer_import() -> dict:
    """Re-import the canonical answer from a different class name."""
    _replace_once(
        ME_CTRL,
        "import com.careeros.auth.dto.MeResponse;",
        "import com.careeros.auth.dto.MeView;",
    )
    return {
        "name": "repoint the canonical answer import to MeView",
        "predicted_red": [T2, T4],
        "description": "T2's import pin and T4's shared-FQN pin both miss; the signature text "
        "still says MeResponse, so only the import-level clauses move",
    }


def arm_point_the_canonical_patch_at_the_read_path() -> dict:
    """Make the PATCH forward to userService.get -- a copy-paste shape that drops the write."""
    _replace_once(
        ME_CTRL,
        "        return userService.update(user.id(), request);",
        "        return userService.get(user.id());",
    )
    return {
        "name": "point the canonical PATCH at userService.get",
        "predicted_red": [T3, T4],
        "description": "T3's block no longer writes through update; T4's list becomes [get, "
        "get] against the pinned pair",
    }


def arm_reorder_the_update_arguments() -> dict:
    """Swap the forwarded arguments -- same call, reversed roles."""
    _replace_once(
        ME_CTRL,
        "userService.update(user.id(), request)",
        "userService.update(request, user.id())",
    )
    return {
        "name": "reorder the forwarded update arguments",
        "predicted_red": [T3, T4],
        "description": "the statement pin in T3 and the list equality in T4 both read the exact "
        "argument shape",
    }


def arm_inject_a_different_service_type() -> dict:
    """Swap the injected service type -- the pair stops sharing one implementation."""
    _replace_once(ME_CTRL, "private final UserService userService;", "private final UserViewService userService;")
    return {
        "name": "inject a different service type in the canonical controller",
        "predicted_red": [T4],
        "description": "T4's field-type pin is the only clause that reads the injected type; "
        "the call sites still spell `userService.`",
    }


def arm_give_the_canonical_get_a_request_body() -> dict:
    """Give the GET a validated request body -- a read that now demands a payload."""
    _replace_once(
        ME_CTRL,
        "public MeResponse me(@CurrentUser AuthUser user) {",
        "public MeResponse me(@CurrentUser AuthUser user, "
        "@RequestBody @Valid UpdateMeRequest request) {",
    )
    return {
        "name": "give the canonical GET a @RequestBody @Valid UpdateMeRequest",
        "predicted_red": [T2, T3, T5],
        "description": "T2's signature pin is gone; T3's one-binding count becomes two; T5's "
        "census reads {canonical: 2, alias: 1}",
    }


def arm_rename_the_canonical_base_prefix() -> dict:
    """Move the canonical base route off /me."""
    _replace_once(ME_CTRL, '@RequestMapping("/api/v1/me")', '@RequestMapping("/api/v1/account")')
    return {
        "name": "rename the canonical base prefix to /api/v1/account",
        "predicted_red": [T1, T6],
        "description": "T1's prefix pin misses; T6's derived canonical route no longer equals "
        "the registry key -- and vitest's never-referenced census reddens on this one too",
    }


def arm_rename_the_canonical_update_path() -> dict:
    """Give the canonical PATCH an explicit path -- the surface is no longer just /me."""
    _replace_once(ME_CTRL, "@PatchMapping", '@PatchMapping("/update")')
    return {
        "name": "give the canonical @PatchMapping a /update path",
        "predicted_red": [T1],
        "description": "the mapping list becomes [(Get,''),(Patch,'/update')]; the prefix-derived "
        "registry key is untouched",
    }


# --------------------------------------------------------------------------- alias-side and carrier arms

def arm_swap_the_alias_profile_binding() -> dict:
    """Rebind the alias profile route to UpdateMeRequest -- a third validated site of the record."""
    _replace_once(
        USER_CTRL,
        "@RequestBody @Valid UpdateProfileRequest request",
        "@RequestBody @Valid UpdateMeRequest request",
    )
    return {
        "name": "rebind the alias /me/profile PATCH to UpdateMeRequest",
        "predicted_red": [T5],
        "description": "the census reads {canonical: 1, alias: 2}; the alias's /me signatures "
        "and forwarded calls are unchanged",
    }


def arm_drop_valid_from_the_alias_patch() -> dict:
    """Remove @Valid from the alias PATCH -- the pair stops binding the record the same way."""
    _replace_once(
        USER_CTRL,
        "@RequestBody @Valid UpdateMeRequest request",
        "@RequestBody UpdateMeRequest request",
    )
    return {
        "name": "drop @Valid from the alias PATCH binding",
        "predicted_red": [T4, T5],
        "description": "T4's alias signature pin misses and T5's census loses the alias site; "
        "the canonical side is untouched",
    }


def arm_rename_the_client_spelling() -> dict:
    """Point the client map's me at a path neither controller serves."""
    _replace_once(ENDPOINTS, 'me: "/users/me",', 'me: "/users/account",')
    return {
        "name": "rename the client's auth.me value",
        "predicted_red": [T6],
        "description": "the client value no longer equals the alias's derived route; every "
        "controller-side clause is untouched",
    }


def arm_reword_the_registry_reason() -> dict:
    """Strip the controller's name from the never-referenced reason."""
    _replace_once(
        VITEST,
        '"/me": "MeController\'s alias of /users/me;',
        '"/me": "an alias of /users/me;',
    )
    return {
        "name": "reword the registry reason so it stops naming MeController",
        "predicted_red": [T6],
        "description": "the reason still names the alias path, so only the subject-identity "
        "clause moves; vitest's own test only checks non-blank",
    }


def arm_reword_the_alias_docstring_targets() -> dict:
    """Make the alias docstring spell the canonical routes as its own."""
    _replace_once(
        USER_CTRL,
        "/api/v1/users/me + /api/v1/users/me/profile.",
        "/api/v1/me + /api/v1/me/profile.",
    )
    return {
        "name": "reword the alias docstring to spell the canonical routes",
        "predicted_red": [T6],
        "description": "the docstring no longer contains either derived alias spelling, and it "
        "now contains the canonical one",
    }


ARMS = [
    arm_flip_the_canonical_patch_to_put,
    arm_delete_the_canonical_get_handler,
    arm_drop_valid_from_the_canonical_patch,
    arm_repoint_the_canonical_answer_import,
    arm_point_the_canonical_patch_at_the_read_path,
    arm_reorder_the_update_arguments,
    arm_inject_a_different_service_type,
    arm_give_the_canonical_get_a_request_body,
    arm_rename_the_canonical_base_prefix,
    arm_rename_the_canonical_update_path,
    arm_swap_the_alias_profile_binding,
    arm_drop_valid_from_the_alias_patch,
    arm_rename_the_client_spelling,
    arm_reword_the_registry_reason,
    arm_reword_the_alias_docstring_targets,
]
