"""Mutation arms for the Resume controller request contract gate.

Each arm mutates one clause of the contract and predicts which tests should go red.
All predictions are frozen before running, so a mismatch is itself evidence.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/resume/web/ResumeController.java"
DTOS = "backend/src/main/java/com/careeros/resume/dto/ResumeDtos.java"
ACTIONS = "frontend/src/lib/hooks/actions.ts"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def write(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text.replace("\n", "\r\n") if "\r\n" in read(rel) else text, encoding="utf-8")


# --------------------------------------------------------------------------- Arms

def arm_remove_notblank_from_title() -> dict:
    """Remove @NotBlank from CreateResumeRequest.title — the guard should fail."""
    old = read(DTOS)
    # Find the CreateResumeRequest record and remove @NotBlank from title
    pattern = r"(record\s+CreateResumeRequest\s*\(\s*)@NotBlank\s+"
    new = re.sub(pattern, r"\1", old)
    assert new != old, "@NotBlank not found on title field"
    write(DTOS, new)
    return {
        "name": "remove @NotBlank from title",
        "predicted_red": ["test_the_title_field_is_guarded_by_notblank_in_create"],
        "description": "Removing @NotBlank means the validation no longer requires title",
    }


def arm_rename_title_to_subject_in_create() -> dict:
    """Rename title→subject in CreateResumeRequest — both census and @NotBlank tests should fail."""
    old = read(DTOS)
    new = old.replace("String title,", "String subject,")
    assert new != old, "title field not found in CreateResumeRequest"
    write(DTOS, new)
    return {
        "name": "rename title to subject in CreateResumeRequest",
        "predicted_red": [
            "test_the_create_resume_request_dto_declares_two_names",
            "test_the_title_field_is_guarded_by_notblank_in_create",
        ],
        "description": "Field name changed from title to subject; census finds 'subject' not 'title', and @NotBlank guard can't find 'title' field",
    }


def arm_rename_versionid_to_vid_in_set_current() -> dict:
    """Rename versionId→vid in SetCurrentVersionRequest — the frontend hook test should fail."""
    old = read(DTOS)
    new = old.replace("UUID versionId)", "UUID vid)")
    assert new != old, "versionId field not found in SetCurrentVersionRequest"
    write(DTOS, new)
    return {
        "name": "rename versionId to vid in SetCurrentVersionRequest",
        "predicted_red": ["test_the_set_current_version_request_dto_declares_one_name"],
        "description": "Field name changed from versionId to vid, census will find 'vid' not 'versionId'",
    }


def arm_remove_valid_from_create_resume_request() -> dict:
    """Remove @Valid from POST /resumes binding — the controller test should fail."""
    old = read(CONTROLLER)
    new = old.replace("@RequestBody @Valid CreateResumeRequest", "@RequestBody CreateResumeRequest")
    assert new != old, "@Valid not found on CreateResumeRequest binding"
    write(CONTROLLER, new)
    return {
        "name": "remove @Valid from CreateResumeRequest binding",
        "predicted_red": ["test_all_three_endpoints_bind_their_request_types"],
        "description": "Controller no longer validates CreateResumeRequest with @Valid",
    }


def arm_remove_fail_from_use_set_current_resume() -> dict:
    """Remove fail() call from useSetCurrentResume onError — the failure announcement test should fail."""
    old = read(ACTIONS)
    # Find useSetCurrentResume function and remove fail() call
    m = re.search(r"(export function useSetCurrentResume.*?\{)(.*?)(\n\})", old, re.DOTALL)
    assert m, "useSetCurrentResume function not found"
    func_body = m.group(2)
    new_body = func_body.replace('onError: fail("Couldn\'t change the current version.")', "onError: () => {}")
    assert new_body != func_body, "fail() call not found in useSetCurrentResume"
    new = old[:m.start(2)] + new_body + old[m.end(2):]
    write(ACTIONS, new)
    return {
        "name": "remove fail() from useSetCurrentResume",
        "predicted_red": ["test_the_resume_mutations_announce_their_failures"],
        "description": "onError handler no longer calls fail(), so the test won't find fail() in the body",
    }


def arm_rename_plaintext_to_rawtext_in_create() -> dict:
    """Rename plaintext→rawText in CreateResumeRequest — the two-field census should fail."""
    old = read(DTOS)
    # Replace the first occurrence of plaintext in the record (the actual field name)
    m = re.search(r"record\s+CreateResumeRequest\s*\((.*?)\)\s*\{", old, re.DOTALL)
    assert m, "CreateResumeRequest record not found"
    record_body = m.group(1)
    # Only replace if it's the field declaration, not inside @JsonAlias
    if "plaintext" in record_body and "@JsonAlias" in record_body:
        # The field is declared as: @JsonAlias({...}) String plaintext
        new_record = record_body.replace("String plaintext", "String rawText")
        new = old[:m.start(1)] + new_record + old[m.end(1):]
        assert new != old, "plaintext field not found"
        write(DTOS, new)
        return {
            "name": "rename plaintext to rawText in CreateResumeRequest",
            "predicted_red": ["test_the_create_resume_request_dto_declares_two_names"],
            "description": "Field renamed from plaintext to rawText; census will find ['rawText', 'title'] instead of ['plaintext', 'title']",
        }
    else:
        # Fallback: just replace the word
        new = old.replace("String plaintext", "String rawText", 1)
        assert new != old, "plaintext field not found"
        write(DTOS, new)
        return {
            "name": "rename plaintext to rawText in CreateResumeRequest",
            "predicted_red": ["test_the_create_resume_request_dto_declares_two_names"],
            "description": "Field renamed from plaintext to rawText; census will find different names",
        }


ARMS = [
    arm_remove_notblank_from_title,
    arm_rename_title_to_subject_in_create,
    arm_rename_versionid_to_vid_in_set_current,
    arm_remove_valid_from_create_resume_request,
    arm_remove_fail_from_use_set_current_resume,
    arm_rename_plaintext_to_rawtext_in_create,
]
