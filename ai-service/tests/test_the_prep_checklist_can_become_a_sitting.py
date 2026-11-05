"""65.1: the interview-prep checklist must lead into a rehearsal.

The growth panel's prep engine answers with two halves of a checklist -- what to
study (``weakAreas``) and what to rehearse (``strengthStories``) -- and stopped
there. Starting a rehearsal lived only on ``/interviews`` and the job page, so a
reader who had just been told what to practise had to leave the sentence, find a
posting (or the empty-list page) and rebuild the context by hand.

The button that closes it is a menu of the same modes every other start surface
offers; the create carries the role the checklist was asked about as the
session's ``positionTitle``, so the report that comes back still says what it was
for. This file pins the seam, not the copy: the prep result mounts the action,
the action spends the create hook with that field, and the field exists on both
the hook's body type and the backend's create record.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

PANEL = ROOT / "frontend" / "src" / "components" / "growth" / "growth-engines-panel.tsx"
ACTIONS = ROOT / "frontend" / "src" / "lib" / "hooks" / "actions.ts"
MODES = ROOT / "frontend" / "src" / "lib" / "interview-modes.ts"
DTOS = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "interview" / "dto" / "InterviewDtos.java"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_prep_result_mounts_the_practice_action_only_when_it_has_an_answer():
    """Case 1: the action rides the prep case, behind the answer it acts on."""
    panel = read(PANEL)
    assert re.search(r'\{engine === "prep" && prep\.data \? \(\s*'
                     r'<PrepPracticeAction role=\{role\.trim\(\)\} />\s*\) : null\}', panel), (
        "the prep result no longer mounts the practice menu behind its own answer")
    assert "function PrepPracticeAction({ role }: { role: string })" in panel, (
        "the practice menu lost the role it titles the sitting with")


def test_the_action_creates_a_sitting_titled_with_the_role_it_advises_about():
    """Case 2: the menu asks a mode, the create carries the role, the page follows the id."""
    panel = read(PANEL)
    start = panel.index("function PrepPracticeAction")
    body = panel[start:]
    assert "useCreateInterviewSession()" in body, (
        "the action no longer spends the one create hook the other start buttons use")
    assert re.search(r"\{ mode: m\.value, positionTitle: role \}", body), (
        "the created session no longer carries the role the checklist was asked about")
    assert "router.push(`/interviews/${id}`)" in body, (
        "the action no longer opens the rehearsal it just created")
    assert "INTERVIEW_MODES.map" in body, (
        "the menu stopped reading the one mode list the other menus share")


def test_both_halves_of_the_wire_know_the_field():
    """Case 3: the hook's body type and the backend's create record both name it."""
    actions = read(ACTIONS)
    assert re.search(r"positionTitle\?: string;", actions), (
        "useCreateInterviewSession's body type no longer carries positionTitle, so the "
        "field could be dropped before it reaches the wire")
    assert "positionTitle" in read(DTOS), (
        "the backend's create record no longer binds positionTitle, so the title would vanish")
    assert 'value: "behavioral"' in read(MODES), (
        "the shared mode list moved, so the menu would offer values the personas do not know")
