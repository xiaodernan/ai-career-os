"""Mutation arms for test_jd_controller_request_contract.py — simplified."""

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_FILE = "ai-service/tests/test_jd_controller_request_contract.py"
DTOS = "backend/src/main/java/com/careeros/job/dto/JobDtos.java"
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

def arm_remove_rawtext_notblank():
    """A1: Remove @NotBlank from rawText in JdRequest (line 115)."""
    src = read(DTOS)
    # Line 115: public record JdRequest(@NotBlank @JsonAlias("raw_text") String rawText,
    old = 'public record JdRequest(@NotBlank @JsonAlias("raw_text") String rawText,'
    new = 'public record JdRequest(@JsonAlias("raw_text") String rawText,'
    assert old in src, f"cannot find JdRequest line"
    mutated = src.replace(old, new, 1)
    backup = sha256(DTOS)
    write(DTOS, mutated)
    try:
        return run_tests()
    finally:
        restore_file(DTOS, backup)


def arm_rename_rawtext_in_analyze():
    """A2: Rename rawText to text in useAnalyzeJd call."""
    src = read(ACTIONS)
    old = "{ rawText }"
    new = "{ text }"
    assert old in src
    mutated = src.replace(old, new, 1)
    backup = sha256(ACTIONS)
    write(ACTIONS, mutated)
    try:
        return run_tests()
    finally:
        restore_file(ACTIONS, backup)


def arm_rename_jdraw_in_suggestions():
    """A3: Rename jdRaw to jd in useResumeSuggestions call."""
    src = read(ACTIONS)
    old = "jdRaw: body.jdRaw"
    new = "jd: body.jdRaw"
    assert old in src
    mutated = src.replace(old, new, 1)
    backup = sha256(ACTIONS)
    write(ACTIONS, mutated)
    try:
        return run_tests()
    finally:
        restore_file(ACTIONS, backup)


def arm_remove_jdraw_notblank():
    """A4: Remove @NotBlank from jdRaw in JdSuggestionsRequest (line 120)."""
    src = read(DTOS)
    # Line 120: @NotBlank @JsonAlias("jd_raw") String jdRaw) {
    old = '@NotBlank @JsonAlias("jd_raw") String jdRaw)'
    new = '@JsonAlias("jd_raw") String jdRaw)'
    assert old in src
    mutated = src.replace(old, new, 1)
    backup = sha256(DTOS)
    write(DTOS, mutated)
    try:
        return run_tests()
    finally:
        restore_file(DTOS, backup)


def arm_rename_endpoint():
    """A5: Rename jdAnalyze to jdParse in endpoints.ts."""
    src = read(ENDPOINTS)
    assert "jdAnalyze:" in src
    mutated = src.replace("jdAnalyze:", "jdParse:", 1)
    backup = sha256(ENDPOINTS)
    write(ENDPOINTS, mutated)
    try:
        return run_tests()
    finally:
        restore_file(ENDPOINTS, backup)


def arm_remove_fail_from_analyze():
    """A6: Remove fail() from useAnalyzeJd onError."""
    src = read(ACTIONS)
    assert 'onError: fail("JD analysis failed.")' in src
    mutated = src.replace('onError: fail("JD analysis failed.")', "onError: () => {}", 1)
    backup = sha256(ACTIONS)
    write(ACTIONS, mutated)
    try:
        return run_tests()
    finally:
        restore_file(ACTIONS, backup)


ARMS = {
    "A1": ("remove @NotBlank from rawText", arm_remove_rawtext_notblank,
           ["test_the_rawtext_field_is_guarded_by_notblank"]),
    "A2": ("rename rawText→text in useAnalyzeJd", arm_rename_rawtext_in_analyze,
           ["test_use_analyze_jd_sends_rawtext"]),
    "A3": ("rename jdRaw→jd in useResumeSuggestions", arm_rename_jdraw_in_suggestions,
           ["test_use_resume_suggestions_sends_jdraw_and_resume_version_id"]),
    "A4": ("remove @NotBlank from jdRaw", arm_remove_jdraw_notblank,
           ["test_the_jdraw_field_is_guarded_by_notblank"]),
    "A5": ("rename jdAnalyze endpoint", arm_rename_endpoint,
           ["test_the_client_endpoint_map_names_both_routes"]),
    "A6": ("remove fail() from useAnalyzeJd", arm_remove_fail_from_analyze,
           ["test_the_jd_mutations_announce_their_failures"]),
}


def main():
    print("=" * 80)
    print("JD controller request contract -- witness chain")
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
