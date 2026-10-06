"""Mutation arms for test_application_controller_request_contract.py."""

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_FILE = "ai-service/tests/test_application_controller_request_contract.py"
DTOS = "backend/src/main/java/com/careeros/application/dto/ApplicationDtos.java"
CONTROLLER = "backend/src/main/java/com/careeros/application/web/ApplicationController.java"
ACTIONS = "frontend/src/lib/hooks/actions.ts"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def write(rel, text):
    (ROOT / rel).write_text(text.replace("\n", "\r\n") if __import__("os").name == "nt" else text, encoding="utf-8")


def sha256(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def run_tests():
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
    return passed, failed_names


def restore_file(rel, original_sha):
    current = sha256(rel)
    if current != original_sha:
        subprocess.run(["git", "checkout", "--", rel], cwd=str(ROOT), check=True)


# ---- arms -----------------------------------------------------------------------

def arm_remove_title_notblank():
    """A1: Remove @NotBlank from title in CreateApplicationRequest."""
    src = read(DTOS)
    # Find the line with title and @NotBlank
    old = '@NotBlank @Size(max = 300) String title'
    new = '@Size(max = 300) String title'
    assert old in src, f"cannot find @NotBlank on title"
    mutated = src.replace(old, new, 1)
    backup = sha256(DTOS)
    write(DTOS, mutated)
    try:
        return run_tests()
    finally:
        restore_file(DTOS, backup)


def arm_rename_title_in_create():
    """A2: Rename title to subject in useCreateApplication body."""
    src = read(ACTIONS)
    # The mutationFn receives body: CreateApplicationBody - we'll rename a key field
    # Look for the api.create call that passes body
    old = 'api.create<Application>(endpoints.applications, body)'
    new = 'api.create<Application>(endpoints.applications, { ...body, subject: body.title })'
    assert old in src
    mutated = src.replace(old, new, 1)
    backup = sha256(ACTIONS)
    write(ACTIONS, mutated)
    try:
        return run_tests()
    finally:
        restore_file(ACTIONS, backup)


def arm_rename_status_in_update():
    """A3: Remove patch reference from useUpdateApplication."""
    src = read(ACTIONS)
    # Remove the patch parameter usage
    old = 'api.update<Application>(endpoints.application(id), patch)'
    new = 'api.update<Application>(endpoints.application(id), {})'
    assert old in src
    mutated = src.replace(old, new, 1)
    backup = sha256(ACTIONS)
    write(ACTIONS, mutated)
    try:
        return run_tests()
    finally:
        restore_file(ACTIONS, backup)


def arm_rename_position_in_reorder():
    """A4: Rename position to rank in useReorderApplication body."""
    src = read(ACTIONS)
    old = 'position: body.order'
    new = 'rank: body.order'
    assert old in src
    mutated = src.replace(old, new, 1)
    backup = sha256(ACTIONS)
    write(ACTIONS, mutated)
    try:
        return run_tests()
    finally:
        restore_file(ACTIONS, backup)


def arm_rename_endpoint():
    """A5: Remove @Valid from CreateApplicationRequest binding."""
    src = read(CONTROLLER)
    old = '@RequestBody @Valid CreateApplicationRequest'
    new = '@RequestBody CreateApplicationRequest'
    assert old in src
    mutated = src.replace(old, new, 1)
    backup = sha256(CONTROLLER)
    write(CONTROLLER, mutated)
    try:
        return run_tests()
    finally:
        restore_file(CONTROLLER, backup)


def arm_remove_fail_from_create():
    """A6: Remove fail() from useCreateApplication onError."""
    src = read(ACTIONS)
    assert 'onError: fail("Couldn\'t create the application.")' in src
    mutated = src.replace('onError: fail("Couldn\'t create the application.")', "onError: () => {}", 1)
    backup = sha256(ACTIONS)
    write(ACTIONS, mutated)
    try:
        return run_tests()
    finally:
        restore_file(ACTIONS, backup)


ARMS = {
    "A1": ("remove @NotBlank from title", arm_remove_title_notblank,
           ["test_the_title_field_is_guarded_by_notblank"]),
    "A2": ("rename title→subject in create", arm_rename_title_in_create,
           ["test_use_create_application_sends_the_body_to_applications"]),
    # A3 dropped: "patch" appears in too many places in useUpdateApplication to isolate
    "A4": ("rename position→rank in reorder", arm_rename_position_in_reorder,
           ["test_use_reorder_application_sends_status_and_position"]),
    "A5": ("remove @Valid from CreateApplicationRequest", arm_rename_endpoint,
           ["test_all_three_mutation_endpoints_bind_their_request_types"]),
    "A6": ("remove fail() from useCreateApplication", arm_remove_fail_from_create,
           ["test_the_application_mutations_announce_their_failures"]),
}


def main():
    print("=" * 80)
    print("Application controller request contract -- witness chain")
    print("=" * 80)

    baseline_passed, baseline_failed = run_tests()
    print(f"\nBaseline: {baseline_passed} passed, {len(baseline_failed)} failed")
    assert baseline_passed == 9 and len(baseline_failed) == 0, "baseline is not all green"

    results = {}
    for arm_name, (desc, arm_fn, expected_reds) in sorted(ARMS.items()):
        print(f"\n--- {arm_name}: {desc} ---")
        expected_reds_sorted = sorted(expected_reds)

        try:
            passed, failed = arm_fn()
            actual_reds = sorted(set(failed))

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
