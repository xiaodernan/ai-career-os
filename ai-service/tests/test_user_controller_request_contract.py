"""The User (/me) controller request: two PATCH endpoints, their DTOs, and what the browser sends.

UserController serves the frontend-facing /me surface. Two entry points carry JSON bodies:

1. ``PATCH /users/me`` -- account update, binds
   ``UpdateMeRequest(displayName, headline, location, summary, yearsExperience, targetRoles,
   targetLocations, links, workAuthorization, preferences)``; all fields optional ("null means
   leave unchanged"), ``displayName`` guarded ``@Size(min = 1, max = 120)``. The frontend calls
   this through ``useUpdateProfile`` in ``actions.ts``; its only caller, the settings page,
   sends ``{ displayName }``. The hook's patch *type* also declares ``email`` and ``avatarUrl``
   -- keys UpdateMeRequest binds neither of, so a caller sending them would be silently
   dropped by the default Jackson setup. No caller sends them today; this gate pins that.

2. ``PATCH /users/me/profile`` -- career profile update, binds
   ``UpdateProfileRequest(headline, summary, location, yearsExperience, targetRoles,
   targetLocations, links, workAuthorization, preferences)``; ``yearsExperience`` guarded
   ``@DecimalMin("0") @DecimalMax("60")``. The frontend calls this through
   ``useUpdateProfileDetails``, whose two callers on the settings page partition the nine
   fields: ``CareerProfileForm`` sends the six scalars, ``CareerProfileMapsCard`` sends the
   three free-form maps (by name, through ``MAP_SECTIONS``).

The settings UI mirrors the server bounds (``MAX_NAME = 120``, ``MAX_YEARS = 60``, and the
three text caps ``MAX_HEADLINE = 240`` / ``MAX_LOCATION = 120`` / ``MAX_SUMMARY = 5000``
enforced through ``maxLength`` attributes), so this gate holds those constants to their
Java guards.

This gate holds the contract at both ends:

- Each DTO declares exactly the expected field names (no extra fields silently accepted).
- Both PATCH routes bind their request types with ``@Valid``.
- The ``@Size``/``@DecimalMin``/``@DecimalMax`` guards and their UI mirrors agree.
- Every key a caller sends is one the bound DTO declares; the union of the two profile
  forms is exactly ``UpdateProfileRequest``'s field list.
- The mutation failure paths are announced (the settings page's handler and ``fail()``).
- Case 12 extends the same bounds join to the two target lists: each record's
  ``@Size(max = 20) List<@Size(max = ...) String>`` pair has a ``profile-targets.ts``
  constant, an enforcing branch, and a screen guard pinned against the form.
- Case 13 closes the three scalar text caps the same way: both records' ``headline`` /
  ``location`` / ``summary`` bounds against the card's constants and the three
  ``maxLength={MAX_*}`` attributes that are the screen's enforcement point.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/user/web/UserController.java"
ME_DTO = "backend/src/main/java/com/careeros/auth/dto/UpdateMeRequest.java"
PROFILE_DTO = "backend/src/main/java/com/careeros/user/dto/UpdateProfileRequest.java"
ACTIONS = "frontend/src/lib/hooks/actions.ts"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"
SETTINGS = "frontend/src/app/(app)/settings/page.tsx"
CARDS = "frontend/src/components/settings/profile-cards.tsx"
# The maps editor's section table moved out of the card file (profile-maps.ts) -- the
# names the maps form sends are declared there now, so the form scan reads both files.
MAPS_TABLE = "frontend/src/lib/profile-maps.ts"
TARGETS = "frontend/src/lib/profile-targets.ts"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


# --------------------------------------------------------------------------- helpers

@lru_cache(maxsize=1)
def controller_source() -> str:
    return read(CONTROLLER)


@lru_cache(maxsize=1)
def me_dto_source() -> str:
    return read(ME_DTO)


@lru_cache(maxsize=1)
def profile_dto_source() -> str:
    return read(PROFILE_DTO)


@lru_cache(maxsize=1)
def actions_source() -> str:
    return read(ACTIONS)


@lru_cache(maxsize=1)
def settings_source() -> str:
    return read(SETTINGS)


@lru_cache(maxsize=1)
def cards_source() -> str:
    """The card file plus the section table its map names now live in."""
    return read(CARDS) + chr(10) + read(MAPS_TABLE)

def record_body(record_name: str, source: str) -> str:
    """Return the raw text between ``record Name(`` and ``) {``, or "" if absent."""
    m = re.search(r"record\s+" + record_name + r"\s*\((.*?)\)\s*\{", source, re.DOTALL)
    return m.group(1) if m else ""


def java_record_fields(record_name: str, source: str) -> list[str]:
    """Return the field names declared inside ``record RecordName(...)`` in Java source.

    Annotations are stripped first, then generics (``List<@Size(max = 80) String>`` and
    ``Map<String, Object>`` both collapse), so remaining commas are field separators.
    """
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


def ts_call_bodies(fn_name: str, source: str) -> list[str]:
    """Return the text of every top-level ``export function fn_name(...) { ... }`` block."""
    blocks = []
    for m in re.finditer(r"export function\s+" + fn_name + r"\s*\([^)]*\)\s*\{", source):
        start = m.end() - 1  # position of the opening brace
        depth = 0
        i = start
        while i < len(source):
            ch = source[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(source[start:i + 1])
                    break
            i += 1
    return blocks


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
    """Property names of an object literal, including shorthand entries."""
    inner = block[1:-1]
    return re.findall(r"(?:^|,)\s*([A-Za-z_$][\w$]*)\s*(?=:|,)", inner)


def guarded_line(body: str, field: str) -> str:
    """The line declaring ``field`` plus its previous line (annotations may sit above)."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"\b" + field + r"\b", line):
            return (lines[i - 1] + "\n" + line) if i > 0 else line
    return ""


def list_size_bounds(record: str, field: str, source: str) -> tuple:
    """``(count_max, item_max)`` from ``@Size(max = 20) List<@Size(max = 80) String> field``."""
    body = record_body(record, source)
    lines = [line for line in body.splitlines() if re.search(r"\b" + field + r"\b", line)]
    assert len(lines) == 1, "%s.%s sits on %d lines" % (record, field, len(lines))
    sizes = [int(n) for n in re.findall(r"@Size\(max = (\d+)\)", lines[0])]
    assert len(sizes) == 2, (
        "%s.%s carries %d @Size bounds, expected the list one and the item one" % (
            record, field, len(sizes)))
    return sizes[0], sizes[1]


def single_size_max(record: str, field: str, source: str) -> int:
    """The ``max`` from ``@Size(max = 240) String field`` -- exactly one @Size on the line."""
    body = record_body(record, source)
    lines = [line for line in body.splitlines() if re.search(r"\b" + field + r"\b", line)]
    assert len(lines) == 1, "%s.%s sits on %d lines" % (record, field, len(lines))
    sizes = re.findall(r"@Size\(max = (\d+)\)", lines[0])
    assert len(sizes) == 1, (
        "%s.%s carries %d @Size(max) bounds, expected exactly one scalar bound" % (
            record, field, len(sizes)))
    return int(sizes[0])


# --------------------------------------------------------------------------- case 1: UpdateMeRequest has ten fields

def test_the_update_me_request_dto_declares_ten_names():
    fields = java_record_fields("UpdateMeRequest", me_dto_source())
    assert sorted(fields) == [
        "displayName",
        "headline",
        "links",
        "location",
        "preferences",
        "summary",
        "targetLocations",
        "targetRoles",
        "workAuthorization",
        "yearsExperience",
    ], "UpdateMeRequest now has %d fields: %s" % (len(fields), fields)


# --------------------------------------------------------------------------- case 2: UpdateProfileRequest has nine fields

def test_the_update_profile_request_dto_declares_nine_names():
    fields = java_record_fields("UpdateProfileRequest", profile_dto_source())
    assert sorted(fields) == [
        "headline",
        "links",
        "location",
        "preferences",
        "summary",
        "targetLocations",
        "targetRoles",
        "workAuthorization",
        "yearsExperience",
    ], "UpdateProfileRequest now has %d fields: %s" % (len(fields), fields)


# --------------------------------------------------------------------------- case 3: both PATCH routes bind @Valid

def test_the_controller_binds_both_patch_routes_with_valid():
    src = controller_source()
    assert '@PatchMapping("/me")' in src, "PATCH /me route missing"
    assert '@PatchMapping("/me/profile")' in src, "PATCH /me/profile route missing"
    me_bindings = src.count("@RequestBody @Valid UpdateMeRequest")
    assert me_bindings == 1, (
        "expected one @Valid UpdateMeRequest binding, found %d" % me_bindings
    )
    profile_bindings = src.count("@RequestBody @Valid UpdateProfileRequest")
    assert profile_bindings == 1, (
        "expected one @Valid UpdateProfileRequest binding, found %d" % profile_bindings
    )


# --------------------------------------------------------------------------- case 4: displayName guard mirrors MAX_NAME

def test_the_display_name_guard_mirrors_the_settings_page():
    line = guarded_line(record_body("UpdateMeRequest", me_dto_source()), "displayName")
    assert line, "displayName field not found in UpdateMeRequest"
    assert "@Size(min = 1, max = 120)" in line, (
        "displayName guard drifted from @Size(min = 1, max = 120):\n%s" % line
    )
    assert "const MAX_NAME = 120;" in settings_source(), (
        "settings page no longer mirrors the 120-char display name cap"
    )


# --------------------------------------------------------------------------- case 5: yearsExperience bounds mirror MAX_YEARS

def test_the_years_experience_bounds_mirror_the_profile_cards():
    for name, source in (("UpdateMeRequest", me_dto_source()),
                         ("UpdateProfileRequest", profile_dto_source())):
        line = guarded_line(record_body(name, source), "yearsExperience")
        assert line, "yearsExperience field not found in %s" % name
        assert '@DecimalMin("0")' in line and '@DecimalMax("60")' in line, (
            "%s.yearsExperience guard drifted from @DecimalMin(\"0\") @DecimalMax(\"60\"):\n%s"
            % (name, line)
        )
    assert "const MAX_YEARS = 60;" in cards_source(), (
        "profile cards no longer mirror the 0-60 years bounds"
    )


# --------------------------------------------------------------------------- case 6: hooks patch their mapped endpoints

def test_the_profile_hooks_patch_their_mapped_endpoints():
    bodies = ts_call_bodies("useUpdateProfile", actions_source())
    assert len(bodies) == 1, "expected exactly one useUpdateProfile, found %d" % len(bodies)
    assert "endpoints.auth.me" in bodies[0], (
        "useUpdateProfile no longer PATCHes endpoints.auth.me"
    )
    assert '"PATCH"' in bodies[0], "useUpdateProfile no longer sends PATCH"

    details = ts_call_bodies("useUpdateProfileDetails", actions_source())
    assert len(details) == 1, (
        "expected exactly one useUpdateProfileDetails, found %d" % len(details)
    )
    assert "api.update<unknown>(endpoints.auth.profile, patch)" in details[0], (
        "useUpdateProfileDetails no longer updates endpoints.auth.profile with the patch"
    )

    src = read(ENDPOINTS)
    assert 'me: "/users/me"' in src, "auth.me path changed"
    assert 'profile: "/users/me/profile"' in src, "auth.profile path changed"


# --------------------------------------------------------------------------- case 7: settings sends only displayName

def test_the_settings_page_sends_only_display_name_through_use_update_profile():
    block = braced_arg_after(settings_source(), "updateMe.mutate(")
    keys = object_literal_keys(block)
    assert keys == ["displayName"], (
        "settings page now sends %s through useUpdateProfile" % keys
    )


# --------------------------------------------------------------------------- case 8: the form sends the six scalars

def test_the_career_profile_form_sends_the_six_scalar_fields():
    block = braced_arg_after(cards_source(), "update.mutate(")
    keys = sorted(object_literal_keys(block))
    assert keys == [
        "headline",
        "location",
        "summary",
        "targetLocations",
        "targetRoles",
        "yearsExperience",
    ], "CareerProfileForm now sends %s" % keys
    fields = java_record_fields("UpdateProfileRequest", profile_dto_source())
    assert set(keys) <= set(fields), (
        "CareerProfileForm sends keys UpdateProfileRequest does not bind: %s"
        % sorted(set(keys) - set(fields))
    )


# --------------------------------------------------------------------------- case 9: the maps form sends the three maps

def test_the_maps_form_sends_the_three_map_fields_by_name():
    src = cards_source()
    assert "Object.fromEntries(MAP_SECTIONS.map" in src, (
        "maps form no longer derives its payload from MAP_SECTIONS"
    )
    names = sorted(re.findall(r'name:\s*"(links|workAuthorization|preferences)"', src))
    assert names == ["links", "preferences", "workAuthorization"], (
        "MAP_SECTIONS now names %s" % names
    )
    fields = java_record_fields("UpdateProfileRequest", profile_dto_source())
    assert set(names) <= set(fields), (
        "maps form sends keys UpdateProfileRequest does not bind: %s"
        % sorted(set(names) - set(fields))
    )
    # The two forms together must cover exactly the DTO: the six scalars plus the three maps.
    form_block = braced_arg_after(src, "update.mutate(")
    union = set(object_literal_keys(form_block)) | set(names)
    assert union == set(fields), (
        "the two profile forms no longer partition UpdateProfileRequest: "
        "uncovered %s, extra %s" % (sorted(set(fields) - union), sorted(union - set(fields)))
    )


# --------------------------------------------------------------------------- case 10: unbound type keys stay unbound

def test_the_unbound_hook_type_keys_stay_unbound_while_the_sent_key_is_bound():
    bodies = ts_call_bodies("useUpdateProfile", actions_source())
    assert len(bodies) == 1, "expected exactly one useUpdateProfile"
    patch_type = braced_arg_after(bodies[0], "mutationFn: async (patch: ")
    type_keys = sorted(re.findall(r"([A-Za-z_$][\w$]*)\s*\??\s*:", patch_type))
    assert type_keys == ["avatarUrl", "displayName", "email"], (
        "useUpdateProfile's patch type now declares %s" % type_keys
    )
    fields = java_record_fields("UpdateMeRequest", me_dto_source())
    assert "displayName" in fields, (
        "the key the settings page sends (displayName) is no longer bound by UpdateMeRequest"
    )
    assert "email" not in fields and "avatarUrl" not in fields, (
        "UpdateMeRequest now binds email/avatarUrl -- update this gate and the hook, or the "
        "type keys and the DTO have converged and this characterization is stale"
    )


# --------------------------------------------------------------------------- case 11: failure paths are announced

def test_the_profile_mutations_announce_their_failures():
    bodies = ts_call_bodies("useUpdateProfile", actions_source())
    assert len(bodies) == 1, "expected exactly one useUpdateProfile"
    assert 'describe(err, "Couldn\'t save your profile.")' in bodies[0], (
        "useUpdateProfile failure toast changed"
    )

    details = ts_call_bodies("useUpdateProfileDetails", actions_source())
    assert len(details) == 1, "expected exactly one useUpdateProfileDetails"
    assert 'fail("Couldn\'t save your career profile.")' in details[0], (
        "useUpdateProfileDetails failure toast changed"
    )


# --------------------------------------------------------------------------- case 12: the target lists are one policy

def test_the_target_list_bounds_are_one_policy_across_records_and_screen():
    # The #215 shape, extended to the profile editor: each list bound both records carry has
    # a module constant, an enforcing branch, and a screen guard -- a single over-long role
    # or a 21st comma-separated entry gets the field's own sentence instead of the generic
    # "Request validation failed" 400 whose per-field details nobody opens (#201).
    target_path = ROOT / TARGETS
    assert target_path.exists(), "%s is not where this case reads it" % TARGETS
    module = read(TARGETS)
    for line in (
        "export const TARGET_ROLES_MAX_COUNT = 20;",
        "export const TARGET_ROLES_MAX_ITEM = 80;",
        "export const TARGET_LOCATIONS_MAX_COUNT = 20;",
        "export const TARGET_LOCATIONS_MAX_ITEM = 120;",
    ):
        assert line in module, (
            "%s is gone -- the record guards checked below have no mirror to agree with" % line)
    for record, source in (("UpdateProfileRequest", profile_dto_source()),
                           ("UpdateMeRequest", me_dto_source())):
        assert list_size_bounds(record, "targetRoles", source) == (20, 80), (
            "%s.targetRoles bounds moved; re-read what the module mirrors" % record)
        assert list_size_bounds(record, "targetLocations", source) == (20, 120), (
            "%s.targetLocations bounds moved; re-read what the module mirrors" % record)
    for line in (
        "if (items.length > TARGET_ROLES_MAX_COUNT) {",
        "if (items.some((item) => item.length > TARGET_ROLES_MAX_ITEM)) {",
        "if (items.length > TARGET_LOCATIONS_MAX_COUNT) {",
        "if (items.some((item) => item.length > TARGET_LOCATIONS_MAX_ITEM)) {",
    ):
        assert line in module, (
            "the module lost %r, so the constant above is declared but not enforced" % line)
    cards = cards_source()
    assert 'import { splitList, targetLocationsIssue, targetRolesIssue } from "@/lib/profile-targets";' in cards, (
        "the screen no longer imports the shared splitter and the two guards")
    assert "function splitList(" not in cards, (
        "splitList is defined in the component again; the guard would judge a different "
        "string than the payload sends")
    assert "const rolesProblem = targetRolesIssue(roleItems);" in cards, (
        "the roles field no longer runs the shared guard")
    assert "const locationsProblem = targetLocationsIssue(locationItems);" in cards, (
        "the target-locations field no longer runs the shared guard")
    assert "const saveable = yearsValid && !rolesProblem && !locationsProblem;" in cards, (
        "the save gate no longer waits for the two list guards")
    assert "targetRoles: roleItems," in cards and "targetLocations: locationItems," in cards, (
        "the payload no longer sends the same items the guard judged")
    assert cards.count("{rolesProblem && (") == 1 and cards.count("{locationsProblem && (") == 1, (
        "a list guard no longer renders its sentence")


# --------------------------------------------------------------------------- case 13: the three text caps

def test_the_scalar_text_caps_are_one_policy_across_records_and_screen():
    # Same one-policy shape as the lists (case 12), except the screen's enforcement point is
    # the input's maxLength attribute: the browser clips typing and paste, so there is no
    # issue-message branch to pin -- the attribute ties each input to its constant.
    cards = cards_source()
    for constant, name, field, cap in (
        ("const MAX_HEADLINE = 240;", "MAX_HEADLINE", "headline", 240),
        ("const MAX_LOCATION = 120;", "MAX_LOCATION", "location", 120),
        ("const MAX_SUMMARY = 5000;", "MAX_SUMMARY", "summary", 5000),
    ):
        assert constant in cards, "the card lost %r" % constant
        for record, source in (("UpdateProfileRequest", profile_dto_source()),
                               ("UpdateMeRequest", me_dto_source())):
            assert single_size_max(record, field, source) == cap, (
                "%s.%s moved; re-read the card constant %r" % (record, field, constant))
        attr = "maxLength={%s}" % name
        assert attr in cards, (
            "no input enforces %r, so the constant above governs nothing" % attr)
