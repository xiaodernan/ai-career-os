"""Mutation arms for test_copilot_chat_request_contract.py — simplified, behavioral only.

Only the arms whose mutation actually changes a value the gate reads are kept.  A1 (add a
Java field) is dropped because the Python gate does not compile Java; A2 (remove @Valid) is
kept because the controller-source scanner can see it; A4/A5 are merged into one arm that
renames ``message`` in *both* call sites at once (the gate checks both).
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_FILE = "ai-service/tests/test_copilot_chat_request_contract.py"
DTOS = "backend/src/main/java/com/careeros/conversation/dto/ConversationDtos.java"
CONTROLLER = "backend/src/main/java/com/careeros/conversation/web/CopilotController.java"
ACTIONS = "frontend/src/lib/hooks/actions.ts"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def write(rel, text):
    (ROOT / rel).write_text(text.replace("\n", "\r\n") if os.name == "nt" else text, encoding="utf-8")


def sha256(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def run_tests():
    """Run only this test file and return (passed_count, failed_names)."""
    test_path = ROOT / TEST_FILE
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=no"],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    output = result.stdout + result.stderr
    summary_match = re.search(r"(\d+)\s+passed", output)
    passed = int(summary_match.group(1)) if summary_match else 0
    failed_names = []
    for m in re.finditer(r"FAILED\s+\S+::(test_\w+)", output):
        failed_names.append(m.group(1))
    return passed, failed_names, output


def restore_file(rel, original_sha):
    current = sha256(rel)
    if current != original_sha:
        subprocess.run(["git", "checkout", "--", rel], cwd=str(ROOT), check=True)


# ---- arms -----------------------------------------------------------------------

def arm_remove_notblank():
    """A1: Remove @NotBlank from the message field."""
    src = read(DTOS)
    assert "@NotBlank" in src
    mutated = src.replace("@NotBlank ", "", 1)
    backup = sha256(DTOS)
    write(DTOS, mutated)
    try:
        passed, failed, output = run_tests()
        return passed, failed
    finally:
        restore_file(DTOS, backup)


def arm_rename_message_in_both_calls():
    """A2: Rename 'message' to 'msg' in both the stream and fallback body objects."""
    src = read(ACTIONS)
    # Replace all occurrences of "message: body.message" with "msg: body.message"
    # This hits both the stream call and the fallback call
    old = "message: body.message"
    new = "msg: body.message"
    assert old in src, f"cannot find '{old}' in actions.ts"
    mutated = src.replace(old, new)
    backup = sha256(ACTIONS)
    write(ACTIONS, mutated)
    try:
        passed, failed, output = run_tests()
        return passed, failed
    finally:
        restore_file(ACTIONS, backup)


def arm_rename_context_in_both_calls():
    """A3: Rename 'context' to 'ctx' in both call sites."""
    src = read(ACTIONS)
    # Replace "context: body.context ?? {}" with "ctx: body.context ?? {}"
    old = "context: body.context"
    new = "ctx: body.context"
    assert old in src, f"cannot find '{old}' in actions.ts"
    mutated = src.replace(old, new)
    backup = sha256(ACTIONS)
    write(ACTIONS, mutated)
    try:
        passed, failed, output = run_tests()
        return passed, failed
    finally:
        restore_file(ACTIONS, backup)


def arm_remove_valid_from_controller():
    """A4: Remove @Valid from the second @PostMapping in CopilotController."""
    src = read(CONTROLLER)
    posts = list(re.finditer(r"@PostMapping", src))
    assert len(posts) >= 2
    second_post_start = posts[1].start()
    after_second = src[second_post_start:]
    assert "@Valid" in after_second
    mutated_src = src[:second_post_start] + after_second.replace("@Valid", "", 1)
    backup = sha256(CONTROLLER)
    write(CONTROLLER, mutated_src)
    try:
        passed, failed, output = run_tests()
        return passed, failed
    finally:
        restore_file(CONTROLLER, backup)


def arm_rename_endpoint():
    """A5: Rename copilotChat to copilotMessage in endpoints.ts."""
    src = read(ENDPOINTS)
    assert "copilotChat:" in src
    mutated = src.replace("copilotChat:", "copilotMessage:", 1)
    backup = sha256(ENDPOINTS)
    write(ENDPOINTS, mutated)
    try:
        passed, failed, output = run_tests()
        return passed, failed
    finally:
        restore_file(ENDPOINTS, backup)


def arm_remove_fail_call():
    """A6: Replace fail() with empty handler in onError."""
    src = read(ACTIONS)
    assert "onError: fail(" in src
    mutated = src.replace("onError: fail(\"Copilot couldn't answer.\")", "onError: () => {}", 1)
    backup = sha256(ACTIONS)
    write(ACTIONS, mutated)
    try:
        passed, failed, output = run_tests()
        return passed, failed
    finally:
        restore_file(ACTIONS, backup)


ARMS = {
    "A1": ("remove @NotBlank guard", arm_remove_notblank,
           ["test_the_message_field_is_guarded_by_notblank"]),
    "A2": ("rename message→msg in both calls", arm_rename_message_in_both_calls,
           ["test_the_stream_call_sends_the_three_dto_names",
            "test_the_fallback_call_sends_the_same_three_names"]),
    "A3": ("rename context→ctx in both calls", arm_rename_context_in_both_calls,
           ["test_the_stream_call_sends_the_three_dto_names",
            "test_the_fallback_call_sends_the_same_three_names"]),
    "A4": ("remove @Valid from second endpoint", arm_remove_valid_from_controller,
           ["test_both_copilot_endpoints_bind_the_same_request_type"]),
    "A5": ("rename copilotChat endpoint", arm_rename_endpoint,
           ["test_the_client_endpoint_map_names_both_routes"]),
    "A6": ("remove fail() from onError", arm_remove_fail_call,
           ["test_the_copilot_mutation_announces_its_failure"]),
}


def main():
    print("=" * 80)
    print("Copilot chat request contract -- witness chain")
    print("=" * 80)

    baseline_passed, baseline_failed, _ = run_tests()
    print(f"\nBaseline: {baseline_passed} passed, {len(baseline_failed)} failed")
    assert baseline_passed == 7 and len(baseline_failed) == 0, "baseline is not all green"

    results = {}
    for arm_name, (desc, arm_fn, expected_reds) in sorted(ARMS.items()):
        print(f"\n--- {arm_name}: {desc} ---")

        try:
            passed, failed = arm_fn()
            actual_reds = sorted(set(failed))
            expected_reds_sorted = sorted(expected_reds)

            match = actual_reds == expected_reds_sorted
            status = "MATCHED" if match else "MISMATCH"

            print(f"  Expected reds: {expected_reds_sorted}")
            print(f"  Actual reds:   {actual_reds}")
            print(f"  Passed: {passed}, Status: {status}")

            results[arm_name] = {
                "status": status,
                "expected": expected_reds_sorted,
                "actual": actual_reds,
                "passed": passed,
            }
        except Exception as e:
            print(f"  ERROR: {e}")
            results[arm_name] = {"status": "ERROR", "error": str(e)}

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    matched = sum(1 for r in results.values() if r.get("status") == "MATCHED")
    mismatched = sum(1 for r in results.values() if r.get("status") == "MISMATCH")
    errors = sum(1 for r in results.values() if r.get("status") == "ERROR")
    total = len(results)
    print(f"Matched: {matched}/{total}")
    print(f"Mismatched: {mismatched}/{total}")
    print(f"Errors: {errors}/{total}")

    for arm_name, result in results.items():
        print(f"  {arm_name}: {result['status']}")

    if mismatched > 0 or errors > 0:
        print("\nIssues:")
        for arm_name, result in results.items():
            if result["status"] == "MISMATCH":
                print(f"  {arm_name}: expected {result['expected']}, got {result['actual']}")
            elif result["status"] == "ERROR":
                print(f"  {arm_name}: {result['error']}")

    sys.exit(0 if (mismatched == 0 and errors == 0) else 1)


if __name__ == "__main__":
    main()
