"""Mutation arms for the User (/me) controller request contract gate.

Each arm mutates one clause of the contract and predicts which tests should go red.
All predictions are frozen before running, so a mismatch is itself evidence.

Read/write are byte-faithful (``newline=""``): the working tree is shared with other
sessions, so an arm must be undone by re-writing the captured bytes, never by
``git checkout``.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/user/web/UserController.java"
ME_DTO = "backend/src/main/java/com/careeros/auth/dto/UpdateMeRequest.java"
PROFILE_DTO = "backend/src/main/java/com/careeros/user/dto/UpdateProfileRequest.java"
ACTIONS = "frontend/src/lib/hooks/actions.ts"
SETTINGS = "frontend/src/app/(app)/settings/page.tsx"
CARDS = "frontend/src/components/settings/profile-cards.tsx"
TARGETS = "frontend/src/lib/profile-targets.ts"


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


def _scoped_replace(src: str, record_name: str, old: str, new: str) -> str:
    """Replace ``old`` with ``new`` only inside ``record Name(...)``'s header."""
    m = re.search(r"record\s+" + record_name + r"\s*\((.*?)\)\s*\{", src, re.DOTALL)
    assert m, "%s record not found" % record_name
    body = m.group(1)
    assert body.count(old) == 1, "%r appears %d times inside %s" % (old, body.count(old), record_name)
    return src[: m.start(1)] + body.replace(old, new) + src[m.end(1):]


# --------------------------------------------------------------------------- Arms

def arm_rename_display_name_to_name_in_update_me() -> dict:
    """Rename displayName->name in UpdateMeRequest -- census, guard and binding tests fail."""
    write(ME_DTO, _scoped_replace(read(ME_DTO), "UpdateMeRequest", "String displayName", "String name"))
    return {
        "name": "rename displayName to name in UpdateMeRequest",
        "predicted_red": [
            "test_the_update_me_request_dto_declares_ten_names",
            "test_the_display_name_guard_mirrors_the_settings_page",
            "test_the_unbound_hook_type_keys_stay_unbound_while_the_sent_key_is_bound",
        ],
        "description": "the settings page still sends displayName; guard finds no displayName line",
    }


def arm_remove_min_from_display_name_guard() -> dict:
    """Drop the min=1 half of the displayName guard -- the mirror test fails."""
    _replace_once(ME_DTO, '@Size(min = 1, max = 120) String displayName', '@Size(max = 120) String displayName')
    return {
        "name": "remove min = 1 from the displayName guard",
        "predicted_red": ["test_the_display_name_guard_mirrors_the_settings_page"],
        "description": "census unaffected (annotations are stripped); the guard needle disappears",
    }


def arm_lower_profile_years_cap_to_fifty() -> dict:
    """Change UpdateProfileRequest's years cap to 50 -- the bounds mirror test fails."""
    _replace_once(PROFILE_DTO, '@DecimalMax("60")', '@DecimalMax("50")')
    return {
        "name": "change UpdateProfileRequest years cap to 50",
        "predicted_red": ["test_the_years_experience_bounds_mirror_the_profile_cards"],
        "description": "UpdateMeRequest's copy stays 60, so only the profile iteration fails",
    }


def arm_remove_valid_from_update_me_binding() -> dict:
    """Remove @Valid from PATCH /me -- the controller test fails."""
    _replace_once(CONTROLLER, "@RequestBody @Valid UpdateMeRequest", "@RequestBody UpdateMeRequest")
    return {
        "name": "remove @Valid from the UpdateMeRequest binding",
        "predicted_red": ["test_the_controller_binds_both_patch_routes_with_valid"],
        "description": "binding count drops from 1 to 0",
    }


def arm_rename_headline_to_title_in_update_profile() -> dict:
    """Rename headline->title in UpdateProfileRequest -- census and both form tests fail."""
    write(PROFILE_DTO, _scoped_replace(read(PROFILE_DTO), "UpdateProfileRequest", "String headline", "String title"))
    return {
        "name": "rename headline to title in UpdateProfileRequest",
        "predicted_red": [
            "test_the_update_profile_request_dto_declares_nine_names",
            "test_the_career_profile_form_sends_the_six_scalar_fields",
            "test_the_maps_form_sends_the_three_map_fields_by_name",
            "test_the_scalar_text_caps_are_one_policy_across_records_and_screen",
        ],
        "description": "form still sends headline; subset and partition assertions both lose it, "
        "and case 13's field lookup finds no headline line to read a bound from",
    }


