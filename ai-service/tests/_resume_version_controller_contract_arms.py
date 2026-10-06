"""Mutation arms for the resume-version controller request contract gate.

Each arm mutates one clause of the contract and predicts which tests should go red.
All predictions are frozen before running, so a mismatch is itself evidence.

Read/write are byte-faithful (``newline=""``): the working tree is shared with other
sessions, so an arm must be undone by re-writing the captured bytes, never by
``git checkout``.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/resume/web/ResumeVersionController.java"
RESOURCES = "frontend/src/lib/hooks/resources.ts"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"
PAGE = "frontend/src/app/(app)/resumes/[id]/page.tsx"

BINDING = '@RequestParam("resumeId") UUID resumeId'
SINGULAR_MEMBER = "resumeVersion: (id: string) => `/resume-versions/${seg(id)}`,"


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


# --------------------------------------------------------------------------- Arms (controller side)

def arm_rename_the_query_name_to_resume_uuid() -> dict:
    """Rename @RequestParam("resumeId") -> "resume_uuid" -- only the join test fails."""
    _replace_once(CONTROLLER, '@RequestParam("resumeId")', '@RequestParam("resume_uuid")')
    return {
        "name": "rename the Java query literal to resume_uuid",
        "predicted_red": ["test_the_client_key_and_the_controller_name_are_the_same_literal"],
        "description": (
            "the binding still has a name literal, is still required UUID (case 2 green); "
            "the JS side still sends resumeId, so only the join fails"
        ),
    }


def arm_make_the_query_parameter_optional() -> dict:
    """Add required = false to the binding -- case 2's requiredness clause fails."""
    _replace_once(
        CONTROLLER,
        BINDING,
        '@RequestParam(name = "resumeId", required = false) UUID resumeId',
    )
    return {
        "name": "make the resumeId query parameter optional",
        "predicted_red": ["test_the_list_route_binds_resume_id_as_a_required_uuid_query_parameter"],
        "description": (
            "the name literal and the UUID type survive, so only the requiredness clause "
            "of case 2 should red; the join is unaffected"
        ),
    }


def arm_widen_the_query_type_to_string() -> dict:
    """Widen UUID -> String -- case 2's type clause fails."""
    _replace_once(CONTROLLER, BINDING, '@RequestParam("resumeId") String resumeId')
    return {
        "name": "widen the resumeId query type from UUID to String",
        "predicted_red": ["test_the_list_route_binds_resume_id_as_a_required_uuid_query_parameter"],
        "description": "name and requiredness survive; only the UUID type clause fails",
    }


def arm_drop_the_request_param_annotation() -> dict:
    """Remove @RequestParam entirely -- the whole query wire goes dark."""
    _replace_once(CONTROLLER, '@RequestParam("resumeId") UUID resumeId', "UUID resumeId")
    return {
        "name": "drop the @RequestParam annotation",
        "predicted_red": [
            "test_the_versions_controller_carries_two_reads_and_no_request_bodies",
            "test_the_list_route_binds_resume_id_as_a_required_uuid_query_parameter",
            "test_the_client_key_and_the_controller_name_are_the_same_literal",
        ],
        "description": (
            "the census counts one fewer @RequestParam; case 2 and case 3 each lose the "
            "binding their regex asserts on"
        ),
    }


def arm_plant_a_request_body_token() -> dict:
    """Plant an @RequestBody token above list -- the no-bodies census fails."""
    _replace_once(
        CONTROLLER,
        "    public java.util.List<ResumeVersionItem> list(",
        "    @RequestBody\n    public java.util.List<ResumeVersionItem> list(",
    )
    return {
        "name": "plant a @RequestBody annotation on the list route",
        "predicted_red": ["test_the_versions_controller_carries_two_reads_and_no_request_bodies"],
        "description": "only the census test counts @RequestBody; nothing else reads that token",
    }


def arm_swap_the_list_service_arguments() -> dict:
    """Swap listVersions(user.id(), resumeId) -- the forwarding test fails."""
    _replace_once(
        CONTROLLER,
        "resumes.listVersions(user.id(), resumeId)",
        "resumes.listVersions(resumeId, user.id())",
    )
    return {
        "name": "swap the listVersions arguments",
        "predicted_red": ["test_the_controller_forwards_the_user_scope_and_the_bound_ids"],
        "description": "case 7 pins the call as one exact string with the arg order",
    }


