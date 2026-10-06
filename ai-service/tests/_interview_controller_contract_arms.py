"""Mutation arms for the Interview controller request contract gate.

Each arm mutates one clause of the contract and predicts which tests should go red.
All predictions are frozen before running, so a mismatch is itself evidence.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/interview/web/InterviewController.java"
DTOS = "backend/src/main/java/com/careeros/interview/dto/InterviewDtos.java"
ACTIONS = "frontend/src/lib/hooks/actions.ts"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def write(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text.replace("\n", "\r\n") if "\r\n" in read(rel) else text, encoding="utf-8")


# --------------------------------------------------------------------------- Arms

def arm_remove_notblank_from_answer() -> dict:
    """Remove @NotBlank from AnswerRequest.answer — the guard should fail."""
    old = read(DTOS)
    # Find the AnswerRequest record and remove @NotBlank from answer
    pattern = r"(record\s+AnswerRequest\s*\(\s*)@NotBlank\s+"
    new = re.sub(pattern, r"\1", old)
    assert new != old, "@NotBlank not found on answer field"
    write(DTOS, new)
    return {
        "name": "remove @NotBlank from answer",
        "predicted_red": ["test_the_answer_field_is_guarded_by_notblank"],
        "description": "Removing @NotBlank means the validation no longer requires answer",
    }


def arm_rename_answer_to_response_in_answer_request() -> dict:
    """Rename answer→response in AnswerRequest — the census test should fail."""
    old = read(DTOS)
    new = old.replace("String answer)", "String response)")
    assert new != old, "answer field not found in AnswerRequest"
    write(DTOS, new)
    return {
        "name": "rename answer to response in AnswerRequest",
        "predicted_red": [
            "test_the_answer_request_dto_declares_one_name",
            "test_the_answer_field_is_guarded_by_notblank",
        ],
        "description": "Field name changed from answer to response; census finds 'response' not 'answer', and @NotBlank guard can't find 'answer' field",
    }


def arm_rename_jobid_to_jid_in_create_session() -> dict:
    """Rename jobId→jid in CreateSessionRequest — the seven-field census should fail."""
    old = read(DTOS)
    new = old.replace("UUID jobId,", "UUID jid,")
    assert new != old, "jobId field not found in CreateSessionRequest"
    write(DTOS, new)
    return {
        "name": "rename jobId to jid in CreateSessionRequest",
        "predicted_red": ["test_the_create_session_request_dto_declares_seven_names"],
        "description": "Field name changed from jobId to jid, census will find different names",
    }


def arm_remove_valid_from_create_session_request() -> dict:
    """Remove @Valid from POST /interview/sessions binding — the controller test should fail."""
    old = read(CONTROLLER)
    new = old.replace("@RequestBody @Valid CreateSessionRequest", "@RequestBody CreateSessionRequest")
    assert new != old, "@Valid not found on CreateSessionRequest binding"
    write(CONTROLLER, new)
    return {
        "name": "remove @Valid from CreateSessionRequest binding",
        "predicted_red": ["test_both_post_endpoints_bind_their_request_types"],
        "description": "Controller no longer validates CreateSessionRequest with @Valid",
    }


def arm_remove_fail_from_use_create_interview_session() -> dict:
    """Remove fail() call from useCreateInterviewSession onError — the failure announcement test should fail."""
    old = read(ACTIONS)
    # Find useCreateInterviewSession function and remove fail() call
    m = re.search(r"(export function useCreateInterviewSession.*?\{)(.*?)(\n\})", old, re.DOTALL)
    assert m, "useCreateInterviewSession function not found"
    func_body = m.group(2)
    new_body = func_body.replace('onError: fail("Couldn\'t start the interview.")', "onError: () => {}")
    assert new_body != func_body, "fail() call not found in useCreateInterviewSession"
    new = old[:m.start(2)] + new_body + old[m.end(2):]
    write(ACTIONS, new)
    return {
        "name": "remove fail() from useCreateInterviewSession",
        "predicted_red": ["test_the_interview_mutations_announce_their_failures"],
        "description": "onError handler no longer calls fail(), so the test won't find fail() in the body",
    }


def arm_rename_mode_to_type_in_create_session() -> dict:
    """Rename mode→type in CreateSessionRequest — the seven-field census should fail."""
    old = read(DTOS)
    new = old.replace("String mode,", "String type,")
    assert new != old, "mode field not found in CreateSessionRequest"
    write(DTOS, new)
    return {
        "name": "rename mode to type in CreateSessionRequest",
        "predicted_red": ["test_the_create_session_request_dto_declares_seven_names"],
        "description": "Field name changed from mode to type, census will find different names",
    }


def arm_rename_config_to_settings_in_create_session() -> dict:
    """Rename config→settings in CreateSessionRequest — the seven-field census should fail."""
    old = read(DTOS)
    new = old.replace("Map<String, Object> config)", "Map<String, Object> settings)")
    assert new != old, "config field not found in CreateSessionRequest"
    write(DTOS, new)
    return {
        "name": "rename config to settings in CreateSessionRequest",
        "predicted_red": ["test_the_create_session_request_dto_declares_seven_names"],
        "description": "Field name changed from config to settings, census will find different names",
    }


ARMS = [
    arm_remove_notblank_from_answer,
    arm_rename_answer_to_response_in_answer_request,
    arm_rename_jobid_to_jid_in_create_session,
    arm_remove_valid_from_create_session_request,
    arm_remove_fail_from_use_create_interview_session,
    arm_rename_mode_to_type_in_create_session,
    arm_rename_config_to_settings_in_create_session,
]