def arm_change_settings_max_name() -> dict:
    """Change the settings page's MAX_NAME to 100 -- the mirror test fails."""
    _replace_once(SETTINGS, "const MAX_NAME = 120;", "const MAX_NAME = 100;")
    return {
        "name": "change settings MAX_NAME to 100",
        "predicted_red": ["test_the_display_name_guard_mirrors_the_settings_page"],
        "description": "the UI mirror no longer agrees with @Size(max = 120)",
    }


def arm_change_cards_max_years() -> dict:
    """Change the profile cards' MAX_YEARS to 50 -- the bounds mirror test fails."""
    _replace_once(CARDS, "const MAX_YEARS = 60;", "const MAX_YEARS = 50;")
    return {
        "name": "change profile cards MAX_YEARS to 50",
        "predicted_red": ["test_the_years_experience_bounds_mirror_the_profile_cards"],
        "description": "the UI mirror no longer agrees with @DecimalMax(60)",
    }


def arm_repoint_details_hook_to_me() -> dict:
    """Point useUpdateProfileDetails at /users/me -- the hook wiring test fails."""
    _replace_once(ACTIONS, "api.update<unknown>(endpoints.auth.profile, patch)", "api.update<unknown>(endpoints.auth.me, patch)")
    return {
        "name": "re-point useUpdateProfileDetails to endpoints.auth.me",
        "predicted_red": ["test_the_profile_hooks_patch_their_mapped_endpoints"],
        "description": "the career profile PATCH would be sent to the account route",
    }


def arm_rename_form_years_key() -> dict:
    """Send the form's years under key years -- the scalar-keys test and the partition fail."""
    _replace_once(CARDS, "yearsExperience: parsedYears,", "years: parsedYears,")
    return {
        "name": "rename the form's yearsExperience key to years",
        "predicted_red": [
            "test_the_career_profile_form_sends_the_six_scalar_fields",
            "test_the_maps_form_sends_the_three_map_fields_by_name",
        ],
        "description": "unknown key would be dropped by Jackson; besides the per-form key list, "
        "the maps test's partition assertion (form keys + map names vs DTO fields) also reads "
        "the form keys, so yearsExperience drops out of the union there",
    }


def arm_rename_maps_section_links() -> dict:
    """Rename the links map section -- the maps-by-name test fails."""
    _replace_once(CARDS, '{ name: "links",', '{ name: "urls",')
    return {
        "name": "rename the maps form's links section to urls",
        "predicted_red": ["test_the_maps_form_sends_the_three_map_fields_by_name"],
        "description": "payload key urls is bound by no DTO field",
    }


def arm_rename_settings_sent_key() -> dict:
    """Send the settings page's edit under key name -- the only-key test fails."""
    _replace_once(SETTINGS, "{ displayName: displayName.trim() }", "{ name: displayName.trim() }")
    return {
        "name": "rename the settings page's sent key to name",
        "predicted_red": ["test_the_settings_page_sends_only_display_name_through_use_update_profile"],
        "description": "UpdateMeRequest binds displayName; name would be dropped",
    }


def arm_change_me_failure_message() -> dict:
    """Change useUpdateProfile's failure toast -- the announcement test fails."""
    _replace_once(ACTIONS, '"Couldn\'t save your profile."', '"Couldn\'t save your account."')
    return {
        "name": "change the useUpdateProfile failure message",
        "predicted_red": ["test_the_profile_mutations_announce_their_failures"],
        "description": "the shipped sentence changed",
    }


def arm_drop_email_from_hook_type() -> dict:
    """Drop email from the hook's patch type -- the type-keys test fails."""
    _replace_once(ACTIONS, "email?: string; ", "")
    return {
        "name": "remove email from useUpdateProfile's patch type",
        "predicted_red": [
            "test_the_unbound_hook_type_keys_stay_unbound_while_the_sent_key_is_bound"
        ],
        "description": "the declared type keys no longer match the pinned trio",
    }