def arm_rename_the_path_variable_parameter() -> dict:
    """Rename the @PathVariable parameter id -> resumeId -- case 8's name join fails."""
    _replace_once(CONTROLLER, "@PathVariable UUID id", "@PathVariable UUID resumeId")
    return {
        "name": "rename the path variable parameter to resumeId",
        "predicted_red": ["test_the_item_route_takes_its_path_variable_from_the_template"],
        "description": (
            "the unnamed binding derives its name from the parameter, so the template's "
            "{id} no longer matches; the versionMeta call text is untouched"
        ),
    }


def arm_default_the_query_parameter() -> dict:
    """Add a defaultValue to the binding -- case 2's defaultValue clause fails."""
    _replace_once(
        CONTROLLER,
        BINDING,
        '@RequestParam(name = "resumeId", defaultValue = "none") UUID resumeId',
    )
    return {
        "name": "give the resumeId query parameter a defaultValue",
        "predicted_red": ["test_the_list_route_binds_resume_id_as_a_required_uuid_query_parameter"],
        "description": (
            "required= is not spelled, so only the defaultValue clause of case 2 reds"
        ),
    }


def arm_swap_the_version_meta_arguments() -> dict:
    """Swap versionMeta(user.id(), id) -- the forwarding test fails."""
    _replace_once(
        CONTROLLER,
        "resumes.versionMeta(user.id(), id)",
        "resumes.versionMeta(id, user.id())",
    )
    return {
        "name": "swap the versionMeta arguments",
        "predicted_red": ["test_the_controller_forwards_the_user_scope_and_the_bound_ids"],
        "description": "case 7's second exact-call pin fails",
    }


# --------------------------------------------------------------------------- Arms (client side)

def arm_rename_the_js_query_key() -> dict:
    """Send { resume_id } instead of { resumeId } -- join and shape both fail."""
    _replace_once(RESOURCES, "endpoints.resumeVersions, { resumeId }", "endpoints.resumeVersions, { resume_id }")
    return {
        "name": "rename the JS query key to resume_id",
        "predicted_red": [
            "test_the_client_key_and_the_controller_name_are_the_same_literal",
            "test_the_fetch_call_is_one_get_on_the_versions_member_with_the_shorthand_key",
        ],
        "description": (
            "the join sees the keys differ; the shorthand literal pin no longer matches"
        ),
    }


def arm_restate_the_shorthand_key() -> dict:
    """{ resumeId } -> { resumeId: resumeId } -- wire-equivalent, shape pin fails alone."""
    _replace_once(
        RESOURCES,
        "endpoints.resumeVersions, { resumeId }",
        "endpoints.resumeVersions, { resumeId: resumeId }",
    )
    return {
        "name": "restate the shorthand key as an explicit pair",
        "predicted_red": ["test_the_fetch_call_is_one_get_on_the_versions_member_with_the_shorthand_key"],
        "description": (
            "case 4 is a shape pin, so the wire-equivalent resyntax reds it; the join is "
            "name-based and must stay green"
        ),
    }


def arm_point_the_fetch_at_the_singular_member() -> dict:
    """Fetch through endpoints.resumeVersion (singular) -- join, shape and census fail."""
    _replace_once(
        RESOURCES,
        "endpoints.resumeVersions, { resumeId }",
        "endpoints.resumeVersion, { resumeId }",
    )
    return {
        "name": "point the fetch at the singular resumeVersion member",
        "predicted_red": [
            "test_the_client_key_and_the_controller_name_are_the_same_literal",
            "test_the_fetch_call_is_one_get_on_the_versions_member_with_the_shorthand_key",
            "test_the_single_version_route_ships_with_no_client",
        ],
        "description": (
            "case 3's marker disappears (statement failure); case 4's literal fails; the "
            "singular token now has a second reference, so the census fails too"
        ),
    }


def arm_force_the_versions_query_enabled() -> dict:
    """enabled: Boolean(resumeId) -> enabled: true -- the hook guard test fails."""
    _replace_once(RESOURCES, "enabled: Boolean(resumeId)", "enabled: true")
    return {
        "name": "force the versions query always enabled",
        "predicted_red": ["test_the_versions_hook_is_disabled_until_a_resume_id_exists"],
        "description": "case 5's enabled clause fails; the queryFn line is untouched",
    }


