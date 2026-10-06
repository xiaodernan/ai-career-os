"""Mutation arms for the Conversation controller request contract gate.

Each arm mutates one clause of the contract and predicts which tests should go red.
All predictions are frozen before running, so a mismatch is itself evidence.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTROLLER = "backend/src/main/java/com/careeros/conversation/web/ConversationController.java"
DTOS = "backend/src/main/java/com/careeros/conversation/dto/ConversationDtos.java"
ACTIONS = "frontend/src/lib/hooks/actions.ts"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def write(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text.replace("\n", "\r\n") if "\r\n" in read(rel) else text, encoding="utf-8")


# --------------------------------------------------------------------------- Arms

def arm_rename_title_to_name_in_create() -> dict:
    """Rename title→name in CreateConversationRequest — both census tests should fail (shared structure)."""
    old = read(DTOS)
    # Replace in both records since they share the same line pattern
    new = old.replace("String title,", "String name,")
    assert new != old, "title field not found"
    write(DTOS, new)
    return {
        "name": "rename title to name in CreateConversationRequest",
        "predicted_red": [
            "test_the_create_conversation_request_dto_declares_two_names",
            "test_the_update_conversation_request_dto_declares_two_names",
        ],
        "description": "Field name changed from title to name in both DTOs (same line pattern), census will find different names in both",
    }


def arm_rename_title_to_label_in_update() -> dict:
    """Rename title→label in UpdateConversationRequest — the census test should fail."""
    old = read(DTOS)
    # Find UpdateConversationRequest specifically
    m = re.search(r"record\s+UpdateConversationRequest\s*\((.*?)\)\s*\{", old, re.DOTALL)
    assert m, "UpdateConversationRequest record not found"
    record_body = m.group(1)
    if "String title" in record_body:
        new_record = record_body.replace("String title", "String label")
        new = old[:m.start(1)] + new_record + old[m.end(1):]
        assert new != old, "title field not found in UpdateConversationRequest"
        write(DTOS, new)
        return {
            "name": "rename title to label in UpdateConversationRequest",
            "predicted_red": ["test_the_update_conversation_request_dto_declares_two_names"],
            "description": "Field name changed from title to label, census will find different names",
        }
    else:
        # Fallback
        new = old.replace("public record UpdateConversationRequest(@Size(max = 200) String title,",
                          "public record UpdateConversationRequest(@Size(max = 200) String label,")
        assert new != old, "title field not found in UpdateConversationRequest"
        write(DTOS, new)
        return {
            "name": "rename title to label in UpdateConversationRequest",
            "predicted_red": ["test_the_update_conversation_request_dto_declares_two_names"],
            "description": "Field name changed from title to label, census will find different names",
        }


def arm_remove_valid_from_update_conversation_request() -> dict:
    """Remove @Valid from PATCH /{id} binding — the controller test should fail."""
    old = read(CONTROLLER)
    new = old.replace("@RequestBody @Valid UpdateConversationRequest", "@RequestBody UpdateConversationRequest")
    assert new != old, "@Valid not found on UpdateConversationRequest binding"
    write(CONTROLLER, new)
    return {
        "name": "remove @Valid from UpdateConversationRequest binding",
        "predicted_red": ["test_both_endpoints_bind_their_request_types"],
        "description": "Controller no longer validates UpdateConversationRequest with @Valid",
    }


def arm_remove_fail_from_use_create_conversation() -> dict:
    """Remove fail() call from useCreateConversation onError — the failure announcement test should fail."""
    old = read(ACTIONS)
    # Find useCreateConversation function and remove fail() call
    m = re.search(r"(export function useCreateConversation.*?\{)(.*?)(\n\})", old, re.DOTALL)
    assert m, "useCreateConversation function not found"
    func_body = m.group(2)
    new_body = func_body.replace('onError: fail("Couldn\'t start a conversation.")', "onError: () => {}")
    assert new_body != func_body, "fail() call not found in useCreateConversation"
    new = old[:m.start(2)] + new_body + old[m.end(2):]
    write(ACTIONS, new)
    return {
        "name": "remove fail() from useCreateConversation",
        "predicted_red": ["test_the_conversation_mutations_announce_their_failures"],
        "description": "onError handler no longer calls fail(), so the test won't find fail() in the body",
    }


def arm_remove_fail_from_use_rename_conversation() -> dict:
    """Remove fail() call from useRenameConversation onError — the failure announcement test should fail."""
    old = read(ACTIONS)
    # Find useRenameConversation function and remove fail() call
    m = re.search(r"(export function useRenameConversation.*?\{)(.*?)(\n\})", old, re.DOTALL)
    assert m, "useRenameConversation function not found"
    func_body = m.group(2)
    new_body = func_body.replace('onError: fail("Couldn\'t rename the conversation.")', "onError: () => {}")
    assert new_body != func_body, "fail() call not found in useRenameConversation"
    new = old[:m.start(2)] + new_body + old[m.end(2):]
    write(ACTIONS, new)
    return {
        "name": "remove fail() from useRenameConversation",
        "predicted_red": ["test_the_conversation_mutations_announce_their_failures"],
        "description": "onError handler no longer calls fail(), so the test won't find fail() in the body",
    }


def arm_rename_context_to_metadata_in_create() -> dict:
    """Rename context→metadata in CreateConversationRequest — the census test should fail."""
    old = read(DTOS)
    # Find CreateConversationRequest specifically
    m = re.search(r"record\s+CreateConversationRequest\s*\((.*?)\)\s*\{", old, re.DOTALL)
    assert m, "CreateConversationRequest record not found"
    record_body = m.group(1)
    if "Map<String, Object> context" in record_body:
        new_record = record_body.replace("Map<String, Object> context", "Map<String, Object> metadata")
        new = old[:m.start(1)] + new_record + old[m.end(1):]
        assert new != old, "context field not found in CreateConversationRequest"
        write(DTOS, new)
        return {
            "name": "rename context to metadata in CreateConversationRequest",
            "predicted_red": ["test_the_create_conversation_request_dto_declares_two_names"],
            "description": "Field name changed from context to metadata, census will find different names",
        }
    else:
        # Fallback
        new = old.replace("String title, Map<String, Object> context)",
                          "String title, Map<String, Object> metadata)")
        assert new != old, "context field not found in CreateConversationRequest"
        write(DTOS, new)
        return {
            "name": "rename context to metadata in CreateConversationRequest",
            "predicted_red": ["test_the_create_conversation_request_dto_declares_two_names"],
            "description": "Field name changed from context to metadata, census will find different names",
        }


ARMS = [
    arm_rename_title_to_name_in_create,
    arm_rename_title_to_label_in_update,
    arm_remove_valid_from_update_conversation_request,
    arm_remove_fail_from_use_create_conversation,
    arm_remove_fail_from_use_rename_conversation,
    arm_rename_context_to_metadata_in_create,
]