def arm_add_email_to_update_me() -> dict:
    """Add String email to UpdateMeRequest -- census and the unbound-keys test fail."""
    _replace_once(ME_DTO, "String displayName,", "String displayName, String email,")
    return {
        "name": "add email as a bound field of UpdateMeRequest",
        "predicted_red": [
            "test_the_update_me_request_dto_declares_ten_names",
            "test_the_unbound_hook_type_keys_stay_unbound_while_the_sent_key_is_bound",
        ],
        "description": "email becomes bound, so the 'email not in fields' pin must move",
    }


def arm_change_me_profile_route() -> dict:
    """Change the PATCH route path -- the controller test fails."""
    _replace_once(CONTROLLER, '@PatchMapping("/me/profile")', '@PatchMapping("/me/profiles")')
    return {
        "name": "change PATCH /me/profile to /me/profiles",
        "predicted_red": ["test_the_controller_binds_both_patch_routes_with_valid"],
        "description": "the client map still points at /users/me/profile",
    }


# --------------------------------------------------------- #216: the two target lists

def arm_widen_profile_target_roles_item_to_160() -> dict:
    """Widen UpdateProfileRequest's targetRoles item ceiling -- the one-policy test fails."""
    write(PROFILE_DTO, _scoped_replace(
        read(PROFILE_DTO), "UpdateProfileRequest",
        "@Size(max = 80) String> targetRoles", "@Size(max = 160) String> targetRoles"))
    return {
        "name": "widen UpdateProfileRequest targetRoles item ceiling to 160",
        "predicted_red": ["test_the_target_list_bounds_are_one_policy_across_records_and_screen"],
        "description": "the module constant 80 and this record would disagree; no other case "
        "reads this bound (the name census strips annotations)",
    }


def arm_widen_me_target_locations_count_to_30() -> dict:
    """Widen UpdateMeRequest's targetLocations item-count ceiling -- the one-policy test fails."""
    write(ME_DTO, _scoped_replace(
        read(ME_DTO), "UpdateMeRequest",
        "@Size(max = 20) List<@Size(max = 120) String> targetLocations",
        "@Size(max = 30) List<@Size(max = 120) String> targetLocations"))
    return {
        "name": "widen UpdateMeRequest targetLocations count ceiling to 30",
        "predicted_red": ["test_the_target_list_bounds_are_one_policy_across_records_and_screen"],
        "description": "UpdateProfileRequest's copy stays 20, so only the me_record iteration fails",
    }


def arm_widen_module_roles_item_to_160() -> dict:
    """Widen the module's TARGET_ROLES_MAX_ITEM declaration -- the one-policy test fails."""
    _replace_once(TARGETS, "export const TARGET_ROLES_MAX_ITEM = 80;",
                  "export const TARGET_ROLES_MAX_ITEM = 160;")
    return {
        "name": "widen profile-targets TARGET_ROLES_MAX_ITEM to 160",
        "predicted_red": ["test_the_target_list_bounds_are_one_policy_across_records_and_screen"],
        "description": "the pinned declaration line disappears; the branch line below it still "
        "reads the (renamed-value) constant by name, so only the declaration assert fires",
    }


def arm_flip_module_roles_count_boundary() -> dict:
    """Make the module refuse a list AT the count ceiling -- the one-policy test fails."""
    _replace_once(TARGETS, "if (items.length > TARGET_ROLES_MAX_COUNT) {",
                  "if (items.length >= TARGET_ROLES_MAX_COUNT) {")
    return {
        "name": "flip the module roles-count branch from > to >=",
        "predicted_red": ["test_the_target_list_bounds_are_one_policy_across_records_and_screen"],
        "description": "the exact branch line is pinned; the constants loop above is untouched",
    }


def arm_revert_saveable_to_years_only() -> dict:
    """Drop the two list guards from the save gate -- the one-policy test fails."""
    _replace_once(CARDS, "const saveable = yearsValid && !rolesProblem && !locationsProblem;",
                  "const saveable = yearsValid;")
    return {
        "name": "revert the save gate to yearsValid alone",
        "predicted_red": ["test_the_target_list_bounds_are_one_policy_across_records_and_screen"],
        "description": "MAX_YEARS and the alerts stay, so only the save-gate assert fires",
    }