def arm_change_the_hook_query_fn_fallback() -> dict:
    """resumeId! -> resumeId ?? "" in the queryFn -- the hook guard test fails."""
    _replace_once(
        RESOURCES,
        "queryFn: () => fetchResumeVersions(resumeId!)",
        'queryFn: () => fetchResumeVersions(resumeId ?? "")',
    )
    return {
        "name": "give the hook queryFn a null fallback",
        "predicted_red": ["test_the_versions_hook_is_disabled_until_a_resume_id_exists"],
        "description": "case 5's queryFn clause fails; the enabled line is untouched",
    }


def arm_append_a_singular_member_reference() -> dict:
    """Append a reference to endpoints.resumeVersion -- the census test fails."""
    write(
        RESOURCES,
        read(RESOURCES) + "\nexport const _witnessProbeResumeVersion = endpoints.resumeVersion;\n",
    )
    return {
        "name": "append a probe reference to the singular member",
        "predicted_red": ["test_the_single_version_route_ships_with_no_client"],
        "description": "the census now sees two references; everything else reads hook bodies",
    }


def arm_delete_the_single_version_member() -> dict:
    """Delete the singular member line -- the census finds zero references."""
    _replace_once(ENDPOINTS, SINGULAR_MEMBER, "")
    return {
        "name": "delete the singular resumeVersion member",
        "predicted_red": ["test_the_single_version_route_ships_with_no_client"],
        "description": "hits == 0, so the census fails before its location or template asserts",
    }


def arm_repath_the_single_version_template() -> dict:
    """Change the member's template path -- the census's template clause fails."""
    _replace_once(
        ENDPOINTS,
        SINGULAR_MEMBER,
        "resumeVersion: (id: string) => `/version-archive/${seg(id)}`,",
    )
    return {
        "name": "repath the singular member's template",
        "predicted_red": ["test_the_single_version_route_ships_with_no_client"],
        "description": (
            "the token and its location survive, so only the member-template clause fails"
        ),
    }


# --------------------------------------------------------------------------- Arms (panel side)

def arm_detach_the_versions_retry_from_its_query() -> dict:
    """Retry the resume query instead of the versions query -- case 6 fails."""
    _replace_once(
        PAGE,
        "onRetry={() => void versionsQ.refetch()}",
        "onRetry={() => void resume.refetch()}",
    )
    return {
        "name": "retry the wrong query from the versions panel",
        "predicted_red": ["test_the_detail_screen_shows_a_failed_versions_read_and_offers_a_retry"],
        "description": "case 6's retry clause fails",
    }


def arm_branch_the_versions_error_on_the_resume_query() -> dict:
    """Branch the panel's error on resume.isError -- case 6's isError clause fails."""
    _replace_once(PAGE, "versionsQ.isError ? (", "resume.isError ? (")
    return {
        "name": "branch the versions panel on the resume query's error",
        "predicted_red": ["test_the_detail_screen_shows_a_failed_versions_read_and_offers_a_retry"],
        "description": (
            "case 6's isError clause fails; the error= and onRetry= strings still match, "
            "so the test reds at its first assert"
        ),
    }


ARMS = [
    arm_rename_the_query_name_to_resume_uuid,
    arm_make_the_query_parameter_optional,
    arm_widen_the_query_type_to_string,
    arm_drop_the_request_param_annotation,
    arm_plant_a_request_body_token,
    arm_swap_the_list_service_arguments,
    arm_rename_the_path_variable_parameter,
    arm_default_the_query_parameter,
    arm_swap_the_version_meta_arguments,
    arm_rename_the_js_query_key,
    arm_restate_the_shorthand_key,
    arm_point_the_fetch_at_the_singular_member,
    arm_force_the_versions_query_enabled,
    arm_change_the_hook_query_fn_fallback,
    arm_append_a_singular_member_reference,
    arm_delete_the_single_version_member,
    arm_repath_the_single_version_template,
    arm_detach_the_versions_retry_from_its_query,
    arm_branch_the_versions_error_on_the_resume_query,
]