def arm_drop_roles_alert_render() -> dict:
    """Stop rendering the roles guard's sentence -- the one-policy test fails."""
    _replace_once(CARDS, "{rolesProblem && (", "{false && (")
    return {
        "name": "drop the roles problem alert render",
        "predicted_red": ["test_the_target_list_bounds_are_one_policy_across_records_and_screen"],
        "description": "rolesProblem is still wired into saveable, so only the render-count "
        "assert (1) fails",
    }


# --------------------------------------------------------- #217: the three scalar text caps

def arm_lower_profile_headline_to_120() -> dict:
    """Lower UpdateProfileRequest's headline cap -- the text-caps test fails."""
    write(PROFILE_DTO, _scoped_replace(
        read(PROFILE_DTO), "UpdateProfileRequest",
        "@Size(max = 240) String headline", "@Size(max = 120) String headline"))
    return {
        "name": "lower UpdateProfileRequest headline cap to 120",
        "predicted_red": ["test_the_scalar_text_caps_are_one_policy_across_records_and_screen"],
        "description": "the card's MAX_HEADLINE = 240 and this record would disagree",
    }


def arm_lower_me_summary_to_4000() -> dict:
    """Lower UpdateMeRequest's summary cap -- the text-caps test fails."""
    write(ME_DTO, _scoped_replace(
        read(ME_DTO), "UpdateMeRequest",
        "@Size(max = 5000) String summary", "@Size(max = 4000) String summary"))
    return {
        "name": "lower UpdateMeRequest summary cap to 4000",
        "predicted_red": ["test_the_scalar_text_caps_are_one_policy_across_records_and_screen"],
        "description": "UpdateProfileRequest's copy stays 5000, so only the me_record iteration fails",
    }


def arm_widen_cards_max_location() -> dict:
    """Widen the card's MAX_LOCATION -- the text-caps test fails."""
    _replace_once(CARDS, "const MAX_LOCATION = 120;", "const MAX_LOCATION = 240;")
    return {
        "name": "widen the card's MAX_LOCATION to 240",
        "predicted_red": ["test_the_scalar_text_caps_are_one_policy_across_records_and_screen"],
        "description": "the pinned constant line disappears before either record is read",
    }


def arm_detach_summary_maxlength_from_constant() -> dict:
    """Replace the summary input's maxLength with an inline number -- the text-caps test fails."""
    _replace_once(CARDS, "maxLength={MAX_SUMMARY}", "maxLength={9000}")
    return {
        "name": "detach the summary maxLength from MAX_SUMMARY",
        "predicted_red": ["test_the_scalar_text_caps_are_one_policy_across_records_and_screen"],
        "description": "the attribute no longer names the constant the case holds to the records",
    }


def arm_point_headline_maxlength_at_location() -> dict:
    """Point the headline input's maxLength at MAX_LOCATION -- the text-caps test fails."""
    _replace_once(CARDS, "maxLength={MAX_HEADLINE}", "maxLength={MAX_LOCATION}")
    return {
        "name": "point the headline maxLength at MAX_LOCATION",
        "predicted_red": ["test_the_scalar_text_caps_are_one_policy_across_records_and_screen"],
        "description": "a maxLength attribute exists, but not the one naming MAX_HEADLINE",
    }


ARMS = [
    arm_rename_display_name_to_name_in_update_me,
    arm_remove_min_from_display_name_guard,
    arm_lower_profile_years_cap_to_fifty,
    arm_remove_valid_from_update_me_binding,
    arm_rename_headline_to_title_in_update_profile,
    arm_change_settings_max_name,
    arm_change_cards_max_years,
    arm_repoint_details_hook_to_me,
    arm_rename_form_years_key,
    arm_rename_maps_section_links,
    arm_rename_settings_sent_key,
    arm_change_me_failure_message,
    arm_drop_email_from_hook_type,
    arm_add_email_to_update_me,
    arm_change_me_profile_route,
    arm_widen_profile_target_roles_item_to_160,
    arm_widen_me_target_locations_count_to_30,
    arm_widen_module_roles_item_to_160,
    arm_flip_module_roles_count_boundary,
    arm_revert_saveable_to_years_only,
    arm_drop_roles_alert_render,
    arm_lower_profile_headline_to_120,
    arm_lower_me_summary_to_4000,
    arm_widen_cards_max_location,
    arm_detach_summary_maxlength_from_constant,
    arm_point_headline_maxlength_at_location,
]
